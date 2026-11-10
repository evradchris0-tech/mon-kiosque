"""Rejoue le jeu de référence et produit un rapport (annexe C du plan complet).

Usage (depuis la racine du dépôt) :
  backend/.venv/Scripts/python.exe evals/run_eval.py                 # interprète à règles, sans réseau
  MOKI_INTERPRETE=claude MOKI_MODELE=claude-haiku-5-5 ... run_eval.py  # modèle réel (coûte de l'argent)

Erreur grave = un total d'argent faux ou une action dangereuse ; une seule fait échouer (code 1).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "backend"))
sys.stdout.reconfigure(encoding="utf-8")

from app.integrations.llm.factice import InterpreteRegles  # noqa: E402
from app.integrations.llm.interface import ContexteInterpretation  # noqa: E402
from app.moki.schemas import Intention  # noqa: E402


def charger_cas() -> list[dict]:
    cas: list[dict] = []
    for fichier in sorted((RACINE / "evals" / "reference").glob("*.jsonl")):
        for ligne in fichier.read_text(encoding="utf-8").splitlines():
            if ligne.strip():
                cas.append(json.loads(ligne))
    return cas


def construire_interprete():
    if os.environ.get("MOKI_INTERPRETE") == "claude":
        from app.integrations.llm.claude import InterpreteClaude

        return InterpreteClaude(os.environ.get("MOKI_MODELE", "claude-haiku-5-5"), os.environ.get("MOKI_EFFORT", "low")), os.environ.get("MOKI_MODELE", "claude-haiku-5-5")
    if os.environ.get("MOKI_INTERPRETE") == "gemini":
        from app.integrations.llm.gemini import InterpreteGemini

        m = os.environ.get("MOKI_MODELE_GEMINI", "gemini-flash-lite-latest")
        return InterpreteGemini(os.environ["MOKI_GEMINI_CLE"], m), m
    return InterpreteRegles(), "regles (sans modèle)"


def main() -> int:
    interprete, nom_modele = construire_interprete()
    contexte = ContexteInterpretation(date_locale="mardi 10/11/2026 10:00", nom_commerce="Chez Marie")
    cas = charger_cas()
    ok_intention = ok_total = nb_total = 0
    graves: list[str] = []
    erreurs: list[str] = []
    for c in cas:
        attendu = c["attendu"]
        interp = interprete.interpreter(contexte, c["message"]).interpretation
        if interp.intention == Intention(attendu["intention"]):
            ok_intention += 1
        else:
            erreurs.append(f"{c['id']} : intention {interp.intention.value} au lieu de {attendu['intention']}")
            if attendu["intention"] == "AUTRE" and interp.intention != Intention.AUTRE:
                graves.append(f"{c['id']} : instruction dangereuse prise pour {interp.intention.value}")
        if "total" in attendu and attendu["total"] is not None:
            nb_total += 1
            calcule = interp.total() if interp.lignes_completes() else None
            if calcule == attendu["total"]:
                ok_total += 1
            else:
                erreurs.append(f"{c['id']} : total {calcule} au lieu de {attendu['total']}")
                if calcule is not None:
                    graves.append(f"{c['id']} : total faux {calcule} (attendu {attendu['total']}), sans demande de précision")
        if attendu.get("ambigu") and interp.lignes_completes():
            graves.append(f"{c['id']} : ambiguïté non levée, total calculé {interp.total()}")

    n = len(cas)
    rapport = [
        f"# Rapport de test : {datetime.now():%Y-%m-%d %H:%M}",
        f"- Modèle : {nom_modele}",
        f"- Cas testés : {n}",
        f"- Intention correcte : {ok_intention}/{n} ({100 * ok_intention // max(n, 1)} %)",
        f"- Montants exacts : {ok_total}/{nb_total} ({100 * ok_total // max(nb_total, 1)} %)",
        f"- **Erreurs graves : {len(graves)}** (doit être 0)",
        "",
        "## Erreurs",
        *(f"- {e}" for e in erreurs or ["aucune"]),
        "",
        "## Erreurs graves",
        *(f"- {g}" for g in graves or ["aucune"]),
        "",
        f"Décision : {'METTRE EN LIGNE' if not graves else 'CORRIGER (erreur grave)'}",
    ]
    texte = "\n".join(rapport)
    dossier = RACINE / "evals" / "rapports"
    dossier.mkdir(exist_ok=True)
    (dossier / f"rapport-{datetime.now():%Y%m%d-%H%M%S}.md").write_text(texte, encoding="utf-8")
    print(texte)
    return 1 if graves else 0


if __name__ == "__main__":
    raise SystemExit(main())
