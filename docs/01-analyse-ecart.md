# 01 · Analyse d'écart : le plan MOKI face au projet Mon Kiosque

**Date :** 10 novembre 2026
**Objet :** confronter le plan « MOKI : Plan de développement, de déploiement et de test » (v1.0) à ce qui existe dans ce dépôt, repérer les contradictions, et fixer les décisions à prendre avant de coder.
**Lecteurs :** le duo fondateur, puis les agents IA qui travailleront sur le dépôt.

---

## 1. Ce qu'on a aujourd'hui

| Artefact | Où | Ce que c'est |
|---|---|---|
| **Prototype Flutter « Mon Kiosque »** | `app/` | Maquette de démonstration pour le Business Game du 23 avril 2026. Quatre onglets (Chat, Moki, Tableau, Profil), mode démo en 6 scènes. Aucun serveur : données en mémoire, Moki simulé par mots-clés, paiement Orange Money simulé, WhatsApp non branché. |
| **Rapport final du concours** | `MonKiosque_RapportFinal.docx` | Dossier de pitch pour Orange : 4 paliers tarifaires, 6 flux de revenus, 10 000 PME en 12 mois, infrastructure 100 % Orange (Data Center de Makepe, Llama 3 fine-tuné, Messaging Pro, USSD, SMS relay). |
| **Plan MOKI v1.0** | à copier dans `docs/plan-moki-v1.0.md` | Plan réaliste de startup : WhatsApp comme canal unique, agrégateur de paiement multi-opérateurs, modèle de langage via API, pilote de 20 PME, dossier de financement basé sur des chiffres mesurés. |

Le dépôt ne contient **aucun backend, aucun test, aucun jeu de données**. Tout ce qui touche à l'IA, au paiement et à WhatsApp est à construire.

---

## 2. Trois documents, trois produits différents

Le point le plus important de cette analyse : les trois artefacts ne décrivent pas le même produit. Il faut choisir, et le plan MOKI est le bon point de départ.

| Dimension | Rapport du concours | Prototype Flutter | Plan MOKI v1.0 | Décision proposée |
|---|---|---|---|---|
| **Canal principal** | App mobile + bot WhatsApp en secours | App mobile (4 onglets) | **WhatsApp** (la PME parle à Moki), page web légère | **WhatsApp d'abord.** L'app Flutter devient la démo investisseurs et la future app V2 branchée sur la même API. |
| **Infrastructure** | Data Center Orange Makepe, APIs Orange (OM, Messaging Pro, Facturier, Data Live, Flex+) | Aucune (tout simulé) | Agrégateur multi-opérateurs, fournisseurs standards (WhatsApp API, SMS, hébergement) | **Fournisseurs standards**, partenariat Orange recherché en parallèle. Rien dans le code ne doit dépendre d'une API Orange. |
| **IA** | Llama 3 fine-tuné en camfranglais, Whisper local, ML churn, prédictions, scoring crédit | Réponses par mots-clés (« facture », « hier ») | Modèle de langage via API + règles métier en code ; fine-tuning décidé en phase 3 ou 4 | **API Claude + règles en code.** Le corpus local se constitue dès le pilote ; le fine-tuning est une option pour plus tard. |
| **Paiement** | Orange Money Pro Lite, QR marchand, bulk fournisseurs, commission 0,8 % | QR code `om://` simulé, paiement hybride cash + OM | Lien de paiement via agrégateur ; Moki ne détient pas l'argent | **Deux étages** (voir §4.1) : suivi déclaratif d'abord, lien agrégateur ensuite. |
| **Hors-ligne** | 3 niveaux : app, SMS relay 32500, USSD *150*PRO# | Rien | WhatsApp tolère les messages en retard ; USSD en V2 si accord opérateur | **Pas de promesse hors-ligne en V1.** On gère correctement l'heure d'envoi des messages en retard. |
| **Fonctions** | Prospection, fidélisation, prédiction, rédaction de posts, score crédit | Facture, bilan d'hier, relance (simulés) | Vente, facture, lien, relance, résumé, carnet clients, catalogue | **Périmètre du plan MOKI**, strictement. Le reste est « vision », pas « V1 ». |
| **Chiffres** | 10 000 PME, ROI x51, 2 h/jour gagnées, 25–35 % de retour clients | Score crédit 71/100, +12 % | Tous les chiffres sont marqués « cible » à remplacer par les mesures du pilote | **Les chiffres du rapport deviennent des hypothèses à tester**, jamais des promesses dans le produit. |

