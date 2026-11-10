"""Montants en francs CFA : entiers, jamais de décimales, formatage unique."""

from __future__ import annotations

import re

ESPACE_FINE = " "


def format_fcfa(montant: int) -> str:
    """15000 -> '15 000 F' (espace fine insécable comme séparateur de milliers)."""
    if not isinstance(montant, int):
        raise TypeError("un montant est un entier de francs CFA")
    signe = "-" if montant < 0 else ""
    chiffres = f"{abs(montant):,}".replace(",", ESPACE_FINE)
    return f"{signe}{chiffres} F"


_K = re.compile(r"^(\d+(?:[.,]\d+)?)\s*k$", re.IGNORECASE)


def lire_montant(texte: str) -> int | None:
    """Lit un montant écrit par une PME : '5000', '5 000', '5.000', '10k', '2,5k'.

    Renvoie None si le texte n'est pas un montant.
    """
    t = texte.strip().lower().replace("f", "").replace("cfa", "").strip()
    m = _K.match(t)
    if m:
        return round(float(m.group(1).replace(",", ".")) * 1000)
    t = re.sub(r"[\s. ]", "", t)
    if t.isdigit():
        return int(t)
    return None
