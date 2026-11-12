"""Préférences d'une PME (table `preferences`) et réglages modifiables depuis l'interface."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.modeles import Pme, Preference
from app.domaine.pme import ErreurValidation

DEFAUTS: dict[str, Any] = {"resume_du_soir": True, "rappels_fiscaux": True}
CLE_ALERTES_LUES = "alertes_lues_jusqua"

MODES_RELANCE = ("transfert", "direct")
SEUIL_MIN, SEUIL_MAX = 1_000, 10_000_000
LONGUEURS_COMMERCE = {"nom_commerce": 120, "nom_gerante": 120, "ville": 60, "quartier": 60, "secteur": 40}  # tailles des colonnes
LIBELLES_COMMERCE = {"nom_commerce": "Le nom du commerce", "nom_gerante": "Ton nom", "ville": "La ville", "quartier": "Le quartier", "secteur": "Le secteur"}
PREFERENCES_MODIFIABLES = ("mode_relance", "seuil_confirmation_renforcee", "resume_du_soir", "rappels_fiscaux")


def lire(session: Session, pme: Pme, cle: str) -> Any:
    ligne = session.scalar(select(Preference).where(Preference.pme_id == pme.id, Preference.cle == cle))
    if ligne is None:
        return DEFAUTS.get(cle)
    return ligne.valeur


def ecrire(session: Session, pme: Pme, cle: str, valeur: Any) -> None:
    ligne = session.scalar(select(Preference).where(Preference.pme_id == pme.id, Preference.cle == cle))
    if ligne is None:
        session.add(Preference(pme_id=pme.id, cle=cle, valeur=valeur))
    else:
        ligne.valeur = valeur
    session.flush()


def actif(session: Session, pme: Pme, cle: str) -> bool:
    return bool(lire(session, pme, cle))


def alertes_lues_jusqua(session: Session, pme: Pme) -> datetime | None:
    brut = lire(session, pme, CLE_ALERTES_LUES)
    if not brut:
        return None
    try:
        return datetime.fromisoformat(str(brut)).replace(tzinfo=None)
    except ValueError:
        return None


def marquer_alertes_lues(session: Session, pme: Pme, instant: datetime) -> None:
    ecrire(session, pme, CLE_ALERTES_LUES, instant.replace(microsecond=0).isoformat())


def vue(session: Session, pme: Pme) -> dict:
    """Forme exacte de GET /api/parametres."""
    return {
        "commerce": {
            "nom_commerce": pme.nom_commerce,
            "nom_gerante": pme.nom_gerante,
            "ville": pme.ville,
            "quartier": pme.quartier,
            "secteur": pme.secteur,
            "numero": pme.numero_whatsapp,
        },
        "preferences": {
            "mode_relance": pme.mode_relance,
            "seuil_confirmation_renforcee": pme.seuil_confirmation_renforcee,
            "resume_du_soir": actif(session, pme, "resume_du_soir"),
            "rappels_fiscaux": actif(session, pme, "rappels_fiscaux"),
        },
        "demo": pme.donnees_fictives,
    }


def _objet(valeur: Any, nom: str) -> dict:
    if not isinstance(valeur, dict):
        raise ErreurValidation(f"« {nom} » doit être un objet.")
    return valeur


def valider_commerce(brut: Any) -> dict[str, str | None]:
    """Champs du commerce acceptés ; toute autre clé (numéro, statut, identifiant…) est refusée."""
    valeurs: dict[str, str | None] = {}
    for cle, valeur in _objet(brut, "commerce").items():
        if cle not in LONGUEURS_COMMERCE:
            raise ErreurValidation(f"Le champ « {cle} » ne peut pas être modifié ici.")
        libelle = LIBELLES_COMMERCE[cle]
        if not isinstance(valeur, str):
            raise ErreurValidation(f"{libelle} doit être un texte.")
        texte = valeur.strip()
        if len(texte) > LONGUEURS_COMMERCE[cle]:
            raise ErreurValidation(f"{libelle} est trop long ({LONGUEURS_COMMERCE[cle]} caractères au maximum).")
        if not texte and cle == "nom_commerce":
            raise ErreurValidation("Le nom du commerce ne peut pas être vide.")
        valeurs[cle] = texte or None
    return valeurs


def valider_preferences(brut: Any) -> dict[str, Any]:
    valeurs: dict[str, Any] = {}
    for cle, valeur in _objet(brut, "preferences").items():
        if cle not in PREFERENCES_MODIFIABLES:
            raise ErreurValidation(f"La préférence « {cle} » n'existe pas.")
        if cle == "mode_relance":
            if valeur not in MODES_RELANCE:
                raise ErreurValidation("Le mode d'envoi doit être « transfert » ou « direct ».")
        elif cle == "seuil_confirmation_renforcee":
            if isinstance(valeur, bool) or not isinstance(valeur, int) or not SEUIL_MIN <= valeur <= SEUIL_MAX:
                raise ErreurValidation("Le seuil de confirmation doit être un nombre entier de francs entre 1 000 et 10 000 000.")
        elif not isinstance(valeur, bool):
            raise ErreurValidation("Cette option se règle par oui ou non.")
        valeurs[cle] = valeur
    return valeurs


def valider(corps: Any) -> tuple[dict[str, str | None], dict[str, Any]]:
    """Valide tout le corps du PUT avant d'appliquer quoi que ce soit."""
    corps = _objet(corps if corps is not None else {}, "corps")
    for cle in corps:
        if cle not in ("commerce", "preferences"):
            raise ErreurValidation(f"Le champ « {cle} » ne peut pas être modifié ici.")
    commerce = valider_commerce(corps["commerce"]) if "commerce" in corps else {}
    preferences = valider_preferences(corps["preferences"]) if "preferences" in corps else {}
    return commerce, preferences


def appliquer(session: Session, pme: Pme, commerce: dict[str, str | None], preferences: dict[str, Any]) -> None:
    for cle, valeur in commerce.items():
        setattr(pme, cle, valeur)
    for cle, valeur in preferences.items():
        if cle in ("mode_relance", "seuil_confirmation_renforcee"):
            setattr(pme, cle, valeur)
        else:
            ecrire(session, pme, cle, valeur)
    session.flush()
