"""Le pipeline Moki : 7 étapes, journal à chaque étape (plan complet §2.3).

Le modèle de langage n'intervient qu'à l'étape 3 (interpréter). Tout le reste est du code.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Parametres
from app.core.horloge import Horloge
from app.db.modeles import Action, CasAVerifier, Client, Confirmation, Conversation, Facture, Journal, Message, Pme, Vente
from app.domaine import annulation as dom_annulation
from app.domaine import clients as dom_clients
from app.domaine import depenses as dom_depenses
from app.domaine import dossier as dom_dossier
from app.domaine import factures as dom_factures
from app.domaine import finances
from app.domaine import paiements as dom_paiements
from app.domaine import pme as dom_pme
from app.domaine import produits as dom_produits
from app.domaine import relances as dom_relances
from app.domaine import resumes as dom_resumes
from app.domaine import ventes as dom_ventes
from app.integrations.llm.interface import ErreurInterprete, Interprete
from app.integrations.stt.interface import ErreurTranscription, Transcripteur
from app.integrations.whatsapp.interface import CanalMessages, MessageSortant
from app.moki import confirmation as conf
from app.moki import contexte as ctx
from app.moki import etats, inscription, regles, reponses
from app.moki.schemas import Decision, Intention, Interpretation, Periode

CONFIANCE_STT_MIN = 0.5


@dataclass
class Dependances:
    interprete: Interprete
    transcripteur: Transcripteur
    canal: CanalMessages
    horloge: Horloge
    parametres: Parametres
    generateur_mot: Callable[[], str] = conf.mot_aleatoire


@dataclass
class Envoi:
    pme_id: int
    message: MessageSortant
    destinataire: str


@dataclass
class Resultat:
    textes: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    interpretation: Interpretation | None = None
    decision: Decision | None = None
    action: dict[str, Any] | None = None
    motif: str = ""
    erreur: str | None = None
    envois: list[Envoi] = field(default_factory=list)


class _Journal:
    def __init__(self, session: Session, pme_id: int | None, message_id: int | None, horloge: Horloge) -> None:
        self.session, self.pme_id, self.message_id, self.horloge = session, pme_id, message_id, horloge

    def ecrire(self, etape: str, entree: Any = None, sortie: Any = None, t0: float | None = None, cout: float | None = None, erreur: str | None = None) -> None:
        self.session.add(
            Journal(
                pme_id=self.pme_id,
                message_id=self.message_id,
                etape=etape,
                entree=_json(entree),
                sortie=_json(sortie),
                duree_ms=int((time.perf_counter() - t0) * 1000) if t0 is not None else 0,
                cout_estime=cout,
                erreur=erreur,
                cree_a=self.horloge.maintenant(),
            )
        )
        self.session.flush()


def _json(valeur: Any) -> Any:
    if valeur is None:
        return None
    if isinstance(valeur, dict | list):
        return valeur
    if hasattr(valeur, "model_dump"):
        return valeur.model_dump(mode="json")
    return {"valeur": str(valeur)}


def traiter(session: Session, deps: Dependances, message: Message) -> Resultat:
    """Traite un message entrant déjà persisté et renvoie les réponses à envoyer."""
    t0 = time.perf_counter()
    pme = dom_pme.pme_par_numero(session, message.numero)
    journal = _Journal(session, pme.id if pme else None, message.id, deps.horloge)
    journal.ecrire("1_normaliser", {"numero": message.numero, "type": message.type}, {"pme_id": pme.id if pme else None}, t0)
    if pme is None:
        textes_ins, motif_ins = inscription.traiter(session, deps, message)
        journal.ecrire("5_decider", None, {"inscription": motif_ins}, t0)
        return Resultat(textes=textes_ins, decision=Decision.EXECUTER, motif=motif_ins)
    message.pme_id = pme.id

    # 2. Transcrire
    texte = message.texte or ""
    if message.type == "audio":
        t1 = time.perf_counter()
        try:
            audio = deps.canal.telecharger_media(message.media_id) if message.media_id else b""
            tr = deps.transcripteur.transcrire(audio, message.media_id)
        except (ErreurTranscription, Exception) as e:  # noqa: BLE001 - toute panne est traitée pareil
            journal.ecrire("2_transcrire", {"media_id": message.media_id}, None, t1, erreur=str(e))
            _cas(session, deps, pme, message, "panne_transcription")
            return Resultat(textes=[reponses.panne()], decision=Decision.REFUSER, motif="panne_transcription", erreur=str(e))
        message.transcription, message.confiance_stt = tr.texte, tr.confiance
        journal.ecrire("2_transcrire", {"media_id": message.media_id}, {"texte": tr.texte, "confiance": tr.confiance}, t1)
        if not tr.texte.strip() or tr.confiance < CONFIANCE_STT_MIN:
            return Resultat(textes=[reponses.vocal_incompris()], decision=Decision.DEMANDER_PRECISION, motif="vocal_incompris")
        texte = tr.texte

    conv, expiree = etats.charger(session, pme, deps.horloge)
    prefixe: list[str] = [reponses.action_expiree()] if expiree else []

    # Réponse à une confirmation en attente : sans modèle de langage.
    if conv.etat in (etats.ATTEND_CONFIRMATION, etats.ATTEND_CONFIRMATION_RENFORCEE):
        resultat = _traiter_confirmation(session, deps, pme, conv, message, texte, journal)
        if resultat is not None:
            resultat.textes = prefixe + resultat.textes
            return resultat
        prefixe.append("(J'ai laissé tomber l'action précédente.)")

    # 3. Interpréter
    t3 = time.perf_counter()
    contexte = ctx.construire(session, pme, conv, deps.horloge)
    try:
        res = deps.interprete.interpreter(contexte, texte)
    except (ErreurInterprete, Exception) as e:  # noqa: BLE001
        journal.ecrire("3_interpreter", {"texte": texte}, None, t3, erreur=str(e))
        _cas(session, deps, pme, message, "panne_modele")
        return Resultat(textes=prefixe + [reponses.panne()], decision=Decision.REFUSER, motif="panne_modele", erreur=str(e))
    interp = res.interpretation
    journal.ecrire("3_interpreter", {"texte": texte, "etat": conv.etat}, {"interpretation": interp.model_dump(mode="json"), "modele": res.modele, "tokens_entree": res.tokens_entree, "tokens_sortie": res.tokens_sortie}, t3, cout=res.cout_estime)

    # 4. Valider (règles en code)
    t4 = time.perf_counter()
    if conv.etat == etats.ATTEND_PRECISION:
        # Le modèle a reçu l'action en attente dans son contexte et renvoie l'interprétation complétée.
        etats.liberer(session, conv, deps.horloge)
    verdict = regles.evaluer(session, pme, interp, deps.horloge)
    journal.ecrire("4_valider", None, {"decision": verdict.decision.value, "motif": verdict.motif, "action": verdict.action}, t4)

    # 5. Décider / 6. Exécuter / 7. Répondre
    resultat = _appliquer(session, deps, pme, conv, message, verdict, journal)
    resultat.interpretation = interp
    resultat.textes = prefixe + resultat.textes
    return resultat


def _traiter_confirmation(session: Session, deps: Dependances, pme: Pme, conv: Conversation, message: Message, texte: str, journal: _Journal) -> Resultat | None:
    """Renvoie un Resultat si le message est une réponse à la confirmation ; None pour abandonner et interpréter le message."""
    t0 = time.perf_counter()
    if conv.etat == etats.ATTEND_CONFIRMATION_RENFORCEE and conv.mot_confirmation:
        rep = conf.lire_renforcee(texte, conv.mot_confirmation)
    else:
        rep = conf.lire(texte)
    action = conv.action_en_attente or {}
    confirmation = session.get(Confirmation, conv.confirmation_id) if conv.confirmation_id else None
    interp_synth = Interpretation(intention=Intention.CONFIRMATION, confiance=1.0)

    if rep == conf.Reponse.OUI:
        if confirmation is not None:
            confirmation.statut = "confirmee"
            confirmation.confirmee_a = deps.horloge.maintenant()
            confirmation.par_numero = message.numero
        etats.liberer(session, conv, deps.horloge)
        journal.ecrire("5_decider", {"texte": texte}, {"confirmation": "oui", "action": action}, t0)
        resultat = _executer(session, deps, pme, action, message, journal, confirmation.id if confirmation else None)
        resultat.interpretation = interp_synth
        resultat.decision = Decision.EXECUTER
        return resultat
    if rep == conf.Reponse.NON:
        if confirmation is not None:
            confirmation.statut = "refusee"
        etats.liberer(session, conv, deps.horloge)
        journal.ecrire("5_decider", {"texte": texte}, {"confirmation": "non"}, t0)
        return Resultat(textes=[reponses.action_abandonnee()], interpretation=interp_synth, decision=Decision.REFUSER, motif="refus_pme")
    # Une vraie phrase (plus de 3 mots) est une nouvelle demande : on abandonne l'action en attente sans la bloquer.
    if len(texte.split()) > 3:
        if confirmation is not None:
            confirmation.statut = "expiree"
        etats.liberer(session, conv, deps.horloge)
        journal.ecrire("5_decider", {"texte": texte}, {"confirmation": "nouvelle_demande"}, t0)
        return None
    # Réponse incompréhensible : on rappelle la question une fois, puis on abandonne.
    if not action.get("rappel_fait"):
        conv.action_en_attente = {**action, "rappel_fait": True}
        session.flush()
        question = conv.question_en_attente or "Tu confirmes ?"
        if conv.etat == etats.ATTEND_CONFIRMATION_RENFORCEE and conv.mot_confirmation:
            question = reponses.confirmation_renforcee(conv.mot_confirmation)
        journal.ecrire("5_decider", {"texte": texte}, {"confirmation": "rappel"}, t0)
        return Resultat(textes=[reponses.rappel_question(question)], interpretation=interp_synth, decision=Decision.DEMANDER_CONFIRMATION, motif="rappel")
    if confirmation is not None:
        confirmation.statut = "expiree"
    etats.liberer(session, conv, deps.horloge)
    journal.ecrire("5_decider", {"texte": texte}, {"confirmation": "abandon"}, t0)
    return None


def _appliquer(session: Session, deps: Dependances, pme: Pme, conv: Conversation, message: Message, verdict: regles.Verdict, journal: _Journal) -> Resultat:
    t0 = time.perf_counter()
    d = verdict.decision
    if d == Decision.EXECUTER:
        assert verdict.action is not None
        etats.liberer(session, conv, deps.horloge)
        journal.ecrire("5_decider", None, {"decision": d.value}, t0)
        resultat = _executer(session, deps, pme, verdict.action, message, journal, None)
        resultat.decision, resultat.motif = d, verdict.motif
        return resultat
    if d == Decision.DEMANDER_PRECISION:
        assert verdict.action is not None and verdict.message
        action = {**verdict.action, "texte_initial": message.texte or message.transcription or ""}
        etats.mettre_en_attente(session, conv, deps.horloge, etat=etats.ATTEND_PRECISION, action=action, question=verdict.message)
        journal.ecrire("5_decider", None, {"decision": d.value, "question": verdict.message}, t0)
        return Resultat(textes=[verdict.message], decision=d, action=verdict.action, motif=verdict.motif)
    if d in (Decision.DEMANDER_CONFIRMATION, Decision.CONFIRMATION_RENFORCEE):
        assert verdict.action is not None and verdict.message
        renforcee = d == Decision.CONFIRMATION_RENFORCEE
        confirmation = Confirmation(pme_id=pme.id, action=verdict.action, mode="renforcee" if renforcee else "simple", demandee_a=deps.horloge.maintenant(), statut="en_attente")
        session.add(confirmation)
        session.flush()
        mot = deps.generateur_mot() if renforcee else None
        question = reponses.demande_oui_non(verdict.message) if not renforcee else verdict.message
        etats.mettre_en_attente(session, conv, deps.horloge, etat=etats.ATTEND_CONFIRMATION_RENFORCEE if renforcee else etats.ATTEND_CONFIRMATION, action=verdict.action, question=question, mot=mot, confirmation_id=confirmation.id)
        textes = [question] + ([reponses.confirmation_renforcee(mot)] if mot else [])
        journal.ecrire("5_decider", None, {"decision": d.value, "confirmation_id": confirmation.id}, t0)
        return Resultat(textes=textes, decision=d, action=verdict.action, motif=verdict.motif)
    # REFUSER
    etats.liberer(session, conv, deps.horloge)
    journal.ecrire("5_decider", None, {"decision": d.value, "motif": verdict.motif}, t0)
    if verdict.motif in ("piege", "incompris"):
        _cas(session, deps, pme, message, verdict.motif)
    return Resultat(textes=[verdict.message or reponses.incompris()], decision=d, motif=verdict.motif)


def _executer(session: Session, deps: Dependances, pme: Pme, action: dict[str, Any], message: Message, journal: _Journal, confirmation_id: int | None) -> Resultat:
    t0 = time.perf_counter()
    genre = action.get("type")
    horloge = deps.horloge
    try:
        resultat = _executer_action(session, deps, pme, action, message, confirmation_id)
    except Exception as e:  # noqa: BLE001 - on ne prétend jamais avoir enregistré
        session.rollback()
        journal.ecrire("6_executer", {"type": genre}, None, t0, erreur=str(e))
        _cas(session, deps, pme, message, "panne_execution")
        return Resultat(textes=[reponses.panne()], action=action, erreur=str(e))
    journal.ecrire("6_executer", {"type": genre, "confirmation_id": confirmation_id}, {"textes": resultat.textes, "documents": resultat.documents}, t0)
    journal.ecrire("7_repondre", None, {"nb": len(resultat.textes)}, time.perf_counter())
    resultat.action = action
    _ = horloge
    return resultat


def _executer_action(session: Session, deps: Dependances, pme: Pme, action: dict[str, Any], message: Message, confirmation_id: int | None) -> Resultat:
    genre = action.get("type")
    horloge = deps.horloge

    if genre in ("VENTE", "LIEN_PAIEMENT_CREDIT"):
        client = _client_de(session, pme, action.get("client_id"))
        if client is None and action.get("client_nom_cite") and action["mode"] == "credit":
            client = dom_clients.ajouter(session, pme, action["client_nom_cite"])
            _tracer_action(session, pme, horloge, "CLIENT", client.id, f"client {client.nom}")
        vente = dom_ventes.enregistrer(session, pme, horloge, lignes=action["lignes"], mode=action["mode"], heure_envoi=message.heure_envoi, client=client, client_nom_cite=action.get("client_nom_cite"), message_id=message.id)
        if action["mode"] == "credit":
            assert client is not None
            reste = dom_paiements.reste_du_client(session, pme, client)
            return Resultat(textes=[reponses.vente_credit_notee(vente.total, client.nom, reste)])
        textes = [reponses.vente_notee(vente.total, action["mode"], dom_resumes.total_du_jour(session, pme, horloge))]
        if action.get("client_nom_cite") and client is None:
            textes.append(reponses.client_inconnu_propose(action["client_nom_cite"]))
        return Resultat(textes=textes)

    if genre == "FACTURE":
        if confirmation_id is None:
            raise PermissionError("facture sans confirmation")
        client = _client_de(session, pme, action.get("client_id"))
        if client is None:
            client = dom_clients.ajouter(session, pme, action["client_nom"])
        facture = dom_factures.creer(session, pme, horloge, client=client, lignes=action["lignes"], frais=action.get("frais", []), confirmation_id=confirmation_id, dossier_pdf=deps.parametres.dossier_factures)
        documents = [facture.pdf_chemin] if facture.pdf_chemin else []
        lien = f"https://pay.moki.cm/f/{pme.id}-{facture.numero}"
        envois: list[Envoi] = []
        if pme.mode_relance == "direct" and client.telephone:
            envois.append(Envoi(pme.id, MessageSortant(numero=client.telephone, texte=reponses.facture_pour_client(pme.nom_commerce, client.nom, facture.numero, facture.total, lien), document=facture.pdf_chemin), client.nom))
            texte = reponses.facture_prete_direct(facture.numero, client.nom, facture.total, lien)
        else:
            texte = reponses.facture_prete(facture.numero, client.nom, facture.total, lien)
        return Resultat(textes=[texte], documents=documents, envois=envois)

    if genre == "RELANCE":
        if confirmation_id is None:
            raise PermissionError("relance sans confirmation")
        facture = session.get(Facture, action["facture_id"])
        client = _client_de(session, pme, action["client_id"])
        if facture is None or facture.pme_id != pme.id or client is None:
            raise PermissionError("facture ou client hors PME")
        if facture.statut not in dom_factures.STATUTS_OUVERTS:
            return Resultat(textes=[reponses.rien_d_ouvert(client.nom)])
        dom_relances.enregistrer(session, pme, horloge, facture=facture, client=client, texte=action["texte"], confirmation_id=confirmation_id, mode=pme.mode_relance)
        if pme.mode_relance == "direct" and client.telephone:
            return Resultat(textes=[reponses.relance_envoi_direct(client.nom)], envois=[Envoi(pme.id, MessageSortant(numero=client.telephone, texte=action["texte"]), client.nom)])
        return Resultat(textes=[reponses.relance_prete(client.nom, action["texte"])])

    if genre == "PAIEMENT_RECU":
        if confirmation_id is None:
            raise PermissionError("paiement sans confirmation")
        client = _client_de(session, pme, action.get("client_id"))
        if action.get("facture_id"):
            facture = session.get(Facture, action["facture_id"])
            if facture is None or facture.pme_id != pme.id:
                raise PermissionError("facture hors PME")
            paiement = dom_paiements.declarer_sur_facture(session, pme, horloge, facture)
        else:
            vente = session.get(Vente, action["vente_id"])
            if vente is None or vente.pme_id != pme.id:
                raise PermissionError("vente hors PME")
            paiement = dom_paiements.declarer_sur_vente(session, pme, horloge, vente)
        nom = client.nom if client else action.get("client_nom", "le client")
        reste = dom_paiements.reste_du_client(session, pme, client) if client else 0
        return Resultat(textes=[reponses.paiement_recu_note(nom, paiement.montant, reste)])

    if genre == "PRODUIT":
        produit, cree = dom_produits.ajouter_ou_mettre_a_jour(session, pme, action["nom"], action["prix"])
        if cree:
            _tracer_action(session, pme, horloge, "PRODUIT", produit.id, f"produit {produit.nom}")
            return Resultat(textes=[reponses.produit_ajoute(produit.nom, produit.prix)])
        return Resultat(textes=[reponses.produit_mis_a_jour(produit.nom, produit.prix)])

    if genre == "CLIENT":
        client = dom_clients.ajouter(session, pme, action["nom"], action.get("telephone"))
        _tracer_action(session, pme, horloge, "CLIENT", client.id, f"client {client.nom}")
        return Resultat(textes=[reponses.client_ajoute(client.nom, client.telephone)])

    if genre == "DEPENSE":
        dep = dom_depenses.enregistrer(session, pme, horloge, libelle=action["libelle"], montant=action["montant"], type_=action["type_depense"], nature=action["nature"], heure_envoi=message.heure_envoi, message_id=message.id)
        return Resultat(textes=[reponses.depense_notee(dep.libelle, dep.montant, dep.nature, dep.type)])

    if genre == "CHANGER_NATURE":
        dep = dom_depenses.derniere(session, pme, horloge)
        if dep is None:
            return Resultat(textes=[reponses.rien_a_changer()])
        dom_depenses.changer_nature(session, dep, action["nature"])
        return Resultat(textes=[reponses.nature_changee(dep.libelle, dep.montant, dep.nature)])

    if genre == "BILAN":
        mois = finances.chiffres_periode(session, pme, Periode(type="mois"), horloge)
        return Resultat(textes=[reponses.bilan(finances.tresorerie(session, pme), mois["benefice"], mois["retraits"], mois["ventes"], mois["charges"])])

    if genre == "DOSSIER_CREDIT":
        chemin, d = dom_dossier.generer(session, pme, horloge, deps.parametres.dossier_factures)
        return Resultat(textes=[reponses.dossier_pret(d["historique_mois"], d["manque_mois"], pme.donnees_fictives)], documents=[chemin])

    if genre == "IMPOT":
        est = finances.impot_estime(session, pme, horloge)
        ech = finances.prochaine_echeance(horloge, pme.fuseau)
        return Resultat(textes=[reponses.impot(est["estimation"], est["ca_annuel"], ech["libelle"], ech["jours"])])

    if genre == "ECHEANCES":
        return Resultat(textes=[reponses.echeances(finances.echeances(horloge, pme.fuseau))])

    if genre == "PRODUIT_SUPPR":
        produit = dom_produits.rechercher(session, pme, action["nom"])
        if produit is None:
            return Resultat(textes=[reponses.produit_introuvable(action["nom"])])
        produit.actif = False
        session.flush()
        return Resultat(textes=[reponses.produit_supprime(produit.nom)])

    if genre == "ANNULER":
        derniere = dom_annulation.derniere_annulable(session, pme, horloge)
        if derniere is None:
            return Resultat(textes=[reponses.rien_a_annuler()])
        resume = dom_annulation.annuler(session, pme, derniere, horloge)
        return Resultat(textes=[reponses.annule(resume)])

    if genre == "RESUME":
        periode = Periode.model_validate(action["periode"]) if action.get("periode") else None
        r = dom_resumes.calculer(session, pme, periode, horloge)
        return Resultat(textes=[reponses.resume(r["libelle"], r["nb"], r["total"], r["par_mode"], r["impayes"], r["charges"], r["benefice"])])

    if genre == "QUI_DOIT":
        return Resultat(textes=[reponses.qui_doit(dom_paiements.impayes_par_client(session, pme, horloge))])

    if genre == "AIDE":
        return Resultat(textes=[reponses.aide()])

    if genre == "HUMAIN":
        _cas(session, deps, pme, message, "demande_humain")
        return Resultat(textes=[reponses.humain()])

    if genre == "RIEN_A_CONFIRMER":
        return Resultat(textes=[reponses.rien_a_confirmer()])

    if genre == "RIEN_D_OUVERT":
        return Resultat(textes=[reponses.rien_d_ouvert(action.get("client_nom"))])

    if genre == "CLIENT_INCONNU":
        return Resultat(textes=[reponses.client_inconnu_propose(action["nom"])])

    raise ValueError(f"action inconnue : {genre}")


def _client_de(session: Session, pme: Pme, client_id: int | None) -> Client | None:
    if client_id is None:
        return None
    client = session.get(Client, client_id)
    if client is None or client.pme_id != pme.id:
        raise PermissionError("client hors PME")
    return client


def _tracer_action(session: Session, pme: Pme, horloge: Horloge, genre: str, cible_id: int, resume: str) -> None:
    maintenant = horloge.maintenant()
    session.add(Action(pme_id=pme.id, type=genre, cible_id=cible_id, resume=resume, creee_a=maintenant, annulable_jusqua=maintenant + dom_ventes.FENETRE_ANNULATION))
    session.flush()


def _cas(session: Session, deps: Dependances, pme: Pme | None, message: Message, motif: str) -> None:
    session.add(CasAVerifier(pme_id=pme.id if pme else None, message_id=message.id, motif=motif, gravite="normale", details={"texte": message.texte or message.transcription}, cree_a=deps.horloge.maintenant()))
    session.flush()
