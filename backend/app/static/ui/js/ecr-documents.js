/* Mon Kiosque : écran Documents (dossier de crédit, impôt IGS estimé, échéances fiscales). Route « documents », retour « reglages ». */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;
  var SEUIL_ATTENTION = 15;
  var SEUIL_URGENT = 3;

  function mois(n) { return n + " mois"; }

  /* Contrat : le taux est une fraction (0,02 = 2 %). */
  function tauxLisible(t) {
    var p = Math.round((Number(t) || 0) * 10000) / 100;
    return String(p).replace(".", ",") + " %";
  }

  function delai(jours) {
    if (jours < 0) return "date dépassée";
    if (jours === 0) return "aujourd'hui";
    if (jours === 1) return "demain";
    return "dans " + MK.fmt.jours(jours);
  }

  function pastilleEcheance(jours) {
    if (jours <= SEUIL_URGENT) return MK.pastille("Urgent", "urgent");
    if (jours <= SEUIL_ATTENTION) return MK.pastille("À préparer", "attention");
    return "";
  }

  /* ---------- carte Dossier de crédit ---------- */
  function carteDossier(d) {
    var requis = Math.max(1, Number(d.requis) || 6);
    var hist = Math.max(0, Math.min(requis, Number(d.historique_mois) || 0));
    var manque = Math.max(0, Number(d.manque_mois) || 0);
    var segments = "";
    for (var i = 0; i < requis; i++) segments += '<span class="doc-seg' + (i < hist ? " plein" : "") + '"></span>';
    return '<section class="carte doc-carte doc-dossier" aria-labelledby="doc-t-dossier">' +
      '<div class="doc-tete"><h2 class="carte-titre" id="doc-t-dossier">' + MK.icone("modeles", { taille: 22 }) + "Dossier de crédit</h2>" +
        (d.pret ? MK.pastille("Prêt", "ok") : MK.pastille("En cours", "attention")) + "</div>" +
      '<p class="doc-progres"><span class="doc-nombre">' + hist + '</span><span class="doc-sur">mois sur ' + requis + "</span></p>" +
      '<div class="doc-barre" role="progressbar" aria-label="Historique disponible pour le dossier de crédit" aria-valuemin="0" aria-valuemax="' + requis +
        '" aria-valuenow="' + hist + '" aria-valuetext="' + hist + " mois sur " + requis + '">' + segments + "</div>" +
      '<p class="doc-statut ' + (d.pret ? "ok" : "") + '">' + (d.pret ? "Ton historique est suffisant" : "Il manque " + mois(manque)) + "</p>" +
      '<p class="doc-texte">' + (d.pret
        ? "Ton dossier peut être généré avec six mois de ventes et de dépenses."
        : "Tu peux générer le dossier dès maintenant : il indiquera ce qu'il manque. Plus tu notes régulièrement, plus il est complet.") + "</p>" +
      '<ul class="doc-mentions"><li>Calculé uniquement à partir de tes saisies.</li>' +
        (d.fictives ? '<li>' + MK.pastille("Données fictives de démonstration", "info") + "</li>" : "") + "</ul>" +
      '<button type="button" class="btn primaire plein" data-generer>Générer mon dossier de crédit (PDF)</button>' +
      '<div class="doc-zone" data-zone aria-live="polite"></div>' +
    "</section>";
  }

  /* ---------- carte Impôt ---------- */
  function carteImpot(i) {
    return '<section class="carte doc-carte doc-impot" aria-labelledby="doc-t-impot">' +
      '<div class="doc-tete"><h2 class="carte-titre" id="doc-t-impot">Impôt (IGS)</h2>' + MK.pastille("Estimation", "neutre") + "</div>" +
      '<p class="doc-etiquette">Estimation de ton impôt</p>' +
      '<p class="doc-grand montant">' + e(MK.fmt.fcfa(i.estimation)) + "</p>" +
      (i.ca_annuel > 0 ? "" : '<p class="doc-texte">Dès que tu notes des ventes, l\'estimation se calcule toute seule.</p>') +
      '<dl class="doc-dl">' +
        '<div><dt>Chiffre d\'affaires annuel estimé</dt><dd class="montant">' + e(MK.fmt.fcfa(i.ca_annuel)) + "</dd></div>" +
        '<div><dt>Taux appliqué</dt><dd class="montant">' + e(tauxLisible(i.taux)) + "</dd></div>" +
      "</dl>" +
      '<div class="bandeau attention doc-note" role="note"><div class="bandeau-corps"><div class="bandeau-titre">' + e(i.note || "Estimation indicative à confirmer avec la DGI") + "</div></div></div>" +
    "</section>";
  }

  /* ---------- carte Échéances ---------- */
  function carteEcheances(liste) {
    var corps;
    if (!liste.length) {
      corps = MK.etatVide({ titre: "Aucune échéance à venir", texte: "Tes prochaines dates fiscales apparaîtront ici." });
    } else {
      corps = '<ul class="liste doc-echeances">' + liste.map(function (x) {
        var j = Number(x.jours) || 0;
        var classe = j <= SEUIL_URGENT ? " urgent" : j <= SEUIL_ATTENTION ? " attention" : "";
        return '<li class="ligne doc-echeance' + classe + '">' +
          '<span class="ligne-ico">' + MK.icone("reservation", { taille: 22 }) + "</span>" +
          '<span class="ligne-corps"><span class="ligne-titre">' + e(x.libelle) + '</span><span class="ligne-sous">' + e(MK.fmt.dateLongue(x.date)) + "</span></span>" +
          '<span class="ligne-fin"><span>' + e(delai(j)) + "</span>" + pastilleEcheance(j) + "</span></li>";
      }).join("") + "</ul>";
    }
    return '<section class="carte doc-carte doc-echeances-carte" aria-labelledby="doc-t-ech">' +
      '<h2 class="carte-titre" id="doc-t-ech">Échéances fiscales</h2>' + corps +
      '<p class="doc-texte doc-explic">Je te préviens 15 jours puis 3 jours avant chaque échéance.</p>' +
    "</section>";
  }

  /* Un PDF « data: » (mode mock) ne s'ouvre pas en navigation directe : on passe par un objet Blob. */
  function adresseOuvrable(url) {
    if (!/^data:/i.test(url)) return Promise.resolve({ href: url, blob: false });
    return fetch(url).then(function (r) { return r.blob(); }).then(function (b) { return { href: URL.createObjectURL(b), blob: true }; });
  }

  function brancherGeneration(el, suivre) {
    var bouton = el.querySelector("[data-generer]");
    var zone = el.querySelector("[data-zone]");
    if (!bouton || !zone) return;

    function erreur(err) {
      zone.innerHTML = '<div class="bandeau urgent" role="alert"><div class="bandeau-corps">' +
        '<div class="bandeau-titre">Le dossier n\'a pas pu être généré</div>' +
        '<div class="bandeau-texte">' + e((err && err.message) || "Réessaie dans un instant.") + "</div>" +
        '<div class="bandeau-actions"><button type="button" class="btn secondaire petit" data-reessayer>Réessayer</button></div></div></div>';
      zone.querySelector("[data-reessayer]").addEventListener("click", generer);
    }

    function succes(info, nom) {
      zone.innerHTML = '<div class="bandeau ok" role="status"><div class="bandeau-corps">' +
        '<div class="bandeau-titre">Ton dossier est prêt</div>' +
        '<div class="bandeau-texte">' + e(nom || "dossier-de-credit.pdf") + "</div>" +
        '<div class="bandeau-actions"><a class="btn secondaire petit" target="_blank" rel="noopener" data-pdf>Ouvrir le PDF</a></div></div></div>';
      var a = zone.querySelector("[data-pdf]");
      a.setAttribute("href", info.href);
    }

    function generer() {
      if (bouton.getAttribute("aria-busy") === "true") return;
      bouton.setAttribute("aria-busy", "true");
      bouton.setAttribute("aria-label", "Génération du dossier en cours");
      zone.textContent = "";
      MK.api("/api/dossier").then(function (r) {
        if (!r || !r.url) throw new Error("Le serveur n'a pas renvoyé de fichier.");
        return adresseOuvrable(r.url).then(function (info) {
          if (info.blob) suivre(info.href);
          succes(info, r.nom);
          var w = window.open(info.href, "_blank");
          if (w) { try { w.opener = null; } catch (x) { /* fenêtre déjà isolée */ } }
        });
      }).then(null, erreur).then(function () {
        bouton.removeAttribute("aria-busy");
        bouton.removeAttribute("aria-label");
      });
    }
    bouton.addEventListener("click", generer);
  }

  MK.ecran("documents", {
    titre: "Documents",
    onglet: "reglages",
    retour: "reglages",
    rendre: function (el) {
      var urlsBlob = [];
      el.innerHTML = '<div class="entete-ecran"><div><h1>Documents</h1><p class="sous">Ton dossier de crédit, ton impôt estimé et tes échéances fiscales.</p></div></div>' +
        '<div aria-busy="true">' + MK.squelette(4) + "</div>";

      return MK.api("/api/documents").then(function (r) {
        el.innerHTML = '<div class="entete-ecran"><div><h1>Documents</h1><p class="sous">Ton dossier de crédit, ton impôt estimé et tes échéances fiscales.</p></div></div>' +
          '<div class="doc-grille">' +
            carteDossier(r.dossier || {}) + carteImpot(r.impot || {}) + carteEcheances(r.echeances || []) +
          "</div>";
        brancherGeneration(el, function (href) { urlsBlob.push(href); });
        return function () { urlsBlob.forEach(function (u) { URL.revokeObjectURL(u); }); };
      });
    }
  });
})();
