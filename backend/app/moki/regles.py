"""Règles métier appliquées EN DEHORS du modèle de langage (plan complet §2.5).

Entrée : une `Interpretation`. Sortie : un `Verdict` (décision + message + action prête
à exécuter). Les totaux sont toujours recalculés ici, jamais repris du modèle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import Client, Pme
from app.domaine import clients as dom_clients
from app.domaine import factures as dom_factures
from app.domaine import paiements as dom_paiements
from app.domaine import relances as dom_relances
from app.domaine import ventes as dom_ventes
from app.moki import reponses
from app.moki.schemas import Decision, Intention, Interpretation, ModePaiement

SEUIL_CONFIANCE = 0.6
FACTEUR_INHABITUEL = 8
MIN_VENTES_POUR_MOYENNE = 20
MOTS_PIEGE = ("tous mes clients", "tout le monde", "ignore", "oublie tes", "contourne")


@dataclass
class Verdict:
    decision: Decision
    message: str | None = None
    action: dict[str, Any] | None = None
    motif: str = ""
    messages_suppl: list[str] = field(default_factory=list)


def _lignes_dict(interp: Interpretation) -> list[dict]:
    return [
        {"produit": ligne.produit, "quantite": ligne.quantite, "prix_unitaire": ligne.prix_unitaire}
        for ligne in interp.lignes
    ]


def _frais_dict(interp: Interpretation) -> list[dict]:
    return [{"libelle": f.libelle, "montant": f.montant} for f in interp.frais]


def _precision(question: str, interp: Interpretation, motif: str) -> Verdict:
    return Verdict(
        Decision.DEMANDER_PRECISION,
        message=question,
        action={"type": "PRECISION", "interpretation": interp.model_dump(mode="json"), "question": question},
        motif=motif,
    )


def _resoudre_client(
    session: Session, pme: Pme, interp: Interpretation
) -> tuple[Client | None, list[Client], str | None]:
    """(client unique ou None, candidats, nom cité)."""
    nom = interp.nom_client()
    if not nom:
        return None, [], None
    candidats = dom_clients.rechercher(session, pme, nom)
    if len(candidats) == 1:
        return candidats[0], candidats, nom
    return None, candidats, nom


def evaluer(session: Session, pme: Pme, interp: Interpretation, horloge: Horloge) -> Verdict:
    i = interp.intention

    if i == Intention.CONFIRMATION:
        return Verdict(Decision.EXECUTER, action={"type": "RIEN_A_CONFIRMER"}, motif="confirmation hors contexte")
    if i == Intention.AIDE:
        return Verdict(Decision.EXECUTER, action={"type": "AIDE"})
    if i == Intention.HUMAIN:
        return Verdict(Decision.EXECUTER, action={"type": "HUMAIN"})
    if i == Intention.ANNULER:
        return Verdict(Decision.EXECUTER, action={"type": "ANNULER"})
    if i == Intention.QUI_DOIT:
        return Verdict(Decision.EXECUTER, action={"type": "QUI_DOIT"})
    if i == Intention.RESUME:
        periode = interp.periode.model_dump(mode="json") if interp.periode else None
        return Verdict(Decision.EXECUTER, action={"type": "RESUME", "periode": periode})
    if i == Intention.BILAN:
        return Verdict(Decision.EXECUTER, action={"type": "BILAN"})
    if i == Intention.DOSSIER_CREDIT:
        return Verdict(Decision.EXECUTER, action={"type": "DOSSIER_CREDIT"})
    if i == Intention.IMPOT:
        return Verdict(Decision.EXECUTER, action={"type": "IMPOT"})
    if i == Intention.ECHEANCES:
        return Verdict(Decision.EXECUTER, action={"type": "ECHEANCES"})
    if i == Intention.AUTRE:
        raison = (interp.hors_perimetre.raison if interp.hors_perimetre else "") or ""
        if any(m in raison.lower() for m in MOTS_PIEGE) or "masse" in raison.lower():
            return Verdict(Decision.REFUSER, message=reponses.refus_piege(), motif="piege")
        if interp.confiance < SEUIL_CONFIANCE and not raison:
            return Verdict(Decision.REFUSER, message=reponses.incompris(), motif="incompris")
        return Verdict(Decision.REFUSER, message=reponses.hors_perimetre(), motif="hors_perimetre")

    if interp.confiance < SEUIL_CONFIANCE:
        return _precision(interp.question_a_poser or reponses.incompris(), interp, "confiance_basse")

    if i == Intention.DEPENSE:
        return _depense(interp)
    if i == Intention.CHANGER_NATURE:
        nature = interp.depense.nature.value if interp.depense else "perso"
        return Verdict(Decision.EXECUTER, action={"type": "CHANGER_NATURE", "nature": nature})
    if i == Intention.PRODUIT:
        return _produit(interp)
    if i == Intention.CLIENT:
        return _client(interp)
    if i == Intention.VENTE:
        return _vente(session, pme, interp, horloge)
    if i == Intention.FACTURE:
        return _facture(session, pme, interp)
    if i == Intention.LIEN_PAIEMENT:
        return _lien(session, pme, interp)
    if i == Intention.PAIEMENT_RECU:
        return _paiement_recu(session, pme, interp)
    if i == Intention.RELANCE:
        return _relance(session, pme, interp, horloge)
    return Verdict(Decision.REFUSER, message=reponses.incompris(), motif="intention_inconnue")


def _depense(interp: Interpretation) -> Verdict:
    d = interp.depense
    if d is None or not d.montant or d.montant <= 0:
        return _precision(interp.question_a_poser or reponses.precision_depense(), interp, "depense_sans_montant")
    nature = d.nature.value
    libelle = (d.libelle or "").strip()
    if not libelle:
        if nature == "perso":
            libelle = "retrait personnel"
        else:
            return _precision("C'était pour quoi ? (loyer, électricité, salaire, stock…)", interp, "depense_sans_libelle")
    type_depense = "retrait_perso" if nature == "perso" else d.type.value
    return Verdict(Decision.EXECUTER, action={"type": "DEPENSE", "libelle": libelle, "montant": d.montant, "nature": nature, "type_depense": type_depense})


def _produit(interp: Interpretation) -> Verdict:
    if interp.action_produit == "supprimer":
        nom = interp.lignes[0].produit if interp.lignes else None
        if not nom:
            return _precision("Quel produit veux-tu retirer du catalogue ?", interp, "produit_sans_nom")
        return Verdict(Decision.EXECUTER, action={"type": "PRODUIT_SUPPR", "nom": nom.strip()})
    if not interp.lignes or not interp.lignes[0].produit or not interp.lignes[0].prix_unitaire:
        return _precision("Quel produit, et à quel prix ?", interp, "produit_incomplet")
    ligne = interp.lignes[0]
    assert ligne.produit and ligne.prix_unitaire
    if ligne.prix_unitaire <= 0:
        return _precision("Le prix doit être supérieur à zéro. Quel est le prix ?", interp, "prix_invalide")
    return Verdict(Decision.EXECUTER, action={"type": "PRODUIT", "nom": ligne.produit.strip(), "prix": ligne.prix_unitaire})


def _client(interp: Interpretation) -> Verdict:
    nom = interp.nom_client()
    if not nom:
        return _precision("Quel est le nom du client ?", interp, "client_sans_nom")
    telephone = interp.client.telephone if interp.client else None
    return Verdict(Decision.EXECUTER, action={"type": "CLIENT", "nom": nom, "telephone": telephone})


def _vente(session: Session, pme: Pme, interp: Interpretation, horloge: Horloge) -> Verdict:
    if not interp.lignes:
        return _precision(interp.question_a_poser or reponses.precision_vente(), interp, "vente_sans_lignes")
    if interp.ambiguites and interp.question_a_poser:
        return _precision(interp.question_a_poser, interp, "ambiguite")
    if not interp.lignes_completes():
        return _precision(interp.question_a_poser or reponses.precision_vente(), interp, "lignes_incompletes")

    lignes = _lignes_dict(interp)
    total = dom_ventes.total_des_lignes(lignes)
    recap = reponses.recap_lignes(lignes)

    client, candidats, nom_cite = _resoudre_client(session, pme, interp)
    if nom_cite and len(candidats) > 1:
        return _precision(
            reponses.client_ambigu(nom_cite, [dom_clients.libelle(c) for c in candidats]), interp, "client_ambigu"
        )

    if interp.paiement == ModePaiement.INCONNU:
        return _precision(reponses.demande_mode_paiement(recap, total), interp, "mode_paiement_inconnu")
    if interp.paiement == ModePaiement.CREDIT and not nom_cite:
        return _precision(reponses.precision_credit_client(), interp, "credit_sans_client")

    action = {
        "type": "VENTE",
        "lignes": lignes,
        "mode": interp.paiement.value,
        "client_id": client.id if client else None,
        "client_nom_cite": nom_cite,
        "total": total,
        "recap": recap,
    }
    if dom_ventes.doublon_probable(session, pme, horloge, lignes, total):
        return Verdict(Decision.DEMANDER_CONFIRMATION, message=reponses.doublon_possible(recap, total), action=action, motif="doublon")
    if total > pme.seuil_confirmation_renforcee:
        return Verdict(Decision.DEMANDER_CONFIRMATION, message=f"{recap}\n{reponses.montant_eleve(total)}", action=action, motif="montant_eleve")
    nb, moyenne = dom_ventes.panier_moyen(session, pme, horloge)
    if nb >= MIN_VENTES_POUR_MOYENNE and moyenne > 0 and total > FACTEUR_INHABITUEL * moyenne:
        return Verdict(Decision.DEMANDER_CONFIRMATION, message=f"{recap}\n{reponses.montant_inhabituel(total, moyenne)}", action=action, motif="montant_inhabituel")
    return Verdict(Decision.EXECUTER, action=action)


def _facture(session: Session, pme: Pme, interp: Interpretation) -> Verdict:
    if not interp.lignes:
        return _precision(interp.question_a_poser or "Quelles lignes sur la facture (produit, quantité, prix) ?", interp, "facture_sans_lignes")
    if interp.ambiguites and interp.question_a_poser:
        return _precision(interp.question_a_poser, interp, "ambiguite")
    if not interp.lignes_completes():
        return _precision(interp.question_a_poser or "Il me manque une quantité ou un prix. Tu peux préciser ?", interp, "lignes_incompletes")
    client, candidats, nom_cite = _resoudre_client(session, pme, interp)
    if not nom_cite:
        return _precision(reponses.precision_client_facture(), interp, "facture_sans_client")
    if len(candidats) > 1:
        return _precision(reponses.client_ambigu(nom_cite, [dom_clients.libelle(c) for c in candidats]), interp, "client_ambigu")

    lignes = [{**ligne, "produit": ligne["produit"] or "Prestation"} for ligne in _lignes_dict(interp)]
    frais = _frais_dict(interp)
    total = dom_factures.total_facture(lignes, frais)
    recap = reponses.recap_lignes(lignes, frais)
    action = {
        "type": "FACTURE",
        "lignes": lignes,
        "frais": frais,
        "client_id": client.id if client else None,
        "client_nom": client.nom if client else nom_cite,
        "total": total,
    }
    message = reponses.facture_recap(action["client_nom"], recap, total, client_nouveau=client is None)
    if total > pme.seuil_confirmation_renforcee:
        return Verdict(Decision.CONFIRMATION_RENFORCEE, message=message, action=action, motif="montant_eleve")
    return Verdict(Decision.DEMANDER_CONFIRMATION, message=message, action=action, motif="action_sortante")


def _lien(session: Session, pme: Pme, interp: Interpretation) -> Verdict:
    """Étage A : pas de lien de paiement, on propose une vente à crédit à suivre."""
    if not interp.lignes_completes():
        return _precision("Quel montant, et pour quel client ?", interp, "lien_sans_montant")
    montant = interp.total()
    client, candidats, nom_cite = _resoudre_client(session, pme, interp)
    if not nom_cite:
        return _precision("Pour quel client ?", interp, "lien_sans_client")
    if len(candidats) > 1:
        return _precision(reponses.client_ambigu(nom_cite, [dom_clients.libelle(c) for c in candidats]), interp, "client_ambigu")
    nom = client.nom if client else nom_cite
    action = {
        "type": "LIEN_PAIEMENT_CREDIT",
        "lignes": [{"produit": "montant demandé", "quantite": 1, "prix_unitaire": montant}],
        "mode": "credit",
        "client_id": client.id if client else None,
        "client_nom_cite": nom,
        "total": montant,
        "recap": reponses.recap_lignes([{"produit": "montant demandé", "quantite": 1, "prix_unitaire": montant}]),
    }
    decision = Decision.CONFIRMATION_RENFORCEE if montant > pme.seuil_confirmation_renforcee else Decision.DEMANDER_CONFIRMATION
    return Verdict(decision, message=reponses.lien_indisponible_credit(montant, nom), action=action, motif="etage_a")


def _paiement_recu(session: Session, pme: Pme, interp: Interpretation) -> Verdict:
    client, candidats, nom_cite = _resoudre_client(session, pme, interp)
    if nom_cite and len(candidats) > 1:
        return _precision(reponses.client_ambigu(nom_cite, [dom_clients.libelle(c) for c in candidats]), interp, "client_ambigu")
    if nom_cite and not candidats:
        return Verdict(Decision.EXECUTER, action={"type": "CLIENT_INCONNU", "nom": nom_cite}, motif="client_inconnu")

    factures = dom_factures.ouvertes(session, pme, client)
    if interp.reference_facture:
        try:
            numero = int("".join(ch for ch in interp.reference_facture if ch.isdigit()))
            factures = [f for f in factures if f.numero == numero]
        except ValueError:
            pass
    ventes = dom_ventes.ventes_a_credit(session, pme, client)
    if client is None and not interp.reference_facture:
        # Sans client ni référence : on ne devine pas.
        ouverts = len(factures) + len(ventes)
        if ouverts == 0:
            return Verdict(Decision.EXECUTER, action={"type": "RIEN_D_OUVERT", "client_nom": None})
        return _precision("De qui as-tu reçu ce paiement ?", interp, "paiement_sans_client")

    candidats_paiement: list[tuple[str, int, dict]] = []
    for f in factures:
        c = session.get(Client, f.client_id)
        candidats_paiement.append((f"la facture n° {f.numero:03d}", f.total, {"facture_id": f.id, "client_id": f.client_id, "client_nom": c.nom if c else "?"}))
    for v in ventes:
        candidats_paiement.append(("la vente à crédit", v.credit_restant, {"vente_id": v.id, "client_id": v.client_id, "client_nom": client.nom if client else "?"}))

    if not candidats_paiement:
        return Verdict(Decision.EXECUTER, action={"type": "RIEN_D_OUVERT", "client_nom": client.nom if client else nom_cite})
    if len(candidats_paiement) > 1:
        choix = [f"{d} ({m} F)" for d, m, _ in candidats_paiement]
        return _precision(reponses.precision_choix_facture(choix), interp, "plusieurs_impayes")
    detail, montant, cible = candidats_paiement[0]
    action = {"type": "PAIEMENT_RECU", "montant": montant, "detail": detail, **cible}
    return Verdict(Decision.DEMANDER_CONFIRMATION, message=reponses.paiement_recu_recap(cible["client_nom"], detail, montant), action=action, motif="paiement_declare")


def _relance(session: Session, pme: Pme, interp: Interpretation, horloge: Horloge) -> Verdict:
    client, candidats, nom_cite = _resoudre_client(session, pme, interp)
    if not nom_cite:
        return _precision(interp.question_a_poser or reponses.precision_relance(), interp, "relance_sans_client")
    if len(candidats) > 1:
        return _precision(reponses.client_ambigu(nom_cite, [dom_clients.libelle(c) for c in candidats]), interp, "client_ambigu")
    if client is None:
        return Verdict(Decision.EXECUTER, action={"type": "CLIENT_INCONNU", "nom": nom_cite}, motif="client_inconnu")

    factures = dom_factures.ouvertes(session, pme, client)
    if interp.reference_facture:
        numero = int("".join(ch for ch in interp.reference_facture if ch.isdigit()) or 0)
        factures = [f for f in factures if f.numero == numero]
    if not factures:
        return Verdict(Decision.EXECUTER, action={"type": "RIEN_D_OUVERT", "client_nom": client.nom}, motif="rien_a_relancer")
    if len(factures) > 1:
        choix = [f"n° {f.numero:03d} ({f.total} F)" for f in factures]
        return _precision(reponses.precision_choix_facture(choix), interp, "plusieurs_factures")
    facture = factures[0]
    plafond = dom_relances.plafond_atteint(session, pme, client, horloge)
    if plafond:
        return Verdict(Decision.REFUSER, message=reponses.relance_plafond(client.nom), motif=f"plafond_{plafond}")
    texte = dom_relances.rediger(pme, client, facture, horloge)
    action = {"type": "RELANCE", "facture_id": facture.id, "client_id": client.id, "client_nom": client.nom, "texte": texte}
    return Verdict(Decision.DEMANDER_CONFIRMATION, message=reponses.relance_proposee(client.nom, texte), action=action, motif="action_sortante")


def reste_du_client(session: Session, pme: Pme, client: Client) -> int:
    return dom_paiements.reste_du_client(session, pme, client)
