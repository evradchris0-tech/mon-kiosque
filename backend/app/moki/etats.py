"""Machine à états de la conversation (une par PME). Voir plan complet §2.4."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import Confirmation, Conversation, Pme

LIBRE = "LIBRE"
ATTEND_PRECISION = "ATTEND_PRECISION"
ATTEND_CONFIRMATION = "ATTEND_CONFIRMATION"
ATTEND_CONFIRMATION_RENFORCEE = "ATTEND_CONFIRMATION_RENFORCEE"
SUSPENDU_HUMAIN = "SUSPENDU_HUMAIN"

EXPIRATION = timedelta(minutes=30)


def charger(session: Session, pme: Pme, horloge: Horloge) -> tuple[Conversation, bool]:
    """Renvoie (conversation, une_action_vient_d_expirer)."""
    maintenant = horloge.maintenant()
    conv = session.scalar(select(Conversation).where(Conversation.pme_id == pme.id))
    if conv is None:
        conv = Conversation(pme_id=pme.id, etat=LIBRE, mise_a_jour=maintenant)
        session.add(conv)
        session.flush()
        return conv, False
    expiree = False
    if conv.etat in (ATTEND_PRECISION, ATTEND_CONFIRMATION, ATTEND_CONFIRMATION_RENFORCEE) and (
        conv.expire_a is not None and conv.expire_a < maintenant
    ):
        if conv.confirmation_id:
            confirmation = session.get(Confirmation, conv.confirmation_id)
            if confirmation is not None and confirmation.statut == "en_attente":
                confirmation.statut = "expiree"
        liberer(session, conv, horloge)
        expiree = True
    return conv, expiree


def mettre_en_attente(
    session: Session,
    conv: Conversation,
    horloge: Horloge,
    *,
    etat: str,
    action: dict[str, Any],
    question: str,
    mot: str | None = None,
    confirmation_id: int | None = None,
) -> None:
    maintenant = horloge.maintenant()
    conv.etat = etat
    conv.action_en_attente = action
    conv.question_en_attente = question
    conv.mot_confirmation = mot
    conv.confirmation_id = confirmation_id
    conv.expire_a = maintenant + EXPIRATION
    conv.mise_a_jour = maintenant
    session.flush()


def liberer(session: Session, conv: Conversation, horloge: Horloge) -> None:
    conv.etat = LIBRE
    conv.action_en_attente = None
    conv.question_en_attente = None
    conv.mot_confirmation = None
    conv.confirmation_id = None
    conv.expire_a = None
    conv.mise_a_jour = horloge.maintenant()
    session.flush()


def suspendre_pour_humain(session: Session, conv: Conversation, horloge: Horloge) -> None:
    liberer(session, conv, horloge)
    conv.etat = SUSPENDU_HUMAIN
    session.flush()


def reprendre(session: Session, conv: Conversation, horloge: Horloge) -> None:
    liberer(session, conv, horloge)
