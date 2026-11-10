"""PME et numéros autorisés."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import NumeroAutorise, Pme


def creer_pme(
    session: Session,
    horloge: Horloge,
    *,
    nom_commerce: str,
    numero_whatsapp: str,
    nom_gerante: str | None = None,
    secteur: str | None = None,
    ville: str | None = None,
    quartier: str | None = None,
    fuseau: str = "Africa/Douala",
    seuil_confirmation_renforcee: int = 50_000,
) -> Pme:
    pme = Pme(
        nom_commerce=nom_commerce,
        nom_gerante=nom_gerante,
        numero_whatsapp=numero_whatsapp,
        secteur=secteur,
        ville=ville,
        quartier=quartier,
        fuseau=fuseau,
        seuil_confirmation_renforcee=seuil_confirmation_renforcee,
        date_inscription=horloge.maintenant(),
    )
    session.add(pme)
    session.flush()
    session.add(NumeroAutorise(pme_id=pme.id, numero=numero_whatsapp, role="gerante", actif=True))
    session.flush()
    return pme


def pme_par_numero(session: Session, numero: str) -> Pme | None:
    """Résout l'expéditeur : seuls les numéros autorisés et actifs donnent accès à une PME."""
    autorise = session.scalar(
        select(NumeroAutorise).where(
            NumeroAutorise.numero == numero, NumeroAutorise.actif.is_(True)
        )
    )
    if autorise is None:
        return None
    pme = session.get(Pme, autorise.pme_id)
    if pme is None or pme.statut != "actif":
        return None
    return pme


def ajouter_numero(session: Session, pme: Pme, numero: str, role: str = "employe") -> NumeroAutorise:
    n = NumeroAutorise(pme_id=pme.id, numero=numero, role=role, actif=True)
    session.add(n)
    session.flush()
    return n
