# Backend Moki

Pipeline : message WhatsApp → (transcription) → interprétation par le modèle (JSON strict) → règles en code → confirmation → exécution → réponse par gabarit, journal à chaque étape.

```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/python -m pytest tests        # 34 tests, sans réseau
.venv/Scripts/python simuler.py              # parler à Moki en terminal
.venv/Scripts/python ../evals/run_eval.py    # jeu de référence
cp ../.env.example ../.env                   # puis MOKI_INTERPRETE=claude + ANTHROPIC_API_KEY pour le vrai modèle
.venv/Scripts/uvicorn app.api.main:creer_app --factory --reload
```

Routes : `GET/POST /webhooks/whatsapp` (signature vérifiée), `GET /console` (auth basique), `GET /sante`.
Worker du soir : `app/workers/resume_du_soir.py` (à planifier toutes les 15 min).

Non branché à ce stade : transcription réelle (banc d'essai P0-10), agrégateur de paiement (étage B), migrations Alembic (les tables sont créées au démarrage).
