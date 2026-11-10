"""Interface du modèle de langage : il interprète, il n'exécute rien."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.moki.schemas import Interpretation


@dataclass
class ContexteInterpretation:
    """Ce que le modèle sait de la PME au moment du message. Jamais de secret."""

    date_locale: str
    nom_commerce: str
    etat_conversation: str = "LIBRE"
    action_en_attente: dict[str, Any] | None = None
    question_en_attente: str | None = None
    derniers_echanges: list[tuple[str, str]] = field(default_factory=list)  # (direction, texte)
    produits: list[tuple[str, int]] = field(default_factory=list)  # (nom, prix)
    clients: list[str] = field(default_factory=list)  # "Nom (quartier)"
    factures_ouvertes: list[tuple[int, str, int]] = field(default_factory=list)  # (numéro, client, total)


@dataclass
class ResultatInterpretation:
    interpretation: Interpretation
    modele: str
    tokens_entree: int = 0
    tokens_sortie: int = 0
    tokens_cache: int = 0
    cout_estime: float | None = None
    brut: dict[str, Any] | None = None


class ErreurInterprete(Exception):
    """Le modèle n'a pas pu répondre (réseau, refus, sortie invalide)."""


class Interprete(Protocol):
    def interpreter(self, contexte: ContexteInterpretation, texte: str) -> ResultatInterpretation: ...
