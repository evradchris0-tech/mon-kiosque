# 06 · Interface pro de Mon Kiosque (v2) : contrat de conception

Document de référence pour tous les agents. **Lis-le en entier avant d'écrire une ligne.** Il fixe ce qui est commun (jetons, fichiers, API JS, API HTTP) pour que chacun travaille en parallèle sans se marcher dessus.

## 0. Règles du projet

1. **Version stable intouchable.** L'appli actuelle (`/app`, fichier `backend/app/static/app.html`) ne se modifie PAS. La nouvelle interface vit entièrement sous `backend/app/static/ui/` et est servie sous `/ui/` (déjà montée dans `main.py`). Elle ne remplacera `/app` qu'après validation.
2. **Les maquettes sont celles d'un autre produit** (`maquettes/*.dc.html`, « OCTAVE · La Maison VH » : réservations, envois, clés). On s'en sert pour la **structure des écrans, la rigueur, les composants et les états** (chargement, vide, erreur), jamais pour le contenu métier. Chaque écran est **adapté à Mon Kiosque** : PME camerounaise, ventes, dépenses, factures, impayés, trésorerie, dossier de crédit, impôt, Moki l'assistant. Pour lire une maquette : `maquettes/<Nom>.dc.html` est du HTML avec des styles inline lisibles ; ignore `support.js`, `/_blob/…` et les balises `x-dc`/`helmet`, lis le markup et le CSS. `maquettes/octave.css` contient des styles partagés utiles. `maquettes/Charte.dc.html` et `Composants.dc.html` décrivent le système de design.
3. **Icônes : uniquement celles du dossier `icones/`** (copiées dans `backend/app/static/ui/icones/`, fichiers `vh-<nom>-clair.png` = trait vert foncé pour fond clair, `vh-<nom>-fonce.png` = trait blanc pour fond foncé, 96×96, transparentes). **Interdit** : emoji ou caractères décoratifs utilisés comme icônes, SVG dessinés à la main, bibliothèques d'icônes. Le logo de la marque est `backend/app/static/ui/img/logo.svg` (hexagone orange, vrai logo). Si un concept n'a pas d'icône, on met un libellé texte (jamais une icône inventée).
4. **Langue** : français partout, tutoiement, ton court et direct (comme Moki). Montants en FCFA avec espace fine insécable : « 15 000 F ».
5. **Pas de dépendance externe** sauf les polices Google (Bricolage Grotesque, Instrument Sans) avec repli système. Pas de framework, pas de CDN de scripts, pas de build : HTML/CSS/JS purs, scripts classiques (pas de modules ES, ils compliquent le service worker).
6. **Sécurité** : toute donnée venant de l'API est échappée avant d'entrer dans du HTML (`MK.echapper`) ou injectée avec `textContent`. Jamais `eval`, jamais d'attribut `on*=` généré avec des données.
7. **Accessibilité** : cibles tactiles ≥ 44 px, contraste AA, focus visible, `aria-label` sur les boutons-icônes, `aria-current="page"` sur l'onglet actif, `prefers-reduced-motion` respecté, un seul `h1` par écran.
8. **Ne jamais atterrir dans le chat** : après connexion on arrive sur **Accueil**. L'assistant est un onglet parmi d'autres.

## 1. Jetons de design (adaptés de la charte OCTAVE, marque Mon Kiosque)

Le vert profond de la charte porte les icônes et les en-têtes ; l'**orange Mon Kiosque** porte l'action.

| Jeton CSS | Valeur | Usage |
|---|---|---|
| `--ink` | `#12211D` | texte principal, texte sur bouton orange |
| `--muted` | `#55635F` | texte secondaire |
| `--soft` | `#74827D` | texte tertiaire, placeholders |
| `--bg` | `#F3F5F4` | fond d'écran |
| `--surface` | `#FFFFFF` | cartes |
| `--line` | `#D9DFDC` | bordures |
| `--line-soft` | `#E6EAE8` | séparateurs |
| `--green` | `#1B4B40` | marque secondaire, en-têtes, icônes |
| `--green-2` | `#245B4E` | survol sur vert |
| `--green-tint` | `#E2EFEA` | fonds doux, pastille neutre/succès |
| `--orange` | `#FF7900` | actions principales, onglet actif, accent |
| `--orange-dark` | `#E65100` | survol/pression orange |
| `--orange-tint` | `#FFF1E0` | fond doux orange |
| `--danger` / `--danger-bg` / `--danger-line` | `#9B1C1C` / `#FDE8E6` / `#E9B8B3` | retard, erreur, urgent |
| `--warn` / `--warn-bg` | `#8A5A00` / `#FFF1D6` | attention |
| `--ok` / `--ok-bg` | `#1B4B40` / `#E2EFEA` | payé, réussi |

