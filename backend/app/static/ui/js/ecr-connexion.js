/* Mon Kiosque : écran Connexion (numéro WhatsApp), création de compte et mise en route. Contrat : docs/06-interface-pro.md. */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;
  var NUMERO_DEMO = "237677000001";
  var SECTEURS = ["Boutique", "Restaurant / snack", "Services"];

  var PROMESSES = [
    { ico: "assistant", texte: "Tes ventes et tes dépenses notées en une phrase" },
    { ico: "suivi", texte: "Tes factures et tes relances prêtes à envoyer" },
    { ico: "modeles", texte: "Ton dossier de crédit et ton impôt estimé" }
  ];

  var ETAPES = [
    { ico: "parcours", titre: "Ajoute tes produits", texte: "Dis à Moki ce que tu vends et à quel prix. Une phrase suffit." },
    { ico: "assistant", titre: "Note ta première vente", texte: "Écris par exemple « j'ai vendu 3 poulets à 3 500 »." },
    { ico: "accueil", titre: "Vois ton tableau de bord", texte: "Ventes du jour, trésorerie et impayés, d'un coup d'œil." }
  ];

  function chiffres(txt) { return String(txt || "").replace(/\D/g, ""); }

  function marque() {
    return '<aside class="con-marque">' +
      '<div class="con-marque-tete"><span class="con-logo"><img src="/ui/img/logo.svg" alt=""></span><span class="con-nom">Mon Kiosque</span></div>' +
      '<p class="con-accroche">Le 3-en-1 de la PME camerounaise. <b>Propulsé par Moki.</b></p>' +
      '<ul class="con-promesse">' + PROMESSES.map(function (p) { return "<li>" + MK.icone(p.ico, { taille: 24, variante: "fonce" }) + "<span>" + e(p.texte) + "</span></li>"; }).join("") + "</ul>" +
      "</aside>";
  }

  /* Bandeau d'erreur ou d'information, injecté dans la zone vivante de la vue. */
  function bandeau(type, titre, texte, reessayer) {
    return '<div class="bandeau ' + type + '"><div class="bandeau-corps"><div class="bandeau-titre">' + e(titre) + "</div>" +
      (texte ? '<div class="bandeau-texte">' + e(texte) + "</div>" : "") +
      (reessayer ? '<div class="bandeau-actions"><button type="button" class="btn secondaire petit" data-reessayer>Réessayer</button></div>' : "") +
      "</div></div>";
  }

  MK.ecran("connexion", {
    titre: "Connexion",
    onglet: null,
    plein: true,
    rendre: function (el) {
      var etat = { vue: "connexion", occupe: false, session: null, finalisee: false, numeroSaisi: NUMERO_DEMO };
      var premiereFois = true;

      el.innerHTML = '<div class="con">' + marque() + '<main class="con-contenu"><div class="con-boite" data-boite></div></main></div>';
      var boite = el.querySelector("[data-boite]");

      /* ----- utilitaires de vue ----- */
      function q(sel) { return boite.querySelector(sel); }
      function zoneMessage() { return q("[data-msg]"); }
      function message(html, reessayer) {
        var z = zoneMessage();
        if (!z) return;
        z.innerHTML = html;
        var b = z.querySelector("[data-reessayer]");
        if (b && reessayer) b.addEventListener("click", reessayer);
      }
      function effacerMessage() { var z = zoneMessage(); if (z) z.textContent = ""; }

      function champErreur(nom, texte) {
        var champ = q('[data-champ="' + nom + '"]');
        if (!champ) return;
        var input = champ.querySelector("input");
        var err = champ.querySelector(".champ-erreur");
        var aide = champ.querySelector(".champ-aide");
        var ids = [];
        if (aide) ids.push(aide.id);
        if (texte) {
          err.textContent = texte;
          err.hidden = false;
          ids.push(err.id);
          input.setAttribute("aria-invalid", "true");
        } else {
          err.textContent = "";
          err.hidden = true;
          input.removeAttribute("aria-invalid");
        }
        if (ids.length) input.setAttribute("aria-describedby", ids.join(" ")); else input.removeAttribute("aria-describedby");
      }

      function occuper(actif, bouton) {
        etat.occupe = actif;
        if (actif) boite.setAttribute("data-occupe", "1"); else boite.removeAttribute("data-occupe");
        if (bouton) { if (actif) bouton.setAttribute("aria-busy", "true"); else bouton.removeAttribute("aria-busy"); }
        var live = q("[data-statut]");
        if (live) live.textContent = actif ? "Un instant…" : "";
      }

      function focaliser(cible) {
        var x = typeof cible === "string" ? q(cible) : cible;
        if (x) { try { x.focus(); } catch (err) { /* focus indisponible */ } }
      }

      /* Les champs de champ(…) : libellé, saisie, aide, erreur. */
      function champ(o) {
        return '<div class="champ" data-champ="' + o.nom + '"><label for="con-' + o.nom + '">' + e(o.libelle) + "</label>" +
          '<input id="con-' + o.nom + '" name="' + o.nom + '" type="' + (o.type || "text") + '"' + (o.mode ? ' inputmode="' + o.mode + '"' : "") +
          ' autocomplete="' + o.auto + '"' + (o.max ? ' maxlength="' + o.max + '"' : "") + (o.placeholder ? ' placeholder="' + e(o.placeholder) + '"' : "") +
          ' value="' + e(o.valeur || "") + '"' + (o.aide ? ' aria-describedby="con-' + o.nom + '-aide"' : "") + ' spellcheck="false">' +
          (o.aide ? '<span class="champ-aide" id="con-' + o.nom + '-aide">' + e(o.aide) + "</span>" : "") +
          '<span class="champ-erreur" id="con-' + o.nom + '-err" hidden></span></div>';
      }

      var RAPPEL = '<p class="con-rappel"><b>Un numéro = un compte.</b> Ton numéro WhatsApp sert d\'identifiant : pas de mot de passe à retenir.</p>';
      var ZONES = '<div class="con-msg" data-msg aria-live="assertive" aria-atomic="true"></div><div class="sr-only" data-statut role="status" aria-live="polite"></div>';

      /* ----- vue 1 : connexion ----- */
      function vueConnexion() {
        boite.innerHTML =
          '<div class="con-tete"><h1 id="con-titre" tabindex="-1">Connexion</h1><p class="con-sous">Entre ton numéro WhatsApp pour retrouver ton kiosque.</p></div>' +
          ZONES +
          '<form class="con-form" novalidate data-form>' +
            champ({ nom: "numero", libelle: "Numéro WhatsApp", type: "tel", mode: "tel", auto: "tel", valeur: etat.numeroSaisi, aide: "Avec l'indicatif du pays, sans espace. Exemple : " + NUMERO_DEMO + "." }) +
            '<button type="submit" class="btn primaire plein">Entrer</button>' +
          "</form>" +
          '<div class="con-ou" aria-hidden="true">ou</div>' +
          '<div class="con-demo"><button type="button" class="btn secondaire plein" data-demo>Utiliser le compte de démonstration</button>' +
          '<p class="con-demo-note"><b>Données fictives.</b> Compte d\'essai sur le numéro ' + NUMERO_DEMO + " : rien n'est envoyé à de vrais clients.</p></div>" +
          RAPPEL;

        var input = q("#con-numero");
        input.addEventListener("input", function () { etat.numeroSaisi = input.value; if (input.hasAttribute("aria-invalid")) champErreur("numero", ""); });
        q("[data-form]").addEventListener("submit", function (ev) {
          ev.preventDefault();
          if (etat.occupe) return;
          var brut = input.value.trim();
          var n = chiffres(brut);
          if (!brut) { champErreur("numero", "Entre ton numéro WhatsApp."); focaliser(input); return; }
          if (/[^\d\s+().-]/.test(brut)) { champErreur("numero", "Le numéro ne doit contenir que des chiffres."); focaliser(input); return; }
          if (n.length < 8 || n.length > 15) { champErreur("numero", "Ton numéro doit avoir entre 8 et 15 chiffres, indicatif compris (ex. " + NUMERO_DEMO + ")."); focaliser(input); return; }
          champErreur("numero", "");
          connecter(n, q('[type="submit"]'));
        });
        q("[data-demo]").addEventListener("click", function () {
          if (etat.occupe) return;
          champErreur("numero", "");
          etat.numeroSaisi = NUMERO_DEMO;
          input.value = NUMERO_DEMO;
          connecter(NUMERO_DEMO, q("[data-demo]"));
        });
      }

      function connecter(numero, bouton) {
        effacerMessage();
        occuper(true, bouton);
        MK.api("/api/connexion", { numero: numero }).then(function (r) {
          occuper(false, bouton);
          if (r && r.pme) {
            etat.finalisee = true;
            MK.ouvrirSession({ token: r.token, numero: r.numero || numero, pme: r.pme, demo: r.demo });
            MK.aller("accueil");
            return;
          }
          /* Numéro sans compte : la session est ouverte pour pouvoir s'inscrire, sans commerce encore. */
          etat.session = { token: r.token, numero: r.numero || numero, demo: !!r.demo };
          MK.etat.token = etat.session.token;
          MK.etat.numero = etat.session.numero;
          MK.etat.demo = etat.session.demo;
          garderPendant();
          montrer("creation");
        }, function (err) {
          occuper(false, bouton);
          if (err.reseau || err.status === 0) message(bandeau("urgent", "Impossible de joindre Mon Kiosque", "Vérifie ta connexion Internet puis réessaie.", true), function () { connecter(numero, bouton); });
          else if (err.status === 403) message(bandeau("attention", "La démonstration est fermée", "L'accès à Mon Kiosque est suspendu pour le moment. Réessaie un peu plus tard."));
          else if (err.status === 422) { champErreur("numero", "Ce numéro n'est pas valide. Vérifie-le et réessaie."); focaliser("#con-numero"); }
          else if (err.status >= 500) message(bandeau("urgent", "Un problème est survenu de notre côté", "Ce n'est pas de ton fait. Réessaie dans un instant.", true), function () { connecter(numero, bouton); });
          else message(bandeau("urgent", "Connexion impossible", err.message || "Réessaie dans un instant."));
        });
      }

      /* ----- vue 2 : création de compte ----- */
      function vueCreation() {
        var chips = SECTEURS.concat(["Autre"]).map(function (s) { return '<button type="button" class="puce" data-secteur="' + e(s) + '" aria-pressed="false">' + e(s) + "</button>"; }).join("");
        boite.innerHTML =
          '<div class="con-tete"><h1 id="con-titre" tabindex="-1">Crée ton compte</h1><p class="con-sous">Ce numéro n\'a pas encore de compte. Trois infos et tu es prêt.</p></div>' +
          '<div class="con-numero"><span class="con-numero-texte">Numéro<b>' + e(etat.session.numero) + '</b></span><button type="button" class="btn discret petit" data-changer aria-label="Changer de numéro">Changer</button></div>' +
          ZONES +
          '<form class="con-form" novalidate data-form>' +
            champ({ nom: "nom", libelle: "Nom du commerce", auto: "organization", max: 120, placeholder: "Ex. Chez Marie" }) +
            champ({ nom: "ville", libelle: "Ville", auto: "address-level2", max: 60, placeholder: "Ex. Yaoundé" }) +
            '<div class="con-secteur">' +
              champ({ nom: "secteur", libelle: "Secteur d'activité", auto: "off", max: 40, placeholder: "Ex. coiffure, couture, vente en gros…" }) +
              '<div role="group" aria-labelledby="con-choix"><div class="con-choix-titre" id="con-choix">Choix rapides</div><div class="puces">' + chips + "</div></div>" +
            "</div>" +
            '<button type="submit" class="btn primaire plein">Créer mon compte</button>' +
          "</form>" +
          RAPPEL;

        var nom = q("#con-nom"), ville = q("#con-ville"), secteur = q("#con-secteur");
        var boutons = Array.prototype.slice.call(boite.querySelectorAll("[data-secteur]"));
        function marquerChoix() {
          var v = secteur.value.trim();
          boutons.forEach(function (b) {
            var s = b.getAttribute("data-secteur");
            var actif = s === "Autre" ? !!v && SECTEURS.indexOf(v) < 0 : v === s;
            b.setAttribute("aria-pressed", actif ? "true" : "false");
          });
        }
        boutons.forEach(function (b) {
          b.addEventListener("click", function () {
            var s = b.getAttribute("data-secteur");
            if (s === "Autre") { if (SECTEURS.indexOf(secteur.value.trim()) >= 0) secteur.value = ""; focaliser(secteur); }
            else secteur.value = s;
            champErreur("secteur", "");
            marquerChoix();
          });
        });
        [nom, ville, secteur].forEach(function (inp) {
          inp.addEventListener("input", function () { if (inp.hasAttribute("aria-invalid")) champErreur(inp.id.replace("con-", ""), ""); if (inp === secteur) marquerChoix(); });
        });
        q("[data-changer]").addEventListener("click", function () { if (!etat.occupe) retourNumero(); });
        q("[data-form]").addEventListener("submit", function (ev) {
          ev.preventDefault();
          if (etat.occupe) return;
          var vals = { nom_commerce: nom.value.trim(), ville: ville.value.trim(), secteur: secteur.value.trim() };
          var premier = null;
          function verifier(nomChamp, input, valeur, requis, max) {
            var txt = !valeur ? requis : valeur.length > max ? "C'est trop long (" + max + " caractères au maximum)." : "";
            champErreur(nomChamp, txt);
            if (txt && !premier) premier = input;
          }
          verifier("nom", nom, vals.nom_commerce, "Entre le nom de ton commerce.", 120);
          verifier("ville", ville, vals.ville, "Entre ta ville.", 60);
          verifier("secteur", secteur, vals.secteur, "Choisis ou écris ton secteur d'activité.", 40);
          if (premier) { focaliser(premier); return; }
          inscrire(vals, q('[type="submit"]'));
        });
      }

      function inscrire(vals, bouton) {
        effacerMessage();
        occuper(true, bouton);
        MK.api("/api/inscription", vals).then(function (r) {
          occuper(false, bouton);
          etat.finalisee = true;
          MK.ouvrirSession({ token: etat.session.token, numero: etat.session.numero, demo: etat.session.demo, pme: (r && r.pme) || { nom_commerce: vals.nom_commerce, ville: vals.ville } });
          montrer("route");
        }, function (err) {
          occuper(false, bouton);
          if (err.reseau || err.status === 0) message(bandeau("urgent", "Impossible de joindre Mon Kiosque", "Vérifie ta connexion Internet puis réessaie. Ce que tu as saisi est conservé.", true), function () { inscrire(vals, bouton); });
          else if (err.status === 409) dejaUnCompte();
          else if (err.status === 422) message(bandeau("urgent", "Il manque une information", err.message));
          else if (err.status >= 500) message(bandeau("urgent", "Un problème est survenu de notre côté", "Ce n'est pas de ton fait. Réessaie dans un instant.", true), function () { inscrire(vals, bouton); });
          else message(bandeau("urgent", "Création impossible", err.message || "Réessaie dans un instant."));
        });
      }

      /* Le compte existe déjà (créé entre-temps, par exemple sur WhatsApp) : on se connecte simplement. */
      function dejaUnCompte() {
        MK.api("/api/connexion", { numero: etat.session.numero }).then(function (r) {
          if (r && r.pme) {
            etat.finalisee = true;
            MK.ouvrirSession({ token: r.token, numero: r.numero || etat.session.numero, pme: r.pme, demo: r.demo });
            MK.toast("Ce numéro avait déjà un compte : te voilà connecté.", "info");
            MK.aller("accueil");
          } else message(bandeau("urgent", "Ce numéro a déjà un compte", "Reviens à la connexion pour l'utiliser."));
        }, function (err) { message(bandeau("urgent", "Ce numéro a déjà un compte", err.message || "Reviens à la connexion pour l'utiliser.")); });
      }

      function retourNumero() {
        oublierSession();
        montrer("connexion");
      }

      /* ----- vue 3 : mise en route ----- */
      function vueRoute() {
        var pme = MK.etat.pme || {};
        boite.innerHTML =
          '<div class="con-tete"><div class="surtitre">Compte créé</div><h1 id="con-titre" tabindex="-1">Ton kiosque est prêt</h1><p class="con-sous">Trois étapes pour bien démarrer.</p></div>' +
          '<div class="con-moki"><span class="con-avatar"><img src="/ui/img/logo.svg" alt=""></span>' +
          '<div class="con-bulle"><b>Moki</b>Bonjour ! Moki ici' + (pme.nom_commerce ? ", prêt à travailler pour " + e(pme.nom_commerce) : "") + ". Je note tes ventes et tes dépenses, je prépare tes factures et je relance tes impayés. Rien ne part chez un client sans ton accord.</div></div>" +
          '<ol class="con-etapes">' + ETAPES.map(function (s, i) {
            return '<li class="con-etape"><span class="con-etape-ico">' + MK.icone(s.ico, { taille: 26 }) + '<span class="con-etape-n"><span class="sr-only">Étape </span>' + (i + 1) + '</span></span>' +
              '<span class="con-etape-corps"><span class="con-etape-titre">' + e(s.titre) + '</span><span class="con-etape-texte">' + e(s.texte) + "</span></span></li>";
          }).join("") + "</ol>" +
          '<button type="button" class="btn primaire plein" data-commencer>Commencer</button>';
        q("[data-commencer]").addEventListener("click", function () { MK.aller("accueil"); });
      }

      /* ----- session en attente d'inscription ----- */
      function oublierSession() {
        if (!etat.session || etat.finalisee) return;
        etat.session = null;
        MK.etat.token = null;
        MK.etat.numero = null;
        MK.etat.demo = false;
        window.removeEventListener("pagehide", oublierSession);
      }
      function garderPendant() { window.addEventListener("pagehide", oublierSession); }

      /* ----- changement de vue ----- */
      function montrer(vue) {
        etat.vue = vue;
        etat.occupe = false;
        boite.removeAttribute("data-occupe");
        boite.style.animation = "none";
        void boite.offsetWidth;
        boite.style.animation = "";
        if (vue === "creation") vueCreation(); else if (vue === "route") vueRoute(); else vueConnexion();
        document.title = (vue === "creation" ? "Création de compte" : vue === "route" ? "Bienvenue" : "Connexion") + " · Mon Kiosque";
        if (vue === "creation") focaliser("#con-nom");
        else if (vue === "route") focaliser("#con-titre");
        else if (premiereFois) {
          /* Le routeur reprend le focus après le rendu : on attend, et on évite d'ouvrir le clavier sur téléphone. */
          setTimeout(function () { if (window.matchMedia && window.matchMedia("(pointer: fine)").matches) focaliser("#con-numero"); }, 0);
        } else focaliser("#con-numero");
        premiereFois = false;
      }

      montrer("connexion");

      return function nettoyage() {
        window.removeEventListener("pagehide", oublierSession);
        oublierSession();
      };
    }
  });
})();
