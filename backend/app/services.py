"""Assemblage des dépendances selon la configuration, et traitement d'un message entrant."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Parametres
from app.core.horloge import Horloge, HorlogeSysteme
from app.db.modeles import Message
from app.integrations.llm.factice import InterpreteRegles
from app.integrations.llm.interface import ContexteInterpretation, Interprete, ResultatInterpretation
from app.integrations.stt.interface import Transcripteur, TranscripteurFactice
from app.integrations.whatsapp.interface import CanalFactice, CanalMessages, MessageEntrant, MessageSortant
from app.moki import pipeline


class _InterpreteRegles:
    def __init__(self) -> None:
        self._r = InterpreteRegles()

    def interpreter(self, contexte: ContexteInterpretation, texte: str) -> ResultatInterpretation:
        return self._r.interpreter(contexte, texte)


def construire_dependances(p: Parametres, horloge: Horloge | None = None, canal: CanalMessages | None = None) -> pipeline.Dependances:
    interprete: Interprete
    if p.interprete == "claude":
        from app.integrations.llm.claude import InterpreteClaude

        interprete = InterpreteClaude(p.modele, p.effort)
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
    """Persiste (idempotent sur wamid), traite, envoie les réponses. Renvoie les textes envoyés."""
    with fabrique() as session:
        deja = session.scalar(select(Message.id).where(Message.wamid == entrant.wamid))
        if deja is not None:
            return []  # webhook rejoué : aucune action en double
        message = Message(
            numero=entrant.numero, direction="entrant", wamid=entrant.wamid, type=entrant.type, texte=entrant.texte,
            media_id=entrant.media_id, heure_envoi=entrant.heure_envoi, heure_reception=deps.horloge.maintenant(),
        )
        session.add(message)
        session.flush()
        if entrant.type == "autre":
            textes = ["Pour l'instant je comprends les messages écrits et les vocaux."]
            resultat_textes, documents = textes, []
        else:
            res = pipeline.traiter(session, deps, message)
            resultat_textes, documents = res.textes, res.documents
        session.commit()

    envoyes: list[str] = []
    for texte in resultat_textes:
        _envoyer(fabrique, deps, entrant.numero, texte=texte)
        envoyes.append(texte)
    for doc in documents:
        _envoyer(fabrique, deps, entrant.numero, document=doc)
    return envoyes


def _envoyer(fabrique: sessionmaker[Session], deps: pipeline.Dependances, numero: str, texte: str | None = None, document: str | None = None) -> None:
    try:
        wamid = deps.canal.envoyer(MessageSortant(numero=numero, texte=texte, document=document))
    except Exception:  # noqa: BLE001 - l'échec d'envoi est journalisé, jamais bloquant
        wamid = None
    with fabrique() as session:
        maintenant = deps.horloge.maintenant()
        session.add(Message(numero=numero, direction="sortant", wamid=wamid, type="document" if document else "texte", texte=texte or document, heure_envoi=maintenant, heure_reception=maintenant))
        session.commit()
