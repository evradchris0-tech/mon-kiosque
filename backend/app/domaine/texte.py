"""Normalisation de texte pour rapprocher noms de clients, produits et numéros."""

from __future__ import annotations

import re
import unicodedata

TITRES = {"mme", "madame", "m", "mr", "monsieur", "mlle", "mademoiselle", "le", "la", "les", "de"}


def sans_accents(texte: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn"
    )


def normaliser(texte: str) -> str:
    t = sans_accents(texte).lower()
    t = re.sub(r"[^a-z0-9\s-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens_nom(texte: str) -> set[str]:
    """Jetons significatifs d'un nom (sans titres ni mots vides)."""
    return {t for t in normaliser(texte).replace("-", " ").split() if t not in TITRES}


def singulier(mot: str) -> str:
    return mot[:-1] if len(mot) > 3 and mot.endswith("s") else mot


def normaliser_telephone(texte: str) -> str | None:
    """'6 77 12 34 56' -> '237677123456' ; '+237 6 77 12 34 56' -> '237677123456'."""
    chiffres = re.sub(r"\D", "", texte)
    if len(chiffres) == 9 and chiffres[0] in "62":
        return "237" + chiffres
    if len(chiffres) == 12 and chiffres.startswith("237"):
        return chiffres
    if len(chiffres) == 13 and chiffres.startswith("00237"):
        return chiffres[2:]
    return None
