# 03 · Travailler avec les agents IA sur Moki

**Date :** 10 novembre 2026
**Objet :** comment un duo fait construire, tester et exploiter Moki par des agents IA (Claude Code) sans perdre le contrôle sur ce qui touche à l'argent des PME.
**Lecteurs :** le duo fondateur ; les sections 7 à 9 sont à copier telles quelles dans le dépôt et dans les prompts.

---

## 1. Principe

**Les humains décident, les agents produisent, les tests tranchent.**

Ce que les agents font très bien ici : poser le squelette du backend, écrire les intégrations derrière des interfaces, écrire les tests et les migrations, construire le harnais d'évaluation, mettre au format et annoter le corpus, rédiger la documentation et les rapports, relire du code.

Ce qu'ils font mal sans cadre : décider d'une règle d'argent, deviner ce que veut une PME, s'arrêter quand l'intégration réelle se comporte autrement que la factice, respecter une règle qu'on ne leur a pas écrite, résister à la tentation d'assouplir un test pour qu'il passe.

Le cadre tient donc en cinq pièces : un `CLAUDE.md` à la racine (section 7), une spécification par fonctionnalité (section 8), des tests qui ne se modifient pas sans décision écrite, un jeu de référence rejoué à chaque changement, et une relecture humaine systématique des chemins « argent ».

---

## 2. Deux « agents IA » à ne pas confondre

| | Agents de développement | Moki lui-même |
|---|---|---|
| Qui | Claude Code, lancé par vous, sur le dépôt | Le backend en production, pour les PME |
| Nature | Agents autonomes avec outils (fichiers, shell, tests), sous revue humaine | **Un workflow** : un appel de modèle par message pour interpréter, puis du code déterministe (`02-plan-complet.md` §2.3) |
| Pourquoi cette différence | Une erreur de code se rattrape avant la fusion | Une erreur sur une facture ne se rattrape pas |

Ce document traite des agents de développement.

---

## 3. Les casquettes des agents

Il n'y a pas huit agents qui tournent en permanence : il y a des **casquettes**, c'est-à-dire des prompts de lancement et des limites, que vous donnez à une session Claude Code selon la tâche.

| Casquette | Mission | Entrées | Sorties | Interdictions |
|---|---|---|---|---|
| **Architecte** | Transformer une tâche du plan en plan d'implémentation | `02-plan-complet.md`, la spec, le code existant | Plan d'étapes, fichiers touchés, risques, questions | Ne code pas |
| **Développeur backend** | Implémenter une fonctionnalité spécifiée | Spec validée, plan validé | Code + tests unitaires + scénarios, petits commits | Ne touche pas `moki/regles/`, `domaine/paiements/`, `prompts/` sans mention explicite dans la tâche |
| **Développeur intégrations** | Brancher WhatsApp, STT, agrégateur, SMS derrière les interfaces | Documentation du fournisseur, sandbox | Implémentation réelle + factice + enregistrements d'échanges | Aucun secret dans le code ; aucun appel réseau dans les tests |
| **Ingénieur évaluations** | Faire vivre `evals/` : format, runner, rapports, comparaisons de modèles | Jeu de référence, journal du pilote | Rapports de test (annexe C du plan), cas ajoutés | Ne modifie pas l'attendu d'un cas sans validation humaine |
| **Rédacteur de prompts Moki** | Améliorer `prompts/systeme.md` et `exemples.jsonl` contre les évaluations | Rapport d'erreurs | Nouvelle version + rapport avant / après | Aucune fusion si le score baisse ou si une erreur grave apparaît |
| **Relecteur sécurité** | Relire un changement sous l'angle étanchéité, injection, idempotence, secrets | La PR | Liste de constats classés | Ne corrige pas lui-même : il signale |
| **Annotateur de corpus** | Anonymiser et mettre au format les messages réels, proposer l'interprétation attendue | Exports du journal (avec consentement) | Lignes JSONL **marquées « à valider »** | Rien n'entre dans `evals/reference/` sans validation humaine |
| **Rapporteur de pilote** | Rédiger le rapport hebdomadaire | Vues SQL en **lecture seule** | `docs/pilote/rapport-semaine-N.md` | Aucune écriture en base, aucune donnée nominative dans le rapport |

---

## 4. Cycle de travail d'une tâche

