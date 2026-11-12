"""Dépenses : charges du commerce, achats de stock, retraits personnels (jamais des charges)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import Action, Depense, Pme
from app.domaine import ventes as dom_ventes


def enregistrer(session: Session, pme: Pme, horloge: Horloge, *, libelle: str, montant: int, type_: str, nature: str, heure_envoi: datetime, message_id: int | None = None) -> Depense:
    if montant <= 0:
        raise ValueError("le montant d'une dépense doit être positif")
    if nature == "perso":
        type_ = "retrait_perso"  # règle C2 : un retrait perso n'est jamais une charge du commerce
    maintenant = horloge.maintenant()
    dep = Depense(pme_id=pme.id, libelle=libelle, montant=montant, type=type_, nature=nature, heure_envoi=heure_envoi, heure_reception=maintenant, statut="active", message_id=message_id)
    session.add(dep)
    session.flush()
    session.add(Action(pme_id=pme.id, type="DEPENSE", cible_id=dep.id, resume=f"dépense de {montant} F ({libelle})", creee_a=maintenant, annulable_jusqua=maintenant + dom_ventes.FENETRE_ANNULATION))
    session.flush()
    return dep


def derniere(session: Session, pme: Pme, horloge: Horloge) -> Depense | None:
    """Dernière dépense saisie dans la dernière heure (on ne modifie jamais une dépense ancienne par un simple « c'est perso »)."""
    depuis = horloge.maintenant() - timedelta(hours=1)
    return session.scalar(select(Depense).where(Depense.pme_id == pme.id, Depense.statut == "active", Depense.heure_reception >= depuis).order_by(Depense.id.desc()).limit(1))


def changer_nature(session: Session, dep: Depense, nature: str) -> None:
    dep.nature = nature
    if nature == "perso":
        dep.type = "retrait_perso"
    elif dep.type == "retrait_perso":
        dep.type = "charge"
    session.flush()


def annuler(session: Session, dep: Depense) -> None:
    dep.statut = "annulee"
    session.flush()
