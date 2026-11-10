# 04 · Connecter Moki à WhatsApp (Meta) : procédure rapide

Objectif : en environ 30 minutes, écrire à Moki depuis votre vrai WhatsApp. On utilise le **numéro de test gratuit** fourni par Meta : pas besoin de vérifier l'entreprise pour cette étape. Les écrans de Meta changent parfois de place ; si un libellé diffère, cherchez le mot-clé en gras.

Ce qu'il faut : un compte Facebook, votre téléphone avec WhatsApp, et le backend qui tourne sur votre ordinateur.

## 1. Rendre le backend joignable depuis Internet

Meta doit pouvoir appeler votre ordinateur. Le plus simple est un tunnel gratuit.

```bash
# terminal 1 : le backend
cd backend
.venv/Scripts/uvicorn app.api.main:creer_app --factory --port 8000
# terminal 2 : le tunnel (Cloudflare, sans compte)
cloudflared tunnel --url http://localhost:8000
```

Notez l'adresse affichée, par exemple `https://xxxx.trycloudflare.com`. Elle change à chaque lancement, sauf compte payant. Alternative : `ngrok http 8000`.

## 2. Créer l'application chez Meta

1. Allez sur **developers.facebook.com**, connectez-vous, cliquez **Mes applications** puis **Créer une application**.
2. Cas d'usage : choisissez **Autre**, puis le type **Entreprise** (Business).
3. Nommez l'application « Moki », validez.
4. Sur le tableau de bord, trouvez le produit **WhatsApp** et cliquez **Configurer**. Meta crée un compte WhatsApp Business de test et un numéro de test.

## 3. Récupérer les trois valeurs

Menu **WhatsApp → Configuration de l'API** (API Setup) :

| Ce que vous voyez | À mettre dans `.env` |
|---|---|
| **Jeton d'accès temporaire** (valable 24 h) | `MOKI_WHATSAPP_JETON` |
| **Identifiant du numéro de téléphone** (Phone number ID, une longue suite de chiffres) | `MOKI_WHATSAPP_ID_NUMERO` |
| Menu **Paramètres de l'application → Général**, ligne **Clé secrète** (App secret), bouton Afficher | `MOKI_WHATSAPP_SECRET_APP` |

Ajoutez aussi une chaîne secrète de votre choix, par exemple `moki-verif-2026` :

```
MOKI_WHATSAPP_JETON_VERIFICATION=moki-verif-2026
MOKI_CANAL=cloud_api
MOKI_ENV=staging
```

Redémarrez le backend après avoir modifié `.env`.

## 4. Brancher le webhook

1. Menu **WhatsApp → Configuration** (Configuration), section **Webhook**, cliquez **Modifier**.
2. **URL de rappel** : `https://xxxx.trycloudflare.com/webhooks/whatsapp`
3. **Jeton de vérification** : exactement `moki-verif-2026`.
4. Cliquez **Vérifier et enregistrer**. Si cela échoue, le backend ou le tunnel ne tourne pas, ou le jeton diffère.
5. Dans **Champs du webhook**, cliquez **Gérer** et abonnez-vous au champ **messages**.

## 5. Autoriser votre téléphone et inscrire la PME

1. Retour dans **Configuration de l'API**, section « Envoyer des messages » : dans **À** (To), ajoutez votre numéro de téléphone, confirmez avec le code reçu sur WhatsApp. Le numéro de test accepte 5 destinataires au maximum.
2. Inscrivez votre numéro comme PME dans Moki. Le format est international, sans `+` ni espaces (Cameroun : `2376XXXXXXXX`).

```bash
cd backend
.venv/Scripts/python.exe - <<'PY'
from app.api.main import creer_app; creer_app()
from app.db.session import fabrique
from app.core.horloge import HorlogeSysteme
from app.domaine import pme
with fabrique()() as s:
    pme.creer_pme(s, HorlogeSysteme(), nom_commerce="Ma boutique", numero_whatsapp="2376XXXXXXXX")
    s.commit()
PY
```

## 6. Premier message

Depuis votre WhatsApp, écrivez au **numéro de test** indiqué par Meta (il apparaît dans API Setup) : « j'ai vendu 3 paires à 5000 ». Moki répond. Si rien ne vient :

| Symptôme | Cause probable |
|---|---|
| Webhook refusé à l'étape 4 | tunnel arrêté, mauvais jeton de vérification |
| Message reçu mais « signature invalide » (401 dans les logs) | `MOKI_WHATSAPP_SECRET_APP` faux |
| Moki répond « numéro pas encore inscrit » | numéro de la PME différent (indicatif, espaces) |
| Aucune réponse, erreur d'envoi | jeton expiré (24 h) : régénérez-le dans API Setup |
| Rien du tout | champ **messages** non abonné |

## 7. Ce qui reste pour la vraie mise en service

- **Jeton permanent** : dans **Business Settings → Utilisateurs → Utilisateurs système**, créez un utilisateur système, donnez-lui l'actif WhatsApp, générez un jeton avec les permissions `whatsapp_business_messaging` et `whatsapp_business_management`. Il remplace le jeton de 24 h.
- **Votre propre numéro** (pas celui de test) et **vérification de l'entreprise** dans Business Settings : prévoir société et justificatifs, plusieurs jours.
- **Messages à modèle** : le résumé de 19 h part hors de la fenêtre de 24 h après le dernier message de la PME. Il faut créer et faire approuver des modèles (WhatsApp Manager → Modèles de messages, catégorie **Utilitaire**), puis les utiliser dans `resume_du_soir`. Tant que ce n'est pas fait, le résumé n'arrive que si la PME a écrit dans les dernières 24 h.
- **Hébergement fixe** à la place du tunnel, avec HTTPS.

Sécurité : ne commitez jamais `.env`. Le jeton et la clé secrète donnent le contrôle du numéro.
