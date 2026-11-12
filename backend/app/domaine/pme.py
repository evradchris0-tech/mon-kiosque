"""PME et numéros autorisés."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import Inscription, NumeroAutorise, Pme


class ErreurValidation(ValueError):
    """Valeur refusée : le message est affiché tel quel à la gérante (français)."""


class DejaInscrit(Exception):
    """Le numéro a déjà un compte (un numéro = un compte)."""



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


CHAMPS_INSCRIPTION = {"nom_commerce": ("Le nom du commerce", 120), "ville": ("La ville", 60), "secteur": ("Le secteur", 40)}


def valider_inscription(corps: Any) -> dict[str, str]:
    """Les trois champs de l'inscription, obligatoires, texte non vide dans la limite de la colonne."""
    if not isinstance(corps, dict):
        raise ErreurValidation("Il faut le nom du commerce, la ville et le secteur.")
    valeurs: dict[str, str] = {}
    for cle, (libelle, maximum) in CHAMPS_INSCRIPTION.items():
        brut = corps.get(cle)
        texte = brut.strip() if isinstance(brut, str) else ""
        if not texte:
            raise ErreurValidation(f"{libelle} est obligatoire.")
        if len(texte) > maximum:
            raise ErreurValidation(f"{libelle} est trop long ({maximum} caractères au maximum).")
        valeurs[cle] = texte
    return valeurs


def inscrire(session: Session, horloge: Horloge, numero: str, valeurs: dict[str, str]) -> Pme:
    """Crée la PME du numéro (celui du jeton). DejaInscrit si le numéro a déjà un compte."""
    if session.scalar(select(Pme.id).where(Pme.numero_whatsapp == numero)) or session.scalar(select(NumeroAutorise.id).where(NumeroAutorise.numero == numero)):
        raise DejaInscrit(numero)
    pme = creer_pme(session, horloge, nom_commerce=valeurs["nom_commerce"], numero_whatsapp=numero, ville=valeurs["ville"], secteur=valeurs["secteur"])
    en_cours = session.scalar(select(Inscription).where(Inscription.numero == numero))
    if en_cours is not None:  # inscription commencée sur WhatsApp : elle est remplacée
        session.delete(en_cours)
    session.flush()
    return pme
