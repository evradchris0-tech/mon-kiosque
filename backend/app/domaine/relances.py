"""Relances : rédaction par gabarit, plafonds, enregistrement après confirmation."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import Client, Facture, Pme, Relance
from app.domaine import factures as dom_factures
from app.moki import reponses

PLAFOND_PAR_CLIENT_PAR_SEMAINE = 1
PLAFOND_PAR_PME_PAR_JOUR = 20


def rediger(pme: Pme, client: Client, facture: Facture, horloge: Horloge) -> str:
    return reponses.relance_texte(
        pme.nom_commerce, client.nom, facture.numero, facture.total,
        dom_factures.jours_de_retard(facture, horloge),
    )


def plafond_atteint(session: Session, pme: Pme, client: Client, horloge: Horloge) -> str | None:
    maintenant = horloge.maintenant()
    par_client = session.scalar(
        select(func.count(Relance.id)).where(
            Relance.pme_id == pme.id,
            Relance.client_id == client.id,
            Relance.envoyee_a >= maintenant - timedelta(days=7),
        )
    )
    if int(par_client or 0) >= PLAFOND_PAR_CLIENT_PAR_SEMAINE:
        return "client"
    par_pme = session.scalar(
        select(func.count(Relance.id)).where(
            Relance.pme_id == pme.id, Relance.envoyee_a >= maintenant - timedelta(days=1)
        )
    )
    if int(par_pme or 0) >= PLAFOND_PAR_PME_PAR_JOUR:
        return "pme"
    return None


def enregistrer(
    session: Session,
    pme: Pme,
    horloge: Horloge,
    *,
    facture: Facture,
    client: Client,
    texte: str,
    confirmation_id: int,
    mode: str = "transfert",
) -> Relance:
    """Une relance ne s'enregistre que confirmée et sur une facture encore ouverte."""
    if confirmation_id is None:
        raise ValueError("une relance ne s'enregistre pas sans confirmation")
    if facture.statut not in dom_factures.STATUTS_OUVERTS:
        raise ValueError("la facture n'est plus ouverte : pas de relance")
    relance = Relance(
        pme_id=pme.id,
        facture_id=facture.id,
        client_id=client.id,
        mode=mode,
        texte=texte,
        confirmation_id=confirmation_id,
        envoyee_a=horloge.maintenant(),
    )
    session.add(relance)
    session.flush()
    return relance