1. **Spécifier.** Une spec courte par fonctionnalité (section 8), écrite par vous ou proposée par un agent, **validée par vous**. Sans spec validée, pas de code.
2. **Planifier.** Lancer l'agent en mode plan sur la spec. Il propose les étapes et les fichiers touchés ; vous validez ou corrigez.
3. **Implémenter** dans un worktree Git dédié (une branche par tâche), par petits commits. L'agent écrit les tests **avec** le code, avec les intégrations factices.
4. **Tester** : lint, types, `pytest` complet. Si `prompts/` ou `backend/app/moki/` ont changé : relancer `evals/run_eval.py` et joindre le rapport.
5. **Relire** : `/code-review` sur la branche ; `/security-review` si la tâche touche l'argent, l'étanchéité, les webhooks ou les secrets. Puis relecture humaine, obligatoire pour les chemins « argent ».
6. **Fusionner et déployer** sur staging ; vérifier à la main sur le numéro WhatsApp de test (liste de contrôle de la spec).
7. **Consigner** : ADR si une décision a été prise, spec mise à jour si elle a changé, cas ajoutés au jeu de référence si le pilote a révélé des erreurs.
8. **Déployer en production** par tag, uniquement depuis `main`, uniquement par un humain.

Durée visée d'une tâche : une demi-journée à deux jours. Au-delà, la découper.

---

## 5. Garde-fous pour les agents

- **Les règles d'argent sont hors de portée.** `backend/app/moki/regles/`, `backend/app/domaine/paiements/`, `tests/securite/` et `prompts/` ne changent que si la tâche le dit explicitement, avec ADR ou spec, relance des évaluations et relecture humaine.
- **Un test rouge ne se contourne pas.** Interdiction d'affaiblir, ignorer ou supprimer un test pour le faire passer ; l'agent explique ce qui bloque.
- **Aucun secret, jamais.** Clés et jetons uniquement via variables d'environnement ; les tests n'appellent jamais un service réel.
- **Aucune action de production.** Un agent ne déploie pas en production, ne modifie pas la base de production, n'envoie pas de message WhatsApp réel sans instruction explicite.
- **Un seul `pme_id`, toujours.** Toute nouvelle requête, route ou vue est écrite avec le filtre `pme_id` et couverte par le test d'étanchéité.
- **Le modèle n'exécute rien.** Aucun outil à effet de bord n'est exposé au modèle de langage dans le pipeline Moki ; les totaux sont calculés en code ; les messages avec montant viennent des gabarits.
- **Le jeu de référence est sacré.** On ajoute des cas ; on ne modifie l'attendu d'un cas existant qu'avec validation humaine et commentaire.
- **Rapport honnête.** L'agent dit ce qu'il n'a pas pu tester (intégration réelle, montant réel) plutôt que de l'annoncer fait.

---

## 6. Définition de « terminé »

Une tâche est terminée quand :

- [ ] la spec est respectée point par point, ou les écarts sont listés ;
- [ ] lint, types et `pytest` sont verts ;
- [ ] les scénarios N2 concernés sont automatisés ;
- [ ] le test d'étanchéité couvre les nouvelles routes et requêtes ;
- [ ] les évaluations ont été relancées si le pipeline ou les prompts ont changé, sans baisse de score et avec 0 erreur grave ;
- [ ] la revue de code et, si nécessaire, la revue de sécurité ont été faites ;
- [ ] la liste de contrôle manuelle sur le numéro de test a été cochée par un humain ;
- [ ] la documentation (spec, ADR, README) est à jour.

---

## 7. `CLAUDE.md` à placer à la racine du dépôt (tâche P0-07)

Brouillon à copier dans `CLAUDE.md` puis à ajuster (commandes réelles) quand le monorepo existe.

