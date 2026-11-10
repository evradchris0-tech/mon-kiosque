"""Annulation de la dernière action, dans la fenêtre de 10 minutes."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import Action, Client, Facture, Paiement, Pme, Produit, Vente
from app.domaine import factures as dom_factures
from app.domaine import paiements as dom_paiements
from app.domaine import ventes as dom_ventes


def derniere_annulable(session: Session, pme: Pme, horloge: Horloge) -> Action | None:
    maintenant = horloge.maintenant()
    return session.scalar(
        select(Action)
        .where(
            Action.pme_id == pme.id,
            Action.annulee.is_(False),
            Action.annulable_jusqua.is_not(None),
            Action.annulable_jusqua >= maintenant,
        )
        .order_by(Action.creee_a.desc(), Action.id.desc())
        .limit(1)
    )


def annuler(session: Session, pme: Pme, action: Action, horloge: Horloge) -> str:
    """Annule l'action et renvoie son résumé. Vérifie l'appartenance à la PME."""
    if action.pme_id != pme.id:
        raise PermissionError("action d'une autre PME")
    if action.type == "VENTE":
        vente = session.get(Vente, action.cible_id)
        if vente is not None and vente.pme_id == pme.id:
            dom_ventes.annuler(session, vente)
    elif action.type == "FACTURE":
        facture = session.get(Facture, action.cible_id)
        if facture is not None and facture.pme_id == pme.id:
            dom_factures.annuler(session, facture)
    elif action.type == "PAIEMENT_RECU":
        paiement = session.get(Paiement, action.cible_id)
        if paiement is not None and paiement.pme_id == pme.id:
            dom_paiements.annuler(session, paiement, horloge)
    elif action.type == "PRODUIT":
        produit = session.get(Produit, action.cible_id)
        if produit is not None and produit.pme_id == pme.id:
            produit.actif = False
    elif action.type == "CLIENT":
        client = session.get(Client, action.cible_id)
        if client is not None and client.pme_id == pme.id:
            client.actif = False
    else:
        raise ValueError(f"type d'action inconnu : {action.type}")
    action.annulee = True
    session.flush()
    return action.resume
