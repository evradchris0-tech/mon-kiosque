"""Accès à la base pour l'application (API et workers)."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import parametres
from app.db.base import creer_moteur, fabrique_sessions


@lru_cache
def fabrique() -> sessionmaker[Session]:
    return fabrique_sessions(creer_moteur(parametres().database_url))
