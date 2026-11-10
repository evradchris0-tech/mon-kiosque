"""Canal de messages : interface, messages normalisés, implémentation factice."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class MessageEntrant:
    """Message reçu, déjà normalisé (indépendant du fournisseur)."""

    wamid: str
    numero: str
    type: str  # texte | audio | autre
    heure_envoi: datetime  # UTC naïf, heure d'envoi côté expéditeur
    texte: str | None = None
    media_id: str | None = None


@dataclass
class MessageSortant:
    numero: str
    texte: str | None = None
    document: str | None = None  # chemin local du fichier à joindre
    modele: str | None = None  # nom du message à modèle (hors fenêtre de 24 h)
    parametres_modele: list[str] = field(default_factory=list)


class ErreurCanal(Exception):
    pass


class CanalMessages(Protocol):
    def envoyer(self, message: MessageSortant) -> str:
        """Envoie et renvoie l'identifiant fournisseur du message."""
        ...

    def telecharger_media(self, media_id: str) -> bytes: ...


class CanalFactice:
    def __init__(self) -> None:
        self.envoyes: list[MessageSortant] = []
        self.medias: dict[str, bytes] = {}
        self.panne = False
        self._compteur = 0

    def envoyer(self, message: MessageSortant) -> str:
        if self.panne:
            raise ErreurCanal("panne simulée du canal")
        self.envoyes.append(message)
        self._compteur += 1
        return f"wamid.factice.{self._compteur}"

    def telecharger_media(self, media_id: str) -> bytes:
        return self.medias.get(media_id, b"")

    def textes(self, numero: str | None = None) -> list[str]:
        return [m.texte for m in self.envoyes if m.texte and (numero is None or m.numero == numero)]

    def vider(self) -> None:
        self.envoyes.clear()
