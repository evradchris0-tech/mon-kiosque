# Mon Kiosque

**Le 3-en-1 de la PME camerounaise. Propulsé par Moki, l'IA qui parle Camfranglais.**

Mon Kiosque est un prototype d'application mobile pensé pour les petites entreprises camerounaises (boutiques, snacks, restaurants, services). Il réunit dans une seule application :

- **Paiement** : encaisser en cash, en Orange Money (QR code) ou les deux à la fois, avec chaque vente tracée automatiquement.
- **Gestion client** : savoir qui paie, qui tarde et qui revient.
- **Prospection** : Moki, un assistant IA qui rédige les factures, relance les clients et fait le point sur les ventes.

Projet réalisé pour le **Business Game IA #2CDYS 2026** (Orange Cameroun × Influence au Mboa, 23 avril 2026, Orange Business Center, Yaoundé). Le rapport complet de la solution (marché, offre, modèle économique) se trouve dans [`MonKiosque_RapportFinal.docx`](MonKiosque_RapportFinal.docx).

## Fonctionnalités du prototype

L'application est organisée en quatre onglets, précédés d'un écran d'accueil (onboarding) :

| Onglet | Ce qu'il montre |
| --- | --- |
| **Chat** | Les conversations WhatsApp Business de la PME, avec un bouton « Moki Analyse » dans chaque conversation. |
| **Moki** | L'assistant IA : génération de factures, bilan des ventes de la veille, relances clients. |
| **Tableau** | Chiffre d'affaires du jour, graphique des ventes des 7 derniers jours, taux de digitalisation, top clients, impayés, score crédit. Donne accès à l'écran d'encaissement (Orange Money, cash ou hybride, avec QR code). |
| **Profil** | Langue (français / anglais), abonnement, sécurité, support, mode démo. |

### Mode démo

Dans **Profil → Mode Démo (Hackathon)**, un interrupteur lance un parcours guidé en 6 scènes qui suit Marie, gérante du snack « Chez Marie » : consultation des ventes du matin, commande reçue sur WhatsApp, détection de l'opportunité par Moki, facture générée, encaissement hybride (Orange Money + cash) et hausse du score crédit.

### Limites du prototype

C'est une maquette fonctionnelle de démonstration, sans serveur :

- les ventes et les clients sont des données d'exemple gardées en mémoire, et elles sont réinitialisées à chaque lancement ;
- les réponses de Moki sont simulées à partir de mots-clés (« facture », « vente », « hier »…) ;
- la confirmation de paiement Orange Money est simulée ;
- l'intégration WhatsApp Business n'est pas branchée.

Seuls la langue choisie et le passage de l'onboarding sont enregistrés sur l'appareil.

## Lancer l'application

Prérequis : [Flutter](https://docs.flutter.dev/get-started/install) avec un SDK Dart 3.10 ou plus récent, et un émulateur, un téléphone ou un navigateur.

```bash
cd app
flutter pub get
flutter run
```

Pour lancer la version web dans Chrome :

```bash
cd app
flutter run -d chrome
```

## Stack technique

- **Flutter / Dart** : Android, iOS et web
- **provider** : gestion de l'état (langue, onboarding, mode démo, ventes)
- **go_router** : navigation par onglets (`StatefulShellRoute`)
- **fl_chart** : graphiques du tableau de bord
- **qr_flutter** : QR codes de paiement
- **flutter_localizations / intl** : interface en français et en anglais
- **shared_preferences** : préférences locales
- **google_fonts**, **flutter_svg** : typographie et logo

## Structure du dépôt

```
.
├── MonKiosque_RapportFinal.docx   Rapport complet de la solution
├── logo.png                       Logo (fichier SVG)
└── app/                           Application Flutter
    ├── lib/
    │   ├── main.dart
    │   ├── l10n/                  Traductions (app_fr.arb, app_en.arb)
    │   └── src/
    │       ├── app_state/         Contrôleurs : langue, onboarding, mode démo
    │       ├── data/              Modèles et données de ventes
    │       ├── features/          Écrans : chat, moki, dashboard, payment, profile, onboarding, shell
    │       ├── router/            Routes go_router
    │       └── theme/             Couleurs et thème
    ├── assets/images/
    ├── android/  ios/  web/
    └── pubspec.yaml
```

Les traductions sont dans `app/lib/l10n/`. Le fichier de référence est `app_fr.arb`, et Flutter régénère les classes `AppL10n` à chaque build.
