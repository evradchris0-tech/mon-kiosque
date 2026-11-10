"""Reconnaissance des réponses oui / non / mot de confirmation, sans modèle de langage."""

from __future__ import annotations

import re
import secrets
from enum import StrEnum

MOTS_CONFIRMATION = (
    "MANGUE",
    "PAPAYE",
    "GOYAVE",
    "ANANAS",
    "BANANE",
    "SAFOU",
    "COROSSOL",
    "AVOCAT",
    "PASTEQUE",
    "CITRON",
)


class Reponse(StrEnum):
    OUI = "OUI"
    NON = "NON"
    INCONNU = "INCONNU"


_OUI = re.compile(
    r"^(oui|ouais|ok|okay|okey|yes|yep|d'?accord|vas-?y|go|c'?est bon|confirme|confirmé|"
    r"je confirme|envoie|envoi|valide|validé|bien sûr|bien sur)\b"
)
_NON = re.compile(r"^(non|no|nope|laisse|annule|annuler|stop|pas maintenant|attends|attend)\b")


def _nettoyer(texte: str) -> str:
    t = texte.strip().lower()
    t = re.sub(r"[\s!.,;:?]+$", "", t)
    t = re.sub(r"^[\s!.,;:?]+", "", t)
    return t


def lire(texte: str) -> Reponse:
    t = _nettoyer(texte)
    if not t:
        return Reponse.INCONNU
    if _NON.match(t):
        return Reponse.NON
    if _OUI.match(t):
        return Reponse.OUI
    return Reponse.INCONNU


def lire_renforcee(texte: str, mot_attendu: str) -> Reponse:
    t = _nettoyer(texte)
    if t == mot_attendu.strip().lower():
        return Reponse.OUI
    if _NON.match(t):
        return Reponse.NON
    return Reponse.INCONNU


def mot_aleatoire() -> str:
    return secrets.choice(MOTS_CONFIRMATION)
