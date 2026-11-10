"""Interprète Gemini (API Google). Même contrat que Claude : JSON validé par `Interpretation`, aucun outil."""

from __future__ import annotations

import json
import time

import httpx
from pydantic import ValidationError

from app.integrations.llm.claude import charger_prompt_systeme, rendre_contexte
from app.integrations.llm.interface import ContexteInterpretation, ErreurInterprete, ResultatInterpretation
from app.moki.schemas import Interpretation

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent"


class InterpreteGemini:
    def __init__(self, cle: str, modele: str = "gemini-flash-lite-latest", client: httpx.Client | None = None) -> None:
        if not cle:
            raise ValueError("clé Gemini absente")
        self.cle, self.modele = cle, modele
        self.client = client or httpx.Client(timeout=90.0)
        schema = json.dumps(Interpretation.model_json_schema(), ensure_ascii=False)
        self.systeme = charger_prompt_systeme() + "\n\n## Format de sortie\nRéponds par un unique objet JSON valide pour ce schéma JSON :\n" + schema

    def interpreter(self, contexte: ContexteInterpretation, texte: str) -> ResultatInterpretation:
        corps = {
            "systemInstruction": {"parts": [{"text": self.systeme}]},
            "contents": [{"role": "user", "parts": [{"text": rendre_contexte(contexte, texte)}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0, "maxOutputTokens": 2048},
        }
        derniere = ""
        for tentative in range(3):
            try:
                r = self.client.post(URL.format(modele=self.modele), json=corps, headers={"x-goog-api-key": self.cle})
            except httpx.HTTPError as e:
                raise ErreurInterprete(f"réseau : {e}") from e
            if r.status_code in (429, 500, 503) and tentative < 2:
                time.sleep(2 * (tentative + 1))
                continue
            if r.status_code >= 400:
                raise ErreurInterprete(f"erreur API {r.status_code} : {r.text[:200]}")
            donnees = r.json()
            try:
                brut = donnees["candidates"][0]["content"]["parts"][0]["text"]
                interp = Interpretation.model_validate_json(brut)
            except (KeyError, IndexError, ValidationError, ValueError) as e:
                derniere = str(e)[:200]
                continue
            u = donnees.get("usageMetadata", {})
            return ResultatInterpretation(
                interpretation=interp, modele=self.modele,
                tokens_entree=int(u.get("promptTokenCount", 0)), tokens_sortie=int(u.get("candidatesTokenCount", 0)),
            )
        raise ErreurInterprete(f"sortie invalide : {derniere}")
