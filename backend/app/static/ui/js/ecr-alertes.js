/* Mon Kiosque : écran Alertes (liste groupée par niveau, marquer comme lues). Contrat : docs/06-interface-pro.md §4 et §5. */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;

  var NIVEAUX = [
    { id: "urgent", titre: "Urgent", pastille: "urgent", pastilleTexte: "Urgent" },
    { id: "attention", titre: "À surveiller", pastille: "attention", pastilleTexte: "À surveiller" },
    { id: "info", titre: "Pour info", pastille: "neutre", pastilleTexte: "Pour info" }
  ];
  var LIBELLE_ACTION = {
    facture: "Voir la facture",
    client: "Voir le client",
    documents: "Ouvrir les documents",
    chiffres: "Voir les chiffres",
    historique: "Voir l'historique",
    suivi: "Ouvrir le suivi",
    accueil: "Ouvrir l'accueil",
    parametres: "Ouvrir les paramètres"
  };

  function pluriel(n, un, plusieurs) { return n + " " + (n > 1 ? plusieurs : un); }

  function dateAlerte(iso) {
    var rel = MK.fmt.relatif(iso);
    var h = MK.fmt.heure(iso);
    return (rel === "aujourd'hui" ? "Aujourd'hui" : rel.charAt(0).toUpperCase() + rel.slice(1)) + (h ? " · " + h : "");
  }

  function carte(a) {
    var niv = NIVEAUX.filter(function (n) { return n.id === a.niveau; })[0] || NIVEAUX[2];
    var act = a.action && a.action.ecran ? a.action : null;
    var corps =
      '<span class="alt-corps">' +
        '<span class="alt-haut">' + MK.pastille(niv.pastilleTexte, niv.pastille) +
          (a.lue ? "" : '<span class="alt-point" aria-hidden="true"></span><span class="sr-only">Non lue</span>') + "</span>" +
        '<span class="alt-titre">' + e(a.titre) + "</span>" +
        (a.texte ? '<span class="alt-texte">' + e(a.texte) + "</span>" : "") +
        '<span class="alt-bas"><span class="alt-date">' + e(dateAlerte(a.date)) + "</span>" +
          (act ? '<span class="alt-action">' + e(LIBELLE_ACTION[act.ecran] || "Ouvrir") + "</span>" : "") + "</span>" +
      "</span>";
    var cls = "alt " + niv.id + (a.lue ? " lue" : " non-lue");
    if (act) return '<li><a class="' + cls + '" href="' + e(MK.lien(act.ecran, act.params)) + '" data-alerte="' + e(a.id) + '">' + corps + "</a></li>";
    return '<li><div class="' + cls + ' statique" data-alerte="' + e(a.id) + '">' + corps + "</div></li>";
  }

  MK.ecran("alertes", {
    titre: "Alertes",
    onglet: "alertes",
    rendre: function (el) {
      var vivant = true;
      var donnees = null;
      var filtre = "toutes";
      var envoi = false;

      function nonLues() { return donnees.alertes.filter(function (a) { return !a.lue; }).length; }

      function entete() {
        var n = nonLues();
        var titre = n ? (n > 1 ? n + " alertes à lire" : "Une alerte à lire") : "Tout est à jour";
        var sous = n ? "Les plus urgentes sont en haut. Touche une alerte pour agir." : "Moki te prévient dès qu'il y a quelque chose à regarder.";
        return '<div class="entete-ecran"><div><div class="surtitre">Alertes · ' + e(MK.fmt.dateLongue(new Date().toISOString())) + "</div>" +
          '<h1 class="alt-h1">' + e(titre) + '</h1><p class="sous">' + e(sous) + "</p></div>" +
          '<div class="alt-outils">' +
            '<div class="segment" role="group" aria-label="Filtrer les alertes">' +
              '<button type="button" data-filtre="toutes" aria-pressed="' + (filtre === "toutes") + '">Toutes</button>' +
              '<button type="button" data-filtre="nonlues" aria-pressed="' + (filtre === "nonlues") + '">Non lues' + (n ? " (" + n + ")" : "") + "</button></div>" +
            '<button type="button" class="btn secondaire petit" data-tout-lire' + (n && !envoi ? "" : " disabled") + ">Tout marquer comme lu</button>" +
          "</div></div>";
      }

      function groupes() {
        var visibles = donnees.alertes.filter(function (a) { return filtre === "toutes" || !a.lue; });
        if (!visibles.length) {
          if (filtre === "nonlues" && donnees.alertes.length) return MK.etatVide({ titre: "Aucune alerte non lue", texte: "Tu as tout lu. Les anciennes alertes restent dans « Toutes ».", icone: "alertes" });
          return MK.etatVide({ titre: "Rien à signaler, tout est à jour", texte: "Moki te prévient ici dès qu'une facture est en retard, qu'une échéance approche ou qu'un client se fait attendre.", icone: "alertes" });
        }
        return NIVEAUX.map(function (niv) {
          var liste = visibles.filter(function (a) { return a.niveau === niv.id || (niv.id === "info" && ["urgent", "attention"].indexOf(a.niveau) < 0); });
          if (!liste.length) return "";
          liste.sort(function (x, y) { return String(y.date).localeCompare(String(x.date)); });
          var nl = liste.filter(function (a) { return !a.lue; }).length;
          return '<section class="alt-groupe" aria-labelledby="alt-g-' + niv.id + '">' +
            '<h2 class="alt-groupe-titre" id="alt-g-' + niv.id + '">' + e(niv.titre) + ' <span class="alt-compte">' + liste.length + "</span>" +
            (nl ? '<span class="alt-compte-nl">' + e(pluriel(nl, "non lue", "non lues")) + "</span>" : "") + "</h2>" +
            '<ul class="alt-liste">' + liste.map(carte).join("") + "</ul></section>";
        }).join("");
      }

      function pied() {
        return '<p class="alt-pied">Le résumé du soir et les rappels d\'échéance se règlent dans <a href="' + e(MK.lien("parametres")) + '">les paramètres</a>.</p>';
      }

      function dessiner() {
        el.innerHTML = '<div class="alt-page">' + entete() + '<div class="alt-groupes">' + groupes() + "</div>" + pied() + "</div>";
        Array.prototype.forEach.call(el.querySelectorAll("[data-filtre]"), function (b) {
          b.addEventListener("click", function () { filtre = b.getAttribute("data-filtre"); dessiner(); var f = el.querySelector('[data-filtre="' + filtre + '"]'); if (f) f.focus(); });
        });
        var tout = el.querySelector("[data-tout-lire]");
        if (tout) tout.addEventListener("click", toutLire);
      }

      function toutLire() {
        if (envoi || !donnees || !nonLues()) return;
        envoi = true;
        var b = el.querySelector("[data-tout-lire]");
        if (b) b.setAttribute("aria-busy", "true");
        MK.api("/api/alertes/lues", {}).then(function (r) {
          envoi = false;
          if (!vivant) { MK.etat.alertesNonLues = r && r.non_lues || 0; return; }
          donnees.alertes.forEach(function (a) { a.lue = true; });
          MK.etat.alertesNonLues = r && r.non_lues || 0;
          dessiner();
          var f = el.querySelector("[data-filtre]");
          if (f) f.focus();
          MK.toast("Toutes les alertes sont marquées comme lues.", "ok");
        }, function (err) {
          envoi = false;
          if (vivant) dessiner();
          MK.toast(err && err.message ? err.message : "Impossible de marquer les alertes comme lues.", "erreur");
        });
      }

      function charger() {
        el.innerHTML = '<div class="alt-page"><div class="entete-ecran"><div><div class="surtitre">Alertes</div><h1 class="alt-h1">Tes alertes</h1></div></div>' + MK.squelette(4) + "</div>";
        return MK.api("/api/alertes").then(function (r) {
          if (!vivant) return;
          donnees = { alertes: (r && r.alertes) || [] };
          MK.etat.alertesNonLues = r && typeof r.non_lues === "number" ? r.non_lues : nonLues();
          dessiner();
        }, function (err) {
          if (!vivant) return;
          el.innerHTML = '<div class="alt-page"><div class="entete-ecran"><div><div class="surtitre">Alertes</div><h1 class="alt-h1">Tes alertes</h1></div></div></div>';
          el.firstChild.appendChild(MK.etatErreur(err, charger));
        });
      }

      charger();
      return function () { vivant = false; };
    }
  });
})();