**Conséquence pour le pitch :** le dossier de financement doit distinguer clairement « ce qui tourne en pilote » (plan MOKI) et « la vision » (rapport). Un investisseur qui voit l'app Flutter promettre un score crédit alors que le produit réel est un bot WhatsApp perdra confiance.

---

## 3. Ce que le prototype apporte, et ce qu'on garde

### 3.1 À réutiliser

| Élément | Fichier | Usage dans la V1 |
|---|---|---|
| Identité visuelle (orange `#FF7900`, violet Moki `#6A5ACD`, neutres) | `app/lib/src/theme/app_colors.dart` | Page web de consultation, factures PDF, console interne |
| Ton de Moki (tutoiement, « C'est noté », « On dit quoi ») | `app/lib/src/features/moki/moki_screen.dart` | Base du prompt système, à valider avec les PME pilotes |
| Modèle de vente avec plusieurs modes de paiement (cash + mobile money sur une même vente) | `app/lib/src/data/models.dart` (`Sale`, `PaymentLeg`) | Repris tel quel dans le modèle de données backend : une vente peut avoir plusieurs « parts » de paiement |
| Scénario de référence « Marie, snack Chez Marie, Essos » et la facture « Lycée Technique, 30 repas à 2 500 + livraison 5 000 = 80 000 » | `simulation_overlay.dart`, `chat_detail_screen.dart` | Premiers cas du jeu de référence, scénarios de test de bout en bout, démo |
| Traductions FR/EN | `app/lib/l10n/` | Vocabulaire produit (« Impayés », « Chiffre d'affaires du jour ») ; l'anglais servira en V2 pour les régions anglophones |
| Logo | `logo.png`, `app/assets/images/logo.png` | Factures, page web |

### 3.2 À ne pas réutiliser

- La logique de Moki par mots-clés : remplacée par le pipeline « modèle de langage + règles » décrit dans le plan complet.
- Les données en mémoire (`SalesController._seed`) : remplacées par PostgreSQL côté serveur (besoin B8, 0 perte de données).
- L'onglet Chat « WhatsApp Pro » : l'API officielle WhatsApp ne donne pas accès aux conversations du WhatsApp Business de la PME. En V1, Moki a **son propre numéro** et la PME lui écrit.
- Le score crédit et « Éligible M+6 » : aucune base réelle. Le besoin B10 (relevé mensuel exportable) le remplace.
- Le QR code `om://pay` : ce format n'existe pas ; le lien de paiement viendra de l'agrégateur.

### 3.3 Décision sur l'app Flutter

Garder `app/` dans le dépôt, **gelée** : pas de nouvelles fonctions tant que le backend n'existe pas. Elle sert à deux choses : montrer la vision aux financeurs, et préparer la V2 mobile qui consommera l'API du backend. La « page web légère » de la V1 ne sera **pas** faite en Flutter web : le bundle est trop lourd pour un téléphone d'entrée de gamme en 3G. Une page servie par le backend suffit.

---

## 4. Points du plan MOKI à corriger ou préciser

Le plan est solide ; les points ci-dessous sont des angles morts ou des formulations qui ne tiendront pas au contact des fournisseurs.

### 4.1 « Moki ne détient jamais l'argent » : vrai seulement sous conditions

Avec la plupart des agrégateurs, l'argent collecté par un lien de paiement arrive sur **votre** compte marchand, puis vous le reversez à la PME. Dans ce cas vous détenez bien des fonds, ce qui peut appeler un agrément. Deux issues :

- l'agrégateur reverse automatiquement sur le portefeuille mobile money de la PME (compte « sous-marchand » ou reversement automatique) : **à vérifier agrégateur par agrégateur** ;
- en attendant, un **étage A déclaratif** : Moki enregistre la vente ou la facture, le client paie directement la PME (cash, ou transfert sur son numéro), et la PME dit à Moki « Jean a payé ». Zéro flux d'argent chez vous, zéro agrément, et déjà l'essentiel de la valeur (besoins B1, B2, B3, B5).

**Proposition :** V1 = étage A dès la phase 1 ; étage B (lien de paiement via agrégateur avec notification) en phase 2, uniquement si un agrégateur offre le reversement direct ou si le juriste valide le schéma.

### 4.2 WhatsApp : qui parle à qui, depuis quel numéro

- **Moki a son propre numéro.** La PME lui écrit depuis son téléphone (n'importe quel numéro WhatsApp, enregistré comme « numéro autorisé »). Le plan parle du « numéro WhatsApp professionnel de la PME » : en V1, c'est simplement le numéro déclaré à l'inscription.
- **Les messages aux clients** (facture, relance, lien) partiraient du numéro de Moki, inconnu du client. C'est une friction et un risque de spam. **Mode par défaut proposé en V1 : « Moki rédige, la PME transfère ».** Moki envoie à la PME le message prêt (texte + PDF de la facture), la PME le transfère à son client depuis son propre WhatsApp. Avantages : zéro coût d'envoi, zéro question de consentement, le client reçoit un message de quelqu'un qu'il connaît. L'envoi direct (SMS ou message WhatsApp à modèle) devient une option activable par PME.
- **Fenêtre de 24 heures.** Moki peut répondre librement à la PME pendant 24 h après son dernier message. Le résumé de 19 h et les rappels du matin sortent de cette fenêtre : ils nécessitent un **message à modèle pré-approuvé** (type « utilitaire »), facturé à l'unité. À prévoir dès la demande de compte.
- **Vocaux.** WhatsApp livre les notes vocales en OGG/Opus via l'API média ; il faut les télécharger puis les transcrire. Le coût de transcription s'ajoute au coût du modèle de langage.
- **À vérifier :** la fonction « coexistence » de Meta (même numéro dans l'application WhatsApp Business et dans l'API) pourrait, en V2, permettre à Moki de lire les conversations clients de la PME, comme le prototype le montrait.

### 4.3 Intentions manquantes

Le tableau des intentions (section 5.1 du plan) oublie trois cas fréquents :

| Code à ajouter | Ce que la PME veut | Exemple |
|---|---|---|
| `PAIEMENT_RECU` | Marquer une vente ou une facture comme payée (indispensable pour l'étage A) | « Jean a payé », « le Lycée a réglé la facture » |
| `CONFIRMATION` | Répondre oui / non / annuler à une question de Moki | « oui », « ok vas-y », « non laisse » |
| `HUMAIN` | Demander à parler à une personne | « je veux parler à quelqu'un » |

Et une variante dans `VENTE` : la **vente à crédit** (« elle paie demain »), qui crée un impayé dans le carnet de dettes. C'est le besoin dominant du profil boutiquier.

### 4.4 Le PIN tapé dans WhatsApp reste lisible

Un code PIN saisi dans la conversation reste dans l'historique du téléphone. Si quelqu'un d'autre tient le téléphone, il voit le PIN. Pour la V1 : conserver la **double confirmation** (Moki renvoie un récapitulatif avec un mot aléatoire à retaper) pour les montants élevés, et prévoir le PIN via la page web (hors conversation) en V1.5. À trancher avec les PME pilotes.

### 4.5 Le modèle de langage ne doit jamais calculer un montant

Le plan le dit implicitement (« le modèle propose, le code vérifie »). Il faut le rendre explicite dans l'architecture : le modèle extrait des **lignes** (produit, quantité, prix unitaire) ; **tous les totaux sont recalculés en code** ; les messages qui contiennent des montants sont produits par des **gabarits déterministes**, pas par le modèle. Cela rend la cible « 0 erreur grave » atteignable et testable.

### 4.6 Le harnais de test doit exister avant la première fonction

Le plan place le jeu de 100 phrases en phase 0 et les tests N1 « à chaque modification ». Pour que ce soit vrai, le **script qui rejoue le jeu de référence et produit le rapport** (annexe C du plan) doit être le premier livrable technique, avant même `VENTE`. Avec des agents IA, c'est le garde-fou principal : aucune modification du prompt ou des règles ne passe sans relance des évaluations.

### 4.7 Dépendances externes : le vrai chemin critique

Avec des agents IA, les phases de développement se compressent. Ce qui ne se compresse pas :

- création de la société (nécessaire pour la vérification WhatsApp Business et le compte agrégateur) ;
- vérification de l'entreprise par Meta (plusieurs jours à plusieurs semaines) ;
- ouverture du compte agrégateur et vérification d'identité (KYC) ;
- recrutement et accompagnement des PME pilotes ;
- rendez-vous juriste (données personnelles, conditions de paiement).

Ces cinq démarches démarrent **la semaine 1**, en parallèle du développement.

### 4.8 Hébergement et données

Le rapport promettait une « souveraineté 100 % Cameroun ». Pour un pilote, un hébergeur standard (Europe ou Afrique du Sud) avec chiffrement, sauvegardes quotidiennes et accès restreint est acceptable, **sous réserve de l'avis du juriste** sur la loi camerounaise sur les données personnelles. Le code doit rester portable (conteneurs, PostgreSQL standard) pour pouvoir migrer vers un hébergeur local si un partenariat l'exige.

### 4.9 Ton et langue

Le rapport dit « camfranglais », le plan dit « avec parcimonie ». Position proposée : Moki **comprend** le français, le franglais et les tournures locales ; il **répond** en français simple, tutoiement, avec quelques expressions locales validées par les pilotes. L'anglais (régions anglophones) est une V2.

### 4.10 Ce qui reste exact dans le plan et qu'on garde tel quel

Les besoins B1 à B10 et leur ordre, les règles de confirmation selon le risque, les 7 règles non négociables, le schéma de base, les 5 niveaux de test, le protocole de pilote et les critères go / no-go. Le plan complet (`02-plan-complet.md`) les reprend sans les réécrire.

---

## 5. Décisions à valider par le duo

| # | Décision | Pourquoi | Statut |
|---|---|---|---|
| D1 | WhatsApp est le seul canal de saisie en V1 ; l'app Flutter est gelée | Un seul canal à fiabiliser ; l'app n'a pas de backend | À valider |
| D2 | Paiement en deux étages : déclaratif (A) puis lien agrégateur (B) | Lever le risque réglementaire et livrer de la valeur dès la phase 1 | À valider |
| D3 | Relances en mode « Moki rédige, la PME transfère » par défaut | Zéro coût, zéro spam, confiance du client | À valider |
| D4 | Backend Python / FastAPI / PostgreSQL, modèle de langage Claude via API, intégrations derrière des interfaces remplaçables | Stack que les agents IA maîtrisent très bien, un seul moteur de base, portabilité | À valider |
| D5 | Le modèle de langage n'exécute rien et ne calcule aucun montant | Cible « 0 erreur grave » | À valider |
| D6 | Le harnais d'évaluation est le premier livrable technique | Garde-fou pour le travail avec des agents IA | À valider |
| D7 | Les démarches externes (société, Meta, agrégateur, juriste, pilotes) démarrent la semaine 1 | Chemin critique | À valider |
| D8 | Aucun score crédit, aucune prédiction, aucun USSD en V1 ; ils figurent dans la « vision » du dossier | Ne rien promettre qu'on ne mesure pas | À valider |
| D9 | Ajout des intentions `PAIEMENT_RECU`, `CONFIRMATION`, `HUMAIN` et de la vente à crédit | Cas fréquents oubliés | À valider |
| D10 | Les chiffres du rapport (2 h/jour, 25–35 % de retour) deviennent des hypothèses mesurées pendant le pilote | Dossier de financement crédible | À valider |
