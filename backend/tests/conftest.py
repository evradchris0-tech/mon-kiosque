"""Fixtures : base SQLite en mémoire, horloge fixe, intégrations factices."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.core.config import Parametres
from app.core.horloge import HorlogeFixe
from app.db import modeles  # noqa: F401 - enregistre les tables
from app.db.base import Base, creer_moteur, fabrique_sessions
from app.db.modeles import Message
from app.domaine import pme as dom_pme
from app.integrations.llm.factice import InterpreteRegles, InterpreteScripte
from app.integrations.stt.interface import TranscripteurFactice
from app.integrations.whatsapp.interface import CanalFactice
from app.moki import pipeline

NUM_A = "237677000001"
NUM_B = "237677000002"


class Banc:
    """Petit banc de test : envoie des messages comme une PME et lit les réponses."""

    def __init__(self, tmp_path) -> None:
        self.moteur = creer_moteur("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.moteur)
        self.fabrique = fabrique_sessions(self.moteur)
        self.horloge = HorlogeFixe(datetime(2026, 11, 10, 9, 0))  # 10h locale à Douala
        self.interprete = InterpreteScripte(par_defaut=lambda c, t: InterpreteRegles().interpreter(c, t).interpretation)
        self.transcripteur = TranscripteurFactice()
        self.canal = CanalFactice()
        self.deps = pipeline.Dependances(
            interprete=self.interprete,
            transcripteur=self.transcripteur,
            canal=self.canal,
            horloge=self.horloge,
            parametres=Parametres(dossier_factures=str(tmp_path / "factures")),
            generateur_mot=lambda: "MANGUE",
        )
        self._n = 0
        with self.fabrique() as s:
            self.pme_a = dom_pme.creer_pme(s, self.horloge, nom_commerce="Chez Marie", numero_whatsapp=NUM_A, quartier="Essos", ville="Yaoundé").id
            self.pme_b = dom_pme.creer_pme(s, self.horloge, nom_commerce="Boutique Paul", numero_whatsapp=NUM_B, quartier="Mokolo", ville="Yaoundé").id
            s.commit()

    def envoyer(self, texte: str, numero: str = NUM_A, type: str = "texte", media_id: str | None = None, heure_envoi: datetime | None = None) -> list[str]:
        self._n += 1
        with self.fabrique() as s:
            m = Message(
                numero=numero, direction="entrant", wamid=f"wamid.{self._n}", type=type, texte=texte if type == "texte" else None,
                media_id=media_id, heure_envoi=heure_envoi or self.horloge.maintenant(), heure_reception=self.horloge.maintenant(),
            )
            s.add(m)
            s.flush()
            res = pipeline.traiter(s, self.deps, m)
            s.commit()
            self.dernier = res
            return res.textes

    def session(self):
        return self.fabrique()


@pytest.fixture
def banc(tmp_path) -> Banc:
    return Banc(tmp_path)
