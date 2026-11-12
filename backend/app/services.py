"""Assemblage des dépendances selon la configuration, et traitement d'un message entrant."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Parametres
from app.core.horloge import Horloge, HorlogeSysteme
from app.db.modeles import Message
from app.domaine.pme import pme_par_numero
from app.integrations.llm.factice import InterpreteRegles
from app.integrations.llm.interface import ContexteInterpretation, ErreurInterprete, Interprete, ResultatInterpretation
from app.integrations.stt.interface import Transcripteur, TranscripteurFactice
from app.integrations.whatsapp.interface import CanalFactice, CanalMessages, MessageEntrant, MessageSortant
from app.moki import pipeline, reponses


class _InterpreteRegles:
    def __init__(self) -> None:
        self._r = InterpreteRegles()

    def interpreter(self, contexte: ContexteInterpretation, texte: str) -> ResultatInterpretation:
        return self._r.interpreter(contexte, texte)


class InterpreteAvecRepli:
    """Modèle réel d'abord ; si le service est indisponible, l'analyseur à règles prend le relais (la démo ne tombe pas)."""

    def __init__(self, principal: Interprete | list[Interprete], secours: Interprete) -> None:
        self.principaux = principal if isinstance(principal, list) else [principal]
        self.secours = secours
        self.nb_replis = 0

    INTENTIONS_RAPIDES = ("QUI_DOIT", "RESUME", "BILAN", "DOSSIER_CREDIT", "IMPOT", "ECHEANCES", "ANNULER", "AIDE", "HUMAIN")

    def interpreter(self, contexte: ContexteInterpretation, texte: str) -> ResultatInterpretation:
        # Voie rapide : les demandes simples et sans ambiguïté sont reconnues localement (instantané, gratuit, sans réseau).
        if contexte.etat_conversation == "LIBRE":
            rapide = self.secours.interpreter(contexte, texte)
            if rapide.interpretation.intention.value in self.INTENTIONS_RAPIDES and rapide.interpretation.confiance >= 0.9:
                return rapide
        for candidat in self.principaux:
            try:
                return candidat.interpreter(contexte, texte)
            except ErreurInterprete:
                continue
        self.nb_replis += 1
        return self.secours.interpreter(contexte, texte)


def construire_dependances(p: Parametres, horloge: Horloge | None = None, canal: CanalMessages | None = None) -> pipeline.Dependances:
    interprete: Interprete
    if p.interprete == "claude":
        from app.integrations.llm.claude import InterpreteClaude

        interprete = InterpreteAvecRepli(InterpreteClaude(p.modele, p.effort), _InterpreteRegles())
    elif p.interprete == "gemini":
        from app.integrations.llm.gemini import InterpreteGemini

        modeles = [p.modele_gemini, *[m for m in ("gemini-3.8-flash",) if m != p.modele_gemini]]
        interprete = InterpreteAvecRepli([InterpreteGemini(p.gemini_cle, m) for m in modeles], _InterpreteRegles())
    else:
        interprete = _InterpreteRegles()
    if canal is None:
        if p.canal == "cloud_api":
            from app.integrations.whatsapp.cloud_api import CanalCloudApi

            canal = CanalCloudApi(p.whatsapp_jeton, p.whatsapp_id_numero)
        else:
            canal = CanalFactice()
    transcripteur: Transcripteur = TranscripteurFactice()
    return pipeline.Dependances(interprete=interprete, transcripteur=transcripteur, canal=canal, horloge=horloge or HorlogeSysteme(), parametres=p)


def traiter_entrant(fabrique: sessionmaker[Session], deps: pipeline.Dependances, entrant: MessageEntrant) -> list[str]:
    """Persiste (idempotent sur wamid), traite, envoie les réponses. Renvoie les textes de réponse."""
    textes, _ = traiter_entrant_complet(fabrique, deps, entrant)
    return textes


def traiter_entrant_complet(fabrique: sessionmaker[Session], deps: pipeline.Dependances, entrant: MessageEntrant, repondre: bool = True) -> tuple[list[str], list[str]]:
    """Comme traiter_entrant, avec les documents (chemins). `repondre=False` : l'appelant (appli web) affiche lui-même les réponses."""
    with fabrique() as session:
        if session.scalar(select(Message.id).where(Message.wamid == entrant.wamid)) is not None:
            return [], []  # webhook rejoué : aucune action en double
        message = Message(
            numero=entrant.numero, direction="entrant", wamid=entrant.wamid, type=entrant.type, texte=entrant.texte,
            media_id=entrant.media_id, heure_envoi=entrant.heure_envoi, heure_reception=deps.horloge.maintenant(),
        )
        session.add(message)
        session.flush()
        pme = pme_par_numero(session, entrant.numero)
        message.pme_id = pme.id if pme else None
        if entrant.type == "autre":
            textes, documents, envois = ["Pour l'instant je comprends les messages écrits et les vocaux."], [], []
        else:
            res = pipeline.traiter(session, deps, message)
            textes, documents, envois = res.textes, res.documents, res.envois
        session.commit()

    textes = list(textes)
    simule = isinstance(deps.canal, CanalFactice)
    for envoi in envois:  # messages vers les clients, après confirmation de la PME
        try:
            wamid = deps.canal.envoyer(envoi.message)
            textes.append(reponses.envoi_ok(envoi.destinataire, simule))
        except Exception:  # noqa: BLE001
            wamid = None
            textes.append(reponses.envoi_echec(envoi.destinataire))
        _tracer(fabrique, deps, envoi.pme_id, envoi.message.numero, envoi.message.texte or envoi.message.document, wamid)

    if repondre:
        for texte in textes:
            _envoyer(fabrique, deps, entrant.numero, texte=texte)
        for doc in documents:
            _envoyer(fabrique, deps, entrant.numero, document=doc)
    return textes, documents


def _tracer(fabrique: sessionmaker[Session], deps: pipeline.Dependances, pme_id: int | None, numero: str, texte: str | None, wamid: str | None) -> None:
    with fabrique() as session:
        maintenant = deps.horloge.maintenant()
        session.add(Message(pme_id=pme_id, numero=numero, direction="sortant", wamid=wamid, type="texte", texte=texte, heure_envoi=maintenant, heure_reception=maintenant))
        session.commit()


def _envoyer(fabrique: sessionmaker[Session], deps: pipeline.Dependances, numero: str, texte: str | None = None, document: str | None = None) -> None:
    try:
        wamid = deps.canal.envoyer(MessageSortant(numero=numero, texte=texte, document=document))
    except Exception:  # noqa: BLE001 - l'échec d'envoi est journalisé, jamais bloquant
        wamid = None
    with fabrique() as session:
        pme = pme_par_numero(session, numero)
        maintenant = deps.horloge.maintenant()
        session.add(Message(pme_id=pme.id if pme else None, numero=numero, direction="sortant", wamid=wamid, type="document" if document else "texte", texte=texte or document, heure_envoi=maintenant, heure_reception=maintenant))
        session.commit()
