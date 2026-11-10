"""Construit le contexte fourni au modèle de langage. Aucune donnée d'une autre PME."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge, en_local
from app.db.modeles import Client, Conversation, Message, Pme
from app.domaine import clients as dom_clients
from app.domaine import factures as dom_factures
from app.domaine import produits as dom_produits
from app.integrations.llm.interface import ContexteInterpretation

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def construire(session: Session, pme: Pme, conv: Conversation, horloge: Horloge) -> ContexteInterpretation:
    local = en_local(horloge.maintenant(), pme.fuseau)
    date_locale = f"{JOURS[local.weekday()]} {local.strftime('%d/%m/%Y %H:%M')}"

    echanges = list(
        session.scalars(
            select(Message)
            .where(Message.pme_id == pme.id)
            .order_by(Message.heure_reception.desc(), Message.id.desc())
            .limit(10)
        )
    )
    derniers = [
        (m.direction, (m.texte or m.transcription or "")[:300]) for m in reversed(echanges)
    ]

    factures = []
    for f in dom_factures.ouvertes(session, pme):
        client = session.scalar(select(Client).where(Client.id == f.client_id, Client.pme_id == pme.id))
        factures.append((f.numero, client.nom if client else "?", f.total))

    return ContexteInterpretation(
        date_locale=date_locale,
        nom_commerce=pme.nom_commerce,
        etat_conversation=conv.etat,
        action_en_attente=conv.action_en_attente,
        question_en_attente=conv.question_en_attente,
        derniers_echanges=derniers,
        produits=[(p.nom, p.prix) for p in dom_produits.tous(session, pme)],
        clients=[dom_clients.libelle(c) for c in dom_clients.tous(session, pme)],
        factures_ouvertes=factures,
    )
