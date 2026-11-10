"""Catalogue produits."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.modeles import Pme, Produit
from app.domaine.texte import normaliser, singulier


def tous(session: Session, pme: Pme) -> list[Produit]:
    return list(
        session.scalars(
            select(Produit).where(Produit.pme_id == pme.id, Produit.actif.is_(True)).order_by(Produit.nom)
        )
    )


def rechercher(session: Session, pme: Pme, nom: str) -> Produit | None:
    cible = " ".join(singulier(m) for m in normaliser(nom).split())
    for produit in tous(session, pme):
        for candidat in [produit.nom, *(produit.alias or [])]:
            if " ".join(singulier(m) for m in normaliser(candidat).split()) == cible:
                return produit
    return None


def ajouter_ou_mettre_a_jour(
    session: Session, pme: Pme, nom: str, prix: int, unite: str | None = None
) -> tuple[Produit, bool]:
    """Renvoie (produit, cree). Si le produit existe déjà, son prix est mis à jour."""
    existant = rechercher(session, pme, nom)
    if existant is not None:
        existant.prix = prix
        if unite:
            existant.unite = unite
        session.flush()
        return existant, False
    produit = Produit(pme_id=pme.id, nom=nom.strip(), prix=prix, unite=unite, alias=[])
    session.add(produit)
    session.flush()
    return produit, True