```markdown
# Mon Kiosque / Moki — consignes pour les agents

## Ce qu'est ce dépôt
Moki est un assistant WhatsApp pour les PME camerounaises : ventes, factures, relances,
résumés. Lire d'abord `docs/02-plan-complet.md` (architecture, phases, règles) et la
spec de la tâche dans `docs/specs/`. Le plan d'origine est `docs/plan-moki-v1.0.md`.
`app/` est un prototype Flutter gelé : ne pas y toucher sauf tâche explicite.

## Commandes (à ajuster lors de l'initialisation)
- Backend : `cd backend && uv sync` puis `uv run pytest`, `uv run ruff check .`, `uv run pyright`
- Base locale : `docker compose -f infra/docker-compose.yml up -d postgres`
- Migrations : `cd backend && uv run alembic upgrade head`
- Évaluations : `uv run python evals/run_eval.py` (rapport dans `evals/rapports/`)

## Règles non négociables (argent)
1. Le modèle de langage interprète seulement : il n'a aucun outil, ne calcule aucun total.
   Tout total est recalculé en code. Tout message contenant un montant vient d'un gabarit.
2. Aucune action sortante (facture, relance, lien, SMS) sans confirmation enregistrée.
3. Toute requête est filtrée par `pme_id`. Aucune route n'accepte un `pme_id` du client.
   Toute nouvelle route ou requête est couverte par `tests/securite/test_etancheite.py`.
4. `backend/app/moki/regles/`, `backend/app/domaine/paiements/`, `tests/securite/` et
   `prompts/` ne se modifient que si la tâche le demande explicitement, avec ADR ou spec,
   relance complète des évaluations et relecture humaine.
5. Un test rouge ne se contourne pas : on explique ce qui bloque.
6. Secrets uniquement par variables d'environnement. Les tests n'appellent jamais le réseau :
   chaque intégration a une implémentation factice dans `backend/app/integrations/*/factice.py`.
7. Aucun déploiement en production, aucune écriture en base de production, aucun message
   WhatsApp réel sans instruction explicite d'un humain.

## Conventions
- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest. Typage complet.
- Code et commentaires en français pour le domaine (ventes, factures, pme, relances) ;
  anglais toléré pour les termes techniques standard.
- Montants en entiers (FCFA, pas de décimales) ; heures en UTC en base, affichage en
  Africa/Douala ; l'heure d'envoi WhatsApp fait foi pour les ventes.
- Une fonctionnalité = une spec dans `docs/specs/` + tests unitaires + scénario N2.
- Petits commits, messages en français à l'impératif : « Ajoute l'intention VENTE ».

## Définition de « terminé »
Voir `docs/03-travailler-avec-les-agents-ia.md` §6. Dire explicitement ce qui n'a pas pu
être testé (intégration réelle, montant réel) au lieu de l'annoncer fait.
```

---

## 8. Gabarit de spécification (`docs/specs/<fonction>.md`)

```markdown
# Spec : <nom de la fonctionnalité>   (tâche P?-??)
Statut : brouillon | validée (par qui, quand)

## Besoin
<le besoin B? du plan, en une phrase, du point de vue de la PME>

## Conversation cible
<deux ou trois échanges PME / Moki, avec les montants exacts>

## Intentions et données
<intentions concernées ; champs du schéma Interpretation utilisés ; valeurs par défaut>

## Règles (hors modèle)
<validations, seuils, confirmations, plafonds ; renvoyer à 02-plan-complet.md §2.5>

## Effets
<tables modifiées, messages envoyés, jobs créés, lignes de journal>

## Cas limites
<ambiguïtés, doublons, numéros inconnus, pannes : ce que Moki fait>

## Tests attendus
- unitaires : ...
- scénarios N2 : S? ...
- sécurité N4 : ...
- cas à ajouter au jeu de référence : ...

## Liste de contrôle manuelle (numéro de test)
- [ ] ...

## Hors périmètre de cette spec
<ce qu'on ne fait pas ici>
```

---

## 9. Prompts prêts à l'emploi

À coller dans Claude Code depuis la racine du dépôt. Chaque prompt commence par désigner la casquette et la tâche.

**P0-07 : initialiser le monorepo**

```
Casquette : développeur backend. Tâche P0-07 de docs/02-plan-complet.md.
Lis docs/02-plan-complet.md §2 et §3, puis docs/03-travailler-avec-les-agents-ia.md §7.
Crée la structure de dépôt de la section 3 (sans toucher à app/), le CLAUDE.md de la
section 7 du document 03, un backend FastAPI minimal (route /sante), la configuration
PostgreSQL + Alembic avec une première migration contenant les tables pme et
numeros_autorises, un docker-compose dans infra/, et une CI GitHub Actions (ruff, pyright,
pytest). Écris un test d'étanchéité vide mais câblé (deux PME créées, assertion triviale)
que les prochaines tâches rempliront. Passe par le mode plan d'abord, puis implémente.
Ne commets rien : je relirai et commettrai moi-même.
```

**P0-08 : harnais d'évaluation**

```
Casquette : ingénieur évaluations. Tâche P0-08.
Lis docs/02-plan-complet.md §5 et annexes A, B, C. Implémente evals/run_eval.py :
charge tous les JSONL de evals/reference/, appelle l'interface Interprete (réelle ou
factice selon une option), compare à l'attendu, calcule les métriques N1 du plan
(intention, montants, quantités/produits, erreurs graves, demandes de précision
justifiées), et écrit un rapport Markdown au format de l'annexe C du plan dans
evals/rapports/. Ajoute une option --rapide (échantillon) et --modele <id>.
Crée evals/reference/ventes_simples.jsonl avec les 22 cas de l'annexe B.
Tests unitaires du runner avec un Interprete factice. Ne modifie aucun cas attendu.
```

**P1-05 : implémenter l'intention VENTE**

```
Casquette : développeur backend. Tâche P1-05, intention VENTE uniquement.
La spec est docs/specs/vente.md (validée). Respecte CLAUDE.md : le modèle n'a aucun outil,
les totaux sont recalculés en code, les messages avec montant viennent de gabarits.
Implémente l'extraction des lignes, la vente à crédit, le mode de paiement inconnu
(question), la fenêtre d'annulation de 10 minutes, et les scénarios N2 S1 et S7 en
pytest avec les intégrations factices. Ajoute les nouvelles requêtes au test
d'étanchéité. Relance evals/run_eval.py --rapide et joins le rapport dans ton compte rendu.
Liste ce que tu n'as pas pu vérifier.
```

**Revue de sécurité d'une branche**

```
Casquette : relecteur sécurité. Relis la branche courante par rapport à main sous
l'angle : étanchéité entre PME (toute requête filtrée par pme_id ?), idempotence des
webhooks (wamid, reference_externe), instructions piégées dans les messages (le modèle
a-t-il un moyen d'agir ?), secrets, journalisation de numéros en clair. Ne corrige rien :
produis une liste classée (bloquant / important / mineur) avec fichier et ligne.
```

**Annotation du corpus du pilote**

```
Casquette : annotateur de corpus. Voici un export de messages du journal (consentement
vérifié). Anonymise noms et numéros (remplace par des pseudonymes cohérents), mets
chaque message au format JSONL de l'annexe B de docs/02-plan-complet.md, propose
l'interprétation attendue et la décision attendue, et marque chaque ligne
"a_valider": true. Écris le résultat dans evals/a_valider/<date>.jsonl, jamais dans
evals/reference/. Signale les messages que tu n'arrives pas à interpréter.
```

**Rapport hebdomadaire du pilote**

```
Casquette : rapporteur de pilote. En lecture seule sur les vues SQL d'indicateurs
(docs/02-plan-complet.md §7), rédige docs/pilote/rapport-semaine-<N>.md : indicateurs
de la section 10.1 du plan avec leur cible, évolution par rapport à la semaine
précédente, trois erreurs les plus fréquentes du journal, coût technique par PME active,
et trois questions à poser aux PME cette semaine. Aucun nom ni numéro de PME dans le
rapport : utiliser les identifiants.
```

---

## 10. Ce qui reste strictement humain

- Valider chaque spec et chaque ADR.
- Décider des seuils, plafonds et règles de confirmation.
- Valider l'attendu de chaque cas du jeu de référence.
- Relire tout changement sur les chemins « argent » et « étanchéité ».
- Déployer en production ; manipuler les secrets ; ouvrir les comptes fournisseurs.
- Parler aux PME : recrutement, inscription, entretiens, support (« humain »).
- Décider du modèle de langage, de l'agrégateur, de l'hébergeur, sur rapports.
- Décider des go / no-go de phase.

---

## 11. Outillage Claude Code recommandé

- **`CLAUDE.md`** à la racine (section 7) ; un `backend/CLAUDE.md` plus court si des conventions locales apparaissent.
- **Mode plan** avant toute tâche qui touche plus d'un fichier ; **worktrees** pour isoler chaque tâche.
- **`/code-review`** sur chaque branche avant fusion ; **`/security-review`** sur l'argent, l'étanchéité, les webhooks.
- **Hook** après modification de `prompts/` ou `backend/app/moki/` : lancer `pytest -q` et `run_eval.py --rapide` (à configurer dans `.claude/settings.json`).
- **Sous-agents** : un relecteur indépendant lancé sur la branche à la fin d'une tâche de développement.
- **CI GitHub Actions** avec les mêmes portes que localement, pour que rien ne dépende de la machine d'un fondateur.
- **Un seul agent à la fois sur les chemins « argent »** ; plusieurs en parallèle sont acceptables sur des tâches indépendantes (console, page web, documentation).