Typographie : titres `Bricolage Grotesque` 600 (`--font-titre`), corps `Instrument Sans` 400/500/600 (`--font-corps`), chiffres en `font-variant-numeric: tabular-nums`. Échelle : 12 / 13 / 14 / 16 / 20 / 26 / 34 px. Rayons : 10 (champs), 14 (cartes), 999 (pastilles, boutons ronds). Espacements en multiples de 4. Ombres très légères (`0 1px 2px rgba(18,33,29,.06)`), bordures de 1 px de préférence aux ombres. Largeur de contenu max 1100 px.

Bouton principal : fond `--orange`, texte `--ink` gras (le blanc sur orange n'est pas assez contrasté). Onglet actif : barre/pastille orange, icône « clair » sur fond clair.

## 2. Structure des fichiers (propriété par agent)

```
backend/app/static/ui/
  index.html              coquille : charge CSS/JS dans l'ordre, <div id="app">          [Fondations]
  manifest.webmanifest    PWA (start_url /ui/, scope /ui/)                                [Fondations]
  sw.js                   service worker (cache de la coquille, jamais /api)              [Fondations]
  css/app.css             jetons + composants communs + coquille                          [Fondations]
  css/ecr-<nom>.css       styles propres à un écran                                       [agent de l'écran]
  js/core.js              espace MK : api, état, routeur, outils, composants              [Fondations]
  js/mock.js              données factices pour ?mock=1 (tous les endpoints §5)           [Fondations]
  js/shell.js             en-tête, barre d'onglets, menu latéral desktop, cloche          [Fondations]
  js/ecr-<nom>.js         un écran = un fichier                                           [agent de l'écran]
  js/main.js              démarrage                                                       [Fondations]
  icones/ img/ icons/     ressources                                                      [Fondations]
```

`index.html` charge dans cet ordre : `css/app.css`, tous les `css/ecr-*.css`, puis `js/core.js`, `js/mock.js`, `js/shell.js`, tous les `js/ecr-*.js`, enfin `js/main.js`. **Fondations liste d'avance tous les fichiers d'écran prévus** (§4) ; un fichier absent ne doit pas casser la page (un `<script>` manquant est ignoré ; crée des fichiers vides `ecr-*.js`/`.css` pour les écrans à venir). Aucun agent d'écran ne modifie les fichiers d'un autre agent ni ceux de Fondations : s'il manque un composant commun, il le définit localement dans son CSS avec son préfixe, et le signale dans son rapport.

## 3. API JavaScript commune (`window.MK`, défini dans `js/core.js`)

```js
MK.etat            // { token, pme:{nom_commerce, ville}|null, demo:boolean, numero, alertesNonLues:number }
MK.api(chemin, corps?)         // Promise<json>. GET si pas de corps, sinon POST ; PUT/DELETE : MK.api(chemin, corps, "PUT")
                               // ajoute Authorization: Bearer <token>; 401 → MK.deconnecter(); erreurs → Error avec .status et .message (champ "detail")
                               // avec ?mock=1 : répond depuis js/mock.js (latence simulée 250 ms)
MK.deconnecter()               // efface le token, va sur #/connexion
MK.fmt.fcfa(n)                 // 15000 → "15 000 F" (espace fine insécable)
MK.fmt.fcfaCourt(n)            // 83000 → "83 k", 1500000 → "1,5 M"
MK.fmt.date(iso)               // "12 nov."   ; MK.fmt.dateLongue(iso) → "jeudi 12 novembre" ; MK.fmt.heure(iso) → "14:05"
MK.fmt.relatif(iso)            // "il y a 3 j", "aujourd'hui", "hier"
MK.fmt.jours(n)                // 1 → "1 jour", 3 → "3 jours"
MK.echapper(txt)               // échappe & < > " '
MK.icone(nom, {taille:24, variante:"clair"|"fonce", classe:""})  // → '<img class="ico" src="/ui/icones/vh-NOM-VARIANTE.png" width height alt="" aria-hidden="true">'
MK.ecran(id, def)              // enregistre un écran : def = { titre, onglet:"accueil"|"suivi"|"assistant"|"alertes"|"reglages"|null,
                               //   plein:boolean (true = sans barre d'onglets, ex. connexion), retour:"id"|null (affiche la flèche retour),
                               //   rendre(el, params) → peut renvoyer une Promise ; peut renvoyer une fonction de nettoyage }
MK.aller(id, params?)          // navigation (hash "#/id?cle=val") ; MK.retour() revient en arrière
MK.params                       // paramètres de la route courante (objet)
MK.toast(msg, type)            // type: "ok"|"erreur"|"info", disparaît en 3,5 s, role="status"
MK.feuille({titre, contenu:Node|string, actions:[{libelle, primaire, onclick}]}) → { fermer() }   // bottom-sheet mobile / modale desktop
MK.squelette(nbLignes)         // HTML d'un état de chargement (blocs gris animés)
MK.etatVide({titre, texte, action:{libelle, ecran, params}})   // HTML d'un état vide
MK.etatErreur(err, reessayer:Function)                         // HTML + bouton « Réessayer » ; renvoie un Node
MK.pastille(texte, type)       // type: "ok"|"attention"|"urgent"|"info"|"neutre" → HTML
MK.amorcerAssistant(texte)     // va sur l'assistant et pré-remplit le champ (sans envoyer)
MK.envoyerAssistant(texte)     // va sur l'assistant et envoie le message
```

Composants CSS communs fournis par Fondations (classes) : `.carte`, `.carte-titre`, `.kpi` (`.kpi-valeur`, `.kpi-libelle`, `.kpi-note`), `.btn` (`.primaire` orange, `.secondaire` bordé, `.discret`, `.danger`, `.plein`), `.pastille` (`.ok .attention .urgent .info .neutre`), `.liste` + `.ligne` (`.ligne-ico`, `.ligne-corps`, `.ligne-titre`, `.ligne-sous`, `.ligne-fin`), `.segment` (contrôle segmenté, boutons `[aria-pressed]`), `.champ` (`label` + `input/select`, `.champ-aide`, `.champ-erreur`), `.bandeau` (`.urgent .attention .info .ok`), `.entete-ecran` (`h1` + `.sous`), `.grille` (auto-fit), `.squelette`, `.vide`, `.feuille`, `.table` (tableau responsive qui devient liste sur mobile), `.sr-only`, `.montant` (chiffres tabulaires), `.positif`/`.negatif`. Les écrans écrivent leur markup avec ces classes et leurs propres classes préfixées (`.acc-*`, `.ass-*`, `.sui-*`, `.chi-*`, `.reg-*`, `.con-*`).

## 4. Écrans, routes, maquettes sources, propriétaires

Navigation : barre d'onglets en bas sur mobile (< 900 px), menu latéral replié/déplié sur desktop (≥ 900 px, voir `Menu.dc.html`). Onglets : **Accueil**, **Suivi**, **Moki** (assistant), **Alertes**, **Réglages**. En-tête : logo, titre de l'écran, boutons Recherche (icône `recherche`) et Cloche (icône `alertes` + badge du nombre d'alertes non lues).

| Route | Écran | Icône d'onglet/menu | Maquettes à lire | Propriétaire |
|---|---|---|---|---|
| `connexion` | Connexion + création de compte (3 champs) + mise en route | — | `Connexion`, `MiseEnRoute`, `Parcours`, `EssaiBlanc` | **C** (`ecr-connexion`) |
| `accueil` | Accueil : salutation, bandeau d'alerte principal, KPI, actions rapides, « À faire », courbe 7 jours, activité récente | `accueil` | `Accueil`, `MobileAccueil`, `Alerte`, `Cloche` | **D** (`ecr-accueil`) |
| `alertes` | Liste des alertes (urgent / attention / info), marquer comme lues | `alertes` | `Alertes`, `Alerte`, `Cloche` | **D** (`ecr-alertes`) |
| `assistant` | Moki : conversation, suggestions, cartes PDF, OUI/NON, dictée | `assistant` | `Assistant`, `EnvoiPonctuel`, `Apercu` | **E** (`ecr-assistant`) |
| `aide` | Aide : ce que Moki sait faire (phrases cliquables), FAQ, parler à un humain | `aide` | `Aide` | **E** (`ecr-aide`) |
| `recherche` | Recherche globale clients/produits/factures | `recherche` | `Recherche` | **E** (`ecr-recherche`) |
| `suivi` | Suivi : segments Factures / Impayés / Clients / Produits | `suivi` | `Main`, `Mobile`, `Etats` | **F** (`ecr-suivi`) |
| `facture` (param `id`) | Fiche facture : lignes, état, relances, paiements, aperçu du message client, actions | — (retour `suivi`) | `Reservation`, `MobileReservation`, `Apercu`, `Etats` | **F** (`ecr-facture`) |
| `client` (param `id`) | Fiche client : historique achats/paiements/dette | — | `Reservation`, `HistoriqueDetail` | **F** (`ecr-client`) |
| `reglages` | Hub des réglages : liens vers Chiffres, Historique, Documents, Connexions, Paramètres, Aide, Déconnexion | `parametres` | `Menu`, `MobileParametres` | **G** (`ecr-reglages`) |
| `chiffres` | Chiffres : période Jour/Semaine/Mois/Année, ventes/charges/bénéfice, trésorerie, pro vs perso, top produits, dépenses par poste | `concurrence` | `Concurrence`, `MobileConcurrence` | **G** (`ecr-chiffres`) |
| `historique` | Historique de toutes les opérations avec filtres + détail en feuille | `historique` | `Historique`, `HistoriqueDetail` | **G** (`ecr-historique`) |
| `documents` | Dossier de crédit (progression vers 6 mois, génération PDF), impôt IGS estimé, échéances fiscales | `modeles` | `Modeles`, `ModeleEdition`, `Parcours` | **G** (`ecr-documents`) |
| `connexions` | État des connexions : WhatsApp (simulé en démo), Orange Money / MTN MoMo (bientôt), banque et DGI (feuille de route) | `connexions` | `Connexions` | **G** (`ecr-connexions`) |
| `parametres` | Paramètres : commerce, mode d'envoi (transfert/direct), seuil de confirmation renforcée, notifications | `parametres` | `Parametres`, `MobileParametres` | **G** (`ecr-parametres`) |
| `introuvable`, hors-ligne, erreurs | Page 404, bandeau « hors ligne », état d'erreur réseau | — | `Erreur404`, `Erreurs`, `ErreursGuide`, `Etats` | **Fondations** (dans `core`/`shell`) |

Règles de contenu par écran : états **chargement** (squelette), **vide**, **erreur** (avec « Réessayer »), **succès** obligatoires. Aucune donnée en dur dans un écran : tout vient de l'API (ou du mock).

## 5. API HTTP (toutes sous `/api`, jeton `Authorization: Bearer`)

Existantes (ne pas changer leur forme) : `POST /api/connexion`, `POST /api/chat`, `GET /api/tableau`, `GET /api/dossier`, `GET /api/notifications`, `GET /api/fichier`.

**Nouvelles** (à implémenter côté backend, `backend/app/api/ecrans.py`, toutes filtrées par la PME du jeton ; un id d'une autre PME → 404). Montants = entiers FCFA. Dates = ISO 8601 UTC sans fuseau (`"2026-11-12T09:30:00"`) sauf mention « date ».

```
POST /api/inscription      {nom_commerce, ville, secteur} → {pme:{nom_commerce, ville}}   (422 si champ vide ; 409 si le numéro a déjà un compte)

GET  /api/accueil → {
  gerante: "Marie"|null, commerce, demo:boolean, date_locale:"jeudi 12 novembre",
  kpis: {ventes_jour, nb_ventes_jour, tresorerie, benefice_mois, impayes},
  alerte_principale: {id, niveau, titre, texte, action:{ecran, params}|null} | null,
  a_faire: [{id, type:"relance"|"echeance"|"dossier"|"info", titre, texte, action:{ecran, params}|null}],
  serie_7j: [{jour:"Lun", ventes}], activite_recente: [<element d'historique> ×5],
  non_lues: number
}

GET  /api/alertes → {non_lues:number, alertes:[{id, type:"retard"|"echeance"|"resume"|"charge"|"client"|"info",
                     niveau:"urgent"|"attention"|"info", titre, texte, date:ISO, lue:boolean, action:{ecran, params}|null}]}
POST /api/alertes/lues     {} → {non_lues:0}

GET  /api/historique?type=tout|vente|depense|facture|paiement&q=&limite=30&avant=<id> → {elements:[<element>], suivant:<id>|null}
     <element> = {id:"vente-12", type, date:ISO, titre, detail, montant, sens:"entree"|"sortie"|"neutre", statut:"ok"|"annule"|"en_attente"|"retard", client:string|null}
GET  /api/historique/{type}/{id} → {element:<element>, lignes:[{libelle, quantite, prix_unitaire, montant}], notes:[string], annulable:boolean}

GET  /api/factures?statut=tout|envoyee|payee|en_retard → {factures:[{id, numero, client, client_id, total, statut:"envoyee"|"payee"|"en_retard", jours_retard, date:ISO, echeance:date|null}]}
GET  /api/factures/{id} → {id, numero, client, client_id, telephone|null, date, echeance, statut, jours_retard, total,
                           lignes:[{libelle, quantite, prix_unitaire, montant}], frais:[{libelle, montant}],
                           relances:[{date:ISO, mode, texte}], paiements:[{date:ISO, montant, source}],
                           message_client:string, lien_paiement:string, paiement_simule:true, pdf_url:string|null}

GET  /api/clients → {clients:[{id, nom, telephone|null, quartier|null, dette, nb_achats, total_achats, dernier_achat:ISO|null, inactif:boolean}]}
GET  /api/clients/{id} → {client:{...idem}, achats:[<element>], factures:[{id, numero, total, statut}], paiements:[<element>], dette}
GET  /api/produits → {produits:[{id, nom, prix, ventes_30j, ca_30j}]}

GET  /api/chiffres?periode=jour|semaine|mois|annee → {periode, libelle, ventes, charges, benefice, stock, retraits_perso, tresorerie,
        par_mode:{cash, mobile_money, credit, facture}, nb_ventes, panier_moyen,
        serie:[{libelle, ventes, charges}], top_produits:[{nom, total}], depenses_par_poste:[{libelle, total}]}

GET  /api/documents → {dossier:{historique_mois, requis:6, manque_mois, pret:boolean, fictives:boolean},
                       impot:{estimation, ca_annuel, taux, note}, echeances:[{libelle, date, jours}]}

GET  /api/parametres → {commerce:{nom_commerce, nom_gerante, ville, quartier, secteur, numero},
                        preferences:{mode_relance:"transfert"|"direct", seuil_confirmation_renforcee, resume_du_soir:boolean, rappels_fiscaux:boolean}, demo:boolean}
PUT  /api/parametres       {commerce?:{nom_commerce?, nom_gerante?, ville?, quartier?, secteur?}, preferences?:{...}}
     → même forme que GET ; validation : mode_relance ∈ {transfert,direct}, seuil ∈ [1000, 10 000 000], textes ≤ 120 caractères, 422 sinon

GET  /api/connexions → {connexions:[{id:"whatsapp"|"orange_money"|"mtn_momo"|"banque"|"dgi", nom, statut:"simule"|"connecte"|"bientot", detail}]}
GET  /api/recherche?q= → {clients:[{id, nom, detail}], produits:[{id, nom, detail}], factures:[{id, numero, client, total, statut}]}   (q ≥ 2 caractères, sinon listes vides)
```

## 6. Mode mock (`?mock=1`)

`/ui/?mock=1` fait répondre `MK.api` depuis `js/mock.js` : données réalistes de « Chez Marie » (restaurant à Yaoundé), **toutes les routes du §5 plus les existantes**, avec de la latence simulée, et un cas vide/erreur déclenchable (`?mock=1&cas=vide` / `&cas=erreur`). `?mock=1&ecran=<route>` ouvre directement un écran sans connexion. Les écrans doivent fonctionner pleinement dans ce mode : c'est ainsi qu'ils sont développés et capturés en images sans backend.

## 7. Lancer, tester, capturer

- **Mock** : sers `backend/app/static/ui/` avec n'importe quel serveur statique, ou lance le backend : `cd backend && .venv/Scripts/uvicorn.exe app.api.main:creer_app --factory --port 8000`, puis `http://localhost:8000/ui/?mock=1`. Avec `MOKI_DEMO_SEED=1 MOKI_ACCES_DEMO=1` (variables d'environnement), le vrai backend sert aussi les données de démo : connexion avec le numéro `237677000001`.
- **Captures** : `"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --window-size=420,900 --virtual-time-budget=6000 --screenshot=<fichier.png> "http://localhost:8000/ui/?mock=1&ecran=accueil"`. Regarde tes captures avec l'outil Read et corrige. Largeurs à vérifier : 390 (téléphone), 768, 1280 (desktop). Les chemins temporaires vont dans le dossier scratchpad de la session.
- **Tests backend** : `cd backend && .venv/Scripts/python.exe -m pytest tests -q` (tous doivent rester verts) et `.venv/Scripts/ruff.exe check app tests`.
- **Aucun** appel réseau réel vers des services tiers, aucune clé API dans le code.

## 8. Barre de qualité

Niveau « maquette » : alignements au pixel près, rythme vertical régulier, hiérarchie typographique nette, états de survol/focus/pression, transitions de 150 ms, aucun texte coupé ou débordant à 360 px, aucun défilement horizontal, aucune erreur dans la console. Pas de lorem ipsum, pas de « TODO », pas de code mort. Chaque écran se vérifie par captures à 390 px et 1280 px.
