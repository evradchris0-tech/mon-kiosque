"""Transcription vocale : interface et implémentation factice.

L'implémentation réelle sera choisie sur banc d'essai (tâche P0-10) ; elle recevra
l'audio OGG téléchargé via le canal WhatsApp.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Transcription:
    texte: str
    confiance: float
    duree_s: float = 0.0


class ErreurTranscription(Exception):
    pass


class Transcripteur(Protocol):
    def transcrire(self, audio: bytes, media_id: str | None = None) -> Transcription: ...


class TranscripteurFactice:
    """Renvoie la transcription programmée pour un media_id ; sinon un texte par défaut."""

    def __init__(self, transcriptions: dict[str, Transcription] | None = None) -> None:
        self.transcriptions = dict(transcriptions or {})
        self.panne = False

    def programmer(self, media_id: str, texte: str, confiance: float = 0.9) -> None:
        self.transcriptions[media_id] = Transcription(texte=texte, confiance=confiance)

    def transcrire(self, audio: bytes, media_id: str | None = None) -> Transcription:
        if self.panne:
            raise ErreurTranscription("panne simulée de la transcription")
        if media_id and media_id in self.transcriptions:
            return self.transcriptions[media_id]
        return Transcription(texte="", confiance=0.0)
