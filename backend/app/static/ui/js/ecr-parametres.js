/* Mon Kiosque : écran Paramètres (commerce, envois aux clients, sécurité, notifications). Route « parametres », retour « reglages ». */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;
  var SEUIL_MIN = 1000;
  var SEUIL_MAX = 10000000;

  var CHAMPS = [
    { cle: "nom_commerce", lib: "Nom du commerce", max: 120, requis: true },
    { cle: "nom_gerante", lib: "Ton nom", max: 120, aide: "Le nom de la gérante : Moki s'en sert pour te saluer." },
    { cle: "ville", lib: "Ville", max: 60, requis: true },
    { cle: "quartier", lib: "Quartier", max: 60 },
    { cle: "secteur", lib: "Secteur d'activité", max: 40, aide: "Par exemple : restauration, couture, vente de téléphones." }
  ];

  var MODES = [
    { valeur: "transfert", titre: "Moki rédige, je transfère", texte: "Moki prépare le message et la facture. C'est toi qui les transfères à ton client depuis ton WhatsApp." },
    { valeur: "direct", titre: "Moki envoie après mon OUI", texte: "Moki envoie le message à ton client dès que tu réponds OUI. Rien ne part sans ton accord." }
  ];

  var NOTIFS = [
    { cle: "resume_du_soir", lib: "Résumé de 19 h", aide: "Chaque soir à 19 h, Moki t'envoie le bilan de ta journée." },
    { cle: "rappels_fiscaux", lib: "Rappels fiscaux", aide: "Moki te prévient 15 jours puis 3 jours avant chaque échéance." }
  ];

  /* Le serveur renvoie une seule phrase d'erreur : on retrouve le champ concerné à ses mots. */
  var CIBLES = [
    [/nom du commerce|nom commerce/i, "nom_commerce"],
    [/ton nom|nom g[ée]rante/i, "nom_gerante"],
    [/ville/i, "ville"],
    [/quartier/i, "quartier"],
    [/secteur/i, "secteur"],
    [/mode d'envoi|mode relance/i, "mode_relance"],
    [/seuil/i, "seuil"]
  ];
  function cibleErreur(message) {
    for (var i = 0; i < CIBLES.length; i++) if (CIBLES[i][0].test(message)) return CIBLES[i][1];
    return null;
  }

  function sansEspaces(t) { return String(t === null || t === undefined ? "" : t).replace(/\s/g, ""); }
  function texte(v) { return v === null || v === undefined ? "" : String(v).trim(); }

  function fichePage(d) {
    var c = d.commerce || {};
    var p = d.preferences || {};
    return {
      commerce: { nom_commerce: texte(c.nom_commerce), nom_gerante: texte(c.nom_gerante), ville: texte(c.ville), quartier: texte(c.quartier), secteur: texte(c.secteur) },
      numero: c.numero,
      mode: p.mode_relance === "direct" ? "direct" : "transfert",
      seuil: MK.fmt.nombre(p.seuil_confirmation_renforcee),
      resume_du_soir: !!p.resume_du_soir,
      rappels_fiscaux: !!p.rappels_fiscaux
    };
  }
  function copie(o) { return JSON.parse(JSON.stringify(o)); }

  function numeroLisible(n) {
    var s = String(n || "").replace(/[^\d]/g, "");
    if (/^237\d{9}$/.test(s)) return "+237 " + s.charAt(3) + " " + s.slice(4, 6) + " " + s.slice(6, 8) + " " + s.slice(8, 10) + " " + s.slice(10, 12);
    return s ? "+" + s : "";
  }

  /* ---------- gabarits ---------- */
  function champTexte(c, valeur) {
    var aide = c.aide ? '<p class="champ-aide" id="par-aide-' + c.cle + '">' + e(c.aide) + "</p>" : "";
    return '<div class="champ" data-champ="' + c.cle + '">' +
      '<label for="par-' + c.cle + '">' + e(c.lib) + (c.requis ? ' <span class="par-oblig">(obligatoire)</span>' : "") + "</label>" +
      '<input type="text" id="par-' + c.cle + '" name="' + c.cle + '" value="' + e(valeur) + '" autocomplete="off"' + (c.requis ? ' aria-required="true"' : "") +
        ' aria-describedby="' + (c.aide ? "par-aide-" + c.cle + " " : "") + 'par-err-' + c.cle + '">' +
      aide + '<p class="champ-erreur" id="par-err-' + c.cle + '" hidden></p></div>';
  }

  function sectionCommerce(f) {
    return '<section class="carte par-carte par-commerce" aria-labelledby="par-t-commerce">' +
      '<h2 class="carte-titre" id="par-t-commerce">Commerce</h2>' +
      '<div class="par-champs">' +
        CHAMPS.map(function (c) { return champTexte(c, f.commerce[c.cle]); }).join("") +
        '<div class="champ">' +
          '<label for="par-numero">Numéro WhatsApp</label>' +
          '<input type="text" id="par-numero" class="par-lecture" value="' + e(numeroLisible(f.numero)) + '" readonly aria-readonly="true" aria-describedby="par-aide-numero">' +
          '<p class="champ-aide" id="par-aide-numero">C\'est ce numéro qui te connecte à Moki. Il ne peut pas être modifié ici.</p>' +
        "</div>" +
      "</div></section>";
  }

  function sectionEnvois(f) {
    return '<section class="carte par-carte par-envois" aria-labelledby="par-t-envois">' +
      '<h2 class="carte-titre" id="par-t-envois">Envois aux clients</h2>' +
      '<p class="par-intro">Choisis comment tes factures et tes relances arrivent chez ton client.</p>' +
      '<fieldset class="par-radios" aria-describedby="par-err-mode_relance"><legend class="sr-only">Mode d\'envoi aux clients</legend>' +
        MODES.map(function (m) {
          return '<label class="par-radio"><input type="radio" name="mode_relance" value="' + m.valeur + '"' + (f.mode === m.valeur ? " checked" : "") + ">" +
            '<span class="par-radio-corps"><span class="par-radio-point" aria-hidden="true"></span>' +
            '<span class="par-radio-texte"><span class="par-radio-titre">' + e(m.titre) + '</span><span class="par-radio-aide">' + e(m.texte) + "</span></span></span></label>";
        }).join("") +
      '</fieldset><p class="champ-erreur" id="par-err-mode_relance" hidden></p></section>';
  }

  function sectionSecurite(f) {
    return '<section class="carte par-carte par-securite" aria-labelledby="par-t-secu">' +
      '<h2 class="carte-titre" id="par-t-secu">Sécurité</h2>' +
      '<div class="champ" data-champ="seuil">' +
        '<label for="par-seuil">Seuil de confirmation renforcée</label>' +
        '<div class="par-suffixe"><input type="text" id="par-seuil" name="seuil" inputmode="numeric" value="' + e(f.seuil) + '" autocomplete="off" aria-describedby="par-aide-seuil par-err-seuil"><span class="par-unite" aria-hidden="true">F</span></div>' +
        '<p class="champ-aide" id="par-aide-seuil">Au-dessus de ce montant, un simple OUI ne suffit plus : Moki te demande de recopier un mot de confirmation. Entre ' + e(MK.fmt.fcfa(SEUIL_MIN)) + " et " + e(MK.fmt.fcfa(SEUIL_MAX)) + ".</p>" +
        '<p class="champ-erreur" id="par-err-seuil" hidden></p>' +
      "</div></section>";
  }

  function sectionNotifs(f) {
    return '<section class="carte par-carte par-notifs" aria-labelledby="par-t-notifs">' +
      '<h2 class="carte-titre" id="par-t-notifs">Notifications</h2>' +
      NOTIFS.map(function (n) {
        return '<div class="par-ligne"><div class="par-ligne-texte"><label id="par-l-' + n.cle + '" for="par-sw-' + n.cle + '">' + e(n.lib) + "</label>" +
          '<p class="champ-aide" id="par-a-' + n.cle + '">' + e(n.aide) + "</p></div>" +
          '<button type="button" role="switch" class="interrupteur" id="par-sw-' + n.cle + '" data-pref="' + n.cle + '" aria-checked="' + (f[n.cle] ? "true" : "false") +
          '" aria-labelledby="par-l-' + n.cle + '" aria-describedby="par-a-' + n.cle + '"></button></div>';
      }).join("") + "</section>";
  }

  MK.ecran("parametres", {
    titre: "Paramètres",
    onglet: "reglages",
    retour: "reglages",
    rendre: function (el) {
      el.innerHTML = '<div class="entete-ecran"><div><h1>Paramètres</h1><p class="sous">Les règles de ton commerce. Tu peux les changer à tout moment.</p></div></div>' + MK.squelette(5);

      return MK.api("/api/parametres").then(function (donnees) {
        var base = fichePage(donnees);
        var cur = copie(base);
        var enCours = false;
        var quitte = false;

        el.innerHTML =
          '<div class="entete-ecran"><div><h1>Paramètres</h1><p class="sous">Les règles de ton commerce. Tu peux les changer à tout moment.</p></div>' +
            (donnees.demo ? "<div>" + MK.pastille("Données fictives", "info") + "</div>" : "") + "</div>" +
          '<form class="par-form" novalidate>' +
            '<div class="bandeau urgent par-global" role="alert" hidden><div class="bandeau-corps"><div class="bandeau-titre">Les changements n\'ont pas été enregistrés</div><div class="bandeau-texte" data-global-texte></div></div></div>' +
            '<div class="par-grille">' + sectionCommerce(base) + sectionEnvois(base) + sectionSecurite(base) + sectionNotifs(base) + "</div>" +
            '<div class="par-barre"><p class="par-statut" data-statut role="status"></p>' +
              '<div class="par-actions"><button type="button" class="btn discret" data-annuler>Annuler</button>' +
              '<button type="submit" class="btn primaire" data-enregistrer>Enregistrer</button></div></div>' +
          "</form>";

        var form = el.querySelector("form");
        var global = el.querySelector(".par-global");
        var bEnreg = el.querySelector("[data-enregistrer]");
        var bAnnuler = el.querySelector("[data-annuler]");
        var statut = el.querySelector("[data-statut]");

        function champ(cle) { return form.querySelector('[data-champ="' + cle + '"]'); }

        /* ----- état modifié ----- */
        function diff() {
          var com = {}, pref = {}, n = 0;
          CHAMPS.forEach(function (c) {
            if (texte(cur.commerce[c.cle]) !== base.commerce[c.cle]) { com[c.cle] = texte(cur.commerce[c.cle]); n++; }
          });
          if (cur.mode !== base.mode) { pref.mode_relance = cur.mode; n++; }
          if (sansEspaces(cur.seuil) !== sansEspaces(base.seuil)) {
            pref.seuil_confirmation_renforcee = /^\d+$/.test(sansEspaces(cur.seuil)) ? parseInt(sansEspaces(cur.seuil), 10) : cur.seuil;
            n++;
          }
          NOTIFS.forEach(function (x) { if (cur[x.cle] !== base[x.cle]) { pref[x.cle] = cur[x.cle]; n++; } });
          return n ? { corps: { commerce: com, preferences: pref }, nb: n } : null;
        }
        function modifie() { return !!diff(); }

        function majBarre() {
          var d = diff();
          bEnreg.disabled = !d || enCours;
          bAnnuler.disabled = !d || enCours;
          statut.textContent = d ? (d.nb > 1 ? d.nb + " changements non enregistrés" : "1 changement non enregistré") : "Tout est enregistré";
          statut.classList.toggle("modifie", !!d);
        }

        /* ----- erreurs ----- */
        function poserErreur(cle, message) {
          var p = form.querySelector("#par-err-" + cle);
          var zone = champ(cle);
          var input = form.querySelector("#par-" + cle);
          if (p) { p.textContent = message || ""; p.hidden = !message; }
          if (zone) zone.classList.toggle("erreur", !!message);
          if (input) { if (message) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid"); }
        }
        function validerChamp(cle) {
          var msg = "", v;
          if (cle === "seuil") {
            v = sansEspaces(cur.seuil);
            if (!/^\d+$/.test(v)) msg = "Écris un nombre entier de francs, par exemple 100 000.";
            else if (parseInt(v, 10) < SEUIL_MIN || parseInt(v, 10) > SEUIL_MAX) msg = "Le seuil doit être compris entre " + MK.fmt.fcfa(SEUIL_MIN) + " et " + MK.fmt.fcfa(SEUIL_MAX) + ".";
          } else {
            var c = CHAMPS.filter(function (x) { return x.cle === cle; })[0];
            v = texte(cur.commerce[cle]);
            if (c.requis && !v) msg = (cle === "ville" ? "La ville" : "Le nom du commerce") + " ne peut pas être vide.";
            else if (v.length > c.max) msg = c.lib + " est trop long (" + c.max + " caractères au maximum).";
          }
          poserErreur(cle, msg);
          return msg;
        }
        function validerTout() {
          var premier = null;
          CHAMPS.map(function (c) { return c.cle; }).concat(["seuil"]).forEach(function (cle) {
            if (validerChamp(cle) && !premier) premier = cle;
          });
          return premier;
        }
        function effacerErreurs() {
          CHAMPS.map(function (c) { return c.cle; }).concat(["seuil", "mode_relance"]).forEach(function (cle) { poserErreur(cle, ""); });
          global.hidden = true;
        }
        function erreurGlobale(message) {
          global.querySelector("[data-global-texte]").textContent = message;
          global.hidden = false;
          global.scrollIntoView({ block: "nearest" });
        }

        /* ----- champs ----- */
        form.addEventListener("input", function (ev) {
          var t = ev.target;
          if (t.name === "seuil") { cur.seuil = t.value; if (champ("seuil").classList.contains("erreur")) validerChamp("seuil"); }
          else if (CHAMPS.some(function (c) { return c.cle === t.name; })) {
            cur.commerce[t.name] = t.value;
            if (champ(t.name).classList.contains("erreur")) validerChamp(t.name);
          }
          majBarre();
        });
        form.addEventListener("focusout", function (ev) {
          var t = ev.target;
          if (t.name === "seuil") {
            if (!validerChamp("seuil")) { cur.seuil = MK.fmt.nombre(parseInt(sansEspaces(cur.seuil), 10)); t.value = cur.seuil; majBarre(); }
          } else if (CHAMPS.some(function (c) { return c.cle === t.name; })) validerChamp(t.name);
        });
        form.addEventListener("change", function (ev) {
          if (ev.target.name === "mode_relance") { cur.mode = ev.target.value; poserErreur("mode_relance", ""); majBarre(); }
        });
        form.querySelectorAll("[data-pref]").forEach(function (b) {
          b.addEventListener("click", function () {
            var cle = b.getAttribute("data-pref");
            cur[cle] = !cur[cle];
            b.setAttribute("aria-checked", cur[cle] ? "true" : "false");
            majBarre();
          });
        });

        function afficher(f) {
          CHAMPS.forEach(function (c) { form.querySelector("#par-" + c.cle).value = f.commerce[c.cle]; });
          form.querySelector("#par-seuil").value = f.seuil;
          form.querySelectorAll('input[name="mode_relance"]').forEach(function (r) { r.checked = r.value === f.mode; });
          NOTIFS.forEach(function (x) { form.querySelector('[data-pref="' + x.cle + '"]').setAttribute("aria-checked", f[x.cle] ? "true" : "false"); });
        }

        bAnnuler.addEventListener("click", function () {
          cur = copie(base);
          afficher(cur);
          effacerErreurs();
          majBarre();
        });

        /* ----- enregistrement ----- */
        function enregistrer() {
          if (enCours) return Promise.resolve(false);
          var premier = validerTout();
          if (premier) {
            var cible = form.querySelector("#par-" + premier);
            if (cible) cible.focus();
            MK.toast("Corrige les champs signalés.", "erreur");
            return Promise.resolve(false);
          }
          var d = diff();
          if (!d) return Promise.resolve(true);
          global.hidden = true;
          enCours = true;
          bEnreg.setAttribute("aria-busy", "true");
          majBarre();
          return MK.api("/api/parametres", d.corps, "PUT").then(function (r) {
            base = fichePage(r);
            cur = copie(base);
            afficher(cur);
            effacerErreurs();
            if (r.commerce && r.commerce.nom_commerce) MK.etat.pme = { nom_commerce: r.commerce.nom_commerce, ville: r.commerce.ville || null };
            MK.toast("Réglages enregistrés.", "ok");
            return true;
          }, function (err) {
            var message = (err && err.message) || "Réessaie dans un instant.";
            var cle = err && err.status === 422 ? cibleErreur(message) : null;
            if (cle) {
              poserErreur(cle, message);
              var cc = form.querySelector("#par-" + cle) || form.querySelector('input[name="' + cle + '"]');
              if (cc) cc.focus();
              MK.toast("Corrige le champ signalé.", "erreur");
            } else {
              erreurGlobale(message);
              MK.toast("Enregistrement impossible.", "erreur");
            }
            return false;
          }).then(function (ok) {
            enCours = false;
            bEnreg.removeAttribute("aria-busy");
            majBarre();
            return ok;
          });
        }
        form.addEventListener("submit", function (ev) { ev.preventDefault(); enregistrer(); });

        /* ----- quitter avec des changements non enregistrés ----- */
        function demanderSortie(suite) {
          MK.feuille({
            titre: "Quitter sans enregistrer ?",
            contenu: '<p class="par-sortie-texte">Tu as des changements qui ne sont pas enregistrés. Si tu pars maintenant, ils seront perdus.</p>',
            actions: [
              { libelle: "Rester ici" },
              { libelle: "Quitter sans enregistrer", onclick: function () { quitte = true; suite(); } },
              { libelle: "Enregistrer et quitter", primaire: true, onclick: function () { return enregistrer().then(function (ok) { if (ok) { quitte = true; suite(); } }); } }
            ]
          });
        }
        function garde(ev) {
          if (quitte || ev.defaultPrevented || ev.button > 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || !modifie()) return;
          var a = ev.target.closest ? ev.target.closest('a[href^="#/"], #btn-retour') : null;
          if (!a) return;
          var retour = a.id === "btn-retour";
          var href = retour ? "" : a.getAttribute("href");
          if (href === "#/parametres") return;
          ev.preventDefault();
          ev.stopImmediatePropagation();
          demanderSortie(function () { if (retour) MK.aller("reglages"); else location.hash = href; });
        }
        function avantFermeture(ev) {
          if (!modifie()) return;
          ev.preventDefault();
          ev.returnValue = "";
        }
        document.addEventListener("click", garde, true);
        window.addEventListener("beforeunload", avantFermeture);

        majBarre();

        return function () {
          document.removeEventListener("click", garde, true);
          window.removeEventListener("beforeunload", avantFermeture);
          if (!quitte && modifie()) MK.toast("Changements non enregistrés : abandonnés.", "info");
        };
      });
    }
  });
})();
