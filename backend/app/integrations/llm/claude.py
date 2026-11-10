"""Interprète réel : Claude via l'API Anthropic, sortie structurée, cache de prompt.

Le modèle ne reçoit aucun outil : il renvoie une `Interpretation`, rien d'autre.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anthropic

from app.integrations.llm.interface import ContexteInterpretation, ErreurInterprete, ResultatInterpretation
from app.moki.schemas import Interpretation

RACINE = Path(__file__).resolve().parents[4]
CHEMIN_PROMPT = RACINE / "prompts" / "systeme.md"
CHEMIN_EXEMPLES = RACINE / "prompts" / "exemples.jsonl"

# Tarifs en $ par million de tokens (entrée, sortie, lecture cache). À revérifier : voir
# docs/02-plan-complet.md §2.8. Lecture cache Haiku 5.5 non publiée dans nos sources : estimation.
TARIFS: dict[str, tuple[float, float, float]] = {
    "claude-opus-5-5": (4.0, 20.0, 0.20),
    "claude-sonnet-5-5": (2.0, 10.0, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}
MODELES_AVEC_REPLI = ("claude-opus-5-5", "claude-sonnet-5-5")


def charger_prompt_systeme() -> str:
    systeme = CHEMIN_PROMPT.read_text(encoding="utf-8")
    if CHEMIN_EXEMPLES.exists():
        exemples = [ligne for ligne in CHEMIN_EXEMPLES.read_text(encoding="utf-8").splitlines() if ligne.strip()]
        if exemples:
            systeme += "\n\n## Exemples (message -> interprétation attendue)\n"
            for ligne in exemples:
                ex = json.loads(ligne)
                systeme += f"\nMessage : {ex['message']}\nInterprétation : {json.dumps(ex['interpretation'], ensure_ascii=False)}\n"
    return systeme


def rendre_contexte(contexte: ContexteInterpretation, texte: str) -> str:
    parts = [
        f"Date et heure locales : {contexte.date_locale}",
        f"Commerce : {contexte.nom_commerce}",
        f"État de la conversation : {contexte.etat_conversation}",
    ]
    if contexte.action_en_attente:
        parts.append("Action en attente (à compléter avec la réponse de la gérante, renvoyer l'interprétation complétée) : " + json.dumps(contexte.action_en_attente.get("interpretation", contexte.action_en_attente), ensure_ascii=False))
    if contexte.question_en_attente:
        parts.append(f"Question posée par Moki : {contexte.question_en_attente}")
    if contexte.produits:
        parts.append("Produits connus : " + "; ".join(f"{n} ({p} F)" for n, p in contexte.produits))
    if contexte.clients:
        parts.append("Clients connus : " + "; ".join(contexte.clients))
    if contexte.factures_ouvertes:
        parts.append("Factures ouvertes : " + "; ".join(f"n° {n:03d} {c} ({t} F)" for n, c, t in contexte.factures_ouvertes))
    if contexte.derniers_echanges:
        parts.append("Derniers échanges :\n" + "\n".join(f"- {'PME' if d == 'entrant' else 'Moki'} : {t}" for d, t in contexte.derniers_echanges))
    parts.append(f"\nMessage de la gérante : « {texte} »")
    return "\n".join(parts)


class InterpreteClaude:
    def __init__(self, modele: str, effort: str = "low", client: anthropic.Anthropic | None = None, prompt_systeme: str | None = None) -> None:
        self.modele = modele
        self.effort = effort
        self.client = client or anthropic.Anthropic()
        self.systeme = prompt_systeme if prompt_systeme is not None else charger_prompt_systeme()

    def interpreter(self, contexte: ContexteInterpretation, texte: str) -> ResultatInterpretation:
        requete: dict[str, Any] = {
            "model": self.modele,
            "max_tokens": 2048,
            "system": [{"type": "text", "text": self.systeme, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": rendre_contexte(contexte, texte)}],
            "output_format": Interpretation,
            "output_config": {"effort": self.effort},
        }
        if self.modele in MODELES_AVEC_REPLI:
            # Repli serveur sur refus du classifieur ; non supporté sur Haiku 5.5.
            requete["betas"] = ["server-side-fallback-2026-07-01"]
            requete["fallbacks"] = "default"
        try:
            reponse = self.client.beta.messages.parse(**requete)
        except anthropic.RateLimitError as e:
            raise ErreurInterprete(f"limite de débit : {e}") from e
        except anthropic.APIStatusError as e:
            raise ErreurInterprete(f"erreur API {e.status_code} : {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ErreurInterprete(f"réseau : {e}") from e

        if reponse.stop_reason == "refusal":
            raise ErreurInterprete("le modèle a refusé la requête")
        interp = reponse.parsed_output
        if interp is None:
            raise ErreurInterprete("sortie structurée absente ou invalide")

        usage = reponse.usage
        entree = int(getattr(usage, "input_tokens", 0) or 0)
        sortie = int(getattr(usage, "output_tokens", 0) or 0)
        cache = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        return ResultatInterpretation(
            interpretation=interp,
            modele=str(getattr(reponse, "model", self.modele)),
            tokens_entree=entree,
            tokens_sortie=sortie,
            tokens_cache=cache,
            cout_estime=estimer_cout(self.modele, entree, sortie, cache),
        )


def estimer_cout(modele: str, entree: int, sortie: int, cache: int) -> float | None:
    tarif = TARIFS.get(modele)
    if tarif is None:
        return None
    pe, ps, pc = tarif
    return (entree * pe + sortie * ps + cache * pc) / 1_000_000
