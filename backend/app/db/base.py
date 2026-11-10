"""Base déclarative et fabrique de sessions."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def creer_moteur(url: str) -> Engine:
    if url.startswith("sqlite"):
        # Un seul pool partagé pour que la base mémoire survive aux connexions.
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if ":memory:" in url else None,
        )
    return create_engine(url, pool_pre_ping=True)


def fabrique_sessions(moteur: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=moteur, expire_on_commit=False)


@contextmanager
def session_transaction(fabrique: sessionmaker[Session]) -> Iterator[Session]:
    session = fabrique()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
