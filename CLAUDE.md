# Mon Kiosque / Moki : consignes pour les agents

Moki est un assistant WhatsApp pour les PME camerounaises (ventes, factures, relances, résumés).
Lire `docs/02-plan-complet.md` (architecture, règles) avant toute tâche. `app/` est un prototype Flutter gelé.

## Commandes (depuis `backend/`, venv dans `backend/.venv`)
- Tests : `.venv/Scripts/python.exe -m pytest tests`
- Lint : `.venv/Scripts/ruff.exe check app tests`
- Évaluations : `.venv/Scripts/python.exe ../evals/run_eval.py`
- Simulateur : `.venv/Scripts/python.exe simuler.py`

## Règles non négociables (argent)
1. Le modèle de langage interprète seulement : aucun outil, aucun total. Totaux recalculés en code ; messages avec montant = gabarits (`app/moki/reponses.py`).
2. Aucune action sortante (facture, relance, lien) sans confirmation enregistrée (`confirmations`).
3. Toute requête est filtrée par `pme_id`. Aucune route n'accepte un `pme_id` du client.
4. `app/moki/regles.py`, `app/domaine/paiements.py`, `prompts/` : modifier seulement si la tâche le demande, avec relance des tests ET de `evals/run_eval.py`.
5. Un test rouge ne se contourne pas.
6. Secrets par variables d'environnement ; les tests n'appellent jamais le réseau (intégrations factices).
7. Aucun déploiement ni message WhatsApp réel sans instruction humaine.

## Conventions
Python 3.12+, montants entiers FCFA, dates UTC naïves en base, domaine en français.
