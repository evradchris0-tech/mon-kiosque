/* Mon Kiosque : écran Réglages (hub). Route « reglages », onglet « reglages ». Contrat : docs/06-interface-pro.md §4. */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;
  var VERSION_APPLI = "2.0";

  var GROUPES = [
    { titre: "Mon commerce", liens: [
      { id: "chiffres", ico: "concurrence", lib: "Chiffres", sous: "Ventes, charges, bénéfice et trésorerie" },
      { id: "historique", ico: "historique", lib: "Historique", sous: "Toutes tes opérations, filtrées" },
      { id: "documents", ico: "modeles", lib: "Documents", sous: "Dossier de crédit, impôt et échéances" },
      { id: "connexions", ico: "connexions", lib: "Connexions", sous: "WhatsApp, Mobile Money, banque" }
    ] },
    { titre: "Application", liens: [
      { id: "parametres", ico: "parametres", lib: "Paramètres", sous: "Commerce, envois, sécurité, notifications" },
      { id: "aide", ico: "aide", lib: "Aide", sous: "Ce que Moki sait faire, questions fréquentes" }
    ] }
  ];

  /* « Chez Marie » → « CM » ; « Kiosque » → « KI » */
  function initiales(nom) {
    var mots = String(nom || "").trim().split(/\s+/).filter(Boolean);
    if (!mots.length) return "MK";
    if (mots.length === 1) return mots[0].slice(0, 2).toUpperCase();
    return (mots[0].charAt(0) + mots[1].charAt(0)).toUpperCase();
  }

  /* 237677000001 → « +237 6 77 00 00 01 » ; tout autre format est montré tel quel */
  function numeroLisible(n) {
    var s = String(n || "").replace(/[^\d]/g, "");
    if (/^237\d{9}$/.test(s)) return "+237 " + s.charAt(3) + " " + s.slice(4, 6) + " " + s.slice(6, 8) + " " + s.slice(8, 10) + " " + s.slice(10, 12);
    return s ? "+" + s : "";
  }

  function profil(c, demo) {
    var ligne2 = [c.nom_gerante, c.quartier && c.ville ? c.quartier + ", " + c.ville : c.ville].filter(Boolean).join(" · ");
    var tel = numeroLisible(c.numero);
    return '<div class="reg-avatar" aria-hidden="true">' + e(initiales(c.nom_commerce)) + "</div>" +
      '<div class="reg-profil-texte">' +
        '<h2 class="reg-nom">' + e(c.nom_commerce || "Mon commerce") + "</h2>" +
        (ligne2 ? '<p class="reg-detail">' + e(ligne2) + "</p>" : "") +
        (tel ? '<p class="reg-detail reg-tel">' + e(tel) + "</p>" : "") +
        (demo ? '<p class="reg-pastille">' + MK.pastille("Données fictives", "info") + "</p>" : "") +
      "</div>";
  }

  function lien(l) {
    return '<li><a class="ligne reg-lien" href="' + e(MK.lien(l.id)) + '">' +
      '<span class="ligne-ico">' + MK.icone(l.ico, { taille: 22 }) + "</span>" +
      '<span class="ligne-corps"><span class="ligne-titre">' + e(l.lib) + '</span><span class="ligne-sous">' + e(l.sous) + "</span></span>" +
      MK.icone("retour", { taille: 18, classe: "reg-fleche" }) + "</a></li>";
  }

  MK.ecran("reglages", {
    titre: "Réglages",
    onglet: "reglages",
    rendre: function (el) {
      var actif = true;
      var base = MK.etat.pme || {};
      var courant = { nom_commerce: base.nom_commerce, ville: base.ville, numero: MK.etat.numero };

      el.innerHTML =
        '<div class="entete-ecran"><div><h1>Réglages</h1><p class="sous">Ton commerce, tes documents et ton compte.</p></div></div>' +
        '<div class="reg-grille">' +
          '<section class="carte reg-profil" aria-label="Mon commerce" data-profil>' + profil(courant, MK.etat.demo) + "</section>" +
          '<div class="reg-colonne">' +
            GROUPES.map(function (g, i) {
              return '<section class="reg-groupe" aria-labelledby="reg-g' + i + '"><h2 class="reg-groupe-titre" id="reg-g' + i + '">' + e(g.titre) + "</h2>" +
                '<ul class="liste">' + g.liens.map(lien).join("") + "</ul></section>";
            }).join("") +
            '<div class="reg-pied">' +
              '<button type="button" class="btn secondaire plein reg-sortie" data-sortie>Se déconnecter</button>' +
              '<p class="reg-version">Mon Kiosque, version ' + e(VERSION_APPLI) + "</p>" +
            "</div>" +
          "</div>" +
        "</div>";

      el.querySelector("[data-sortie]").addEventListener("click", function () { MK.deconnecter(); });

      /* La carte profil s'enrichit (gérante, quartier, numéro) sans bloquer le hub : les liens restent utilisables si l'appel échoue. */
      MK.api("/api/parametres").then(function (r) {
        if (!actif || !r || !r.commerce) return;
        var carte = el.querySelector("[data-profil]");
        if (carte) carte.innerHTML = profil(r.commerce, !!(r.demo || MK.etat.demo));
      }, function () { /* le hub reste complet avec le nom déjà connu */ });

      return function () { actif = false; };
    }
  });
})();
