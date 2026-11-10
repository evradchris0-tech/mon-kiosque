"""Horloge injectable.

Convention du projet : toutes les dates en base sont en UTC, naïves (sans tzinfo).
L'affichage et les calculs de période utilisent le fuseau de la PME (Africa/Douala
par défaut).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo


class Horloge(Protocol):
    def maintenant(self) -> datetime:
        """Instant courant, UTC naïf."""
        ...


class HorlogeSysteme:
    def maintenant(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)


class HorlogeFixe:
    """Horloge pilotée par les tests."""

    def __init__(self, instant: datetime) -> None:
        self._instant = instant.replace(tzinfo=None)

    def maintenant(self) -> datetime:
        return self._instant

    def avancer(self, **kwargs: int) -> None:
        self._instant = self._instant + timedelta(**kwargs)

    def fixer(self, instant: datetime) -> None:
        self._instant = instant.replace(tzinfo=None)


def en_local(instant_utc: datetime, fuseau: str) -> datetime:
    """Convertit un instant UTC naïf en datetime conscient dans le fuseau donné."""
    return instant_utc.replace(tzinfo=UTC).astimezone(ZoneInfo(fuseau))


def en_utc(instant_local: datetime) -> datetime:
    """Convertit un datetime conscient en UTC naïf."""
    if instant_local.tzinfo is None:
        raise ValueError("instant_local doit être conscient (tzinfo)")
    return instant_local.astimezone(UTC).replace(tzinfo=None)
