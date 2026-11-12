/* Mon Kiosque : écran Connexions (route « connexions »). Statuts honnêtes : simulé en démo, connecté, bientôt. */
(function () {
  "use strict";

  var e = MK.echapper;

  var STATUTS = {
    simule: { libelle: "Simulé en démo", type: "info", sens: "Les échanges sont simulés : rien n'est envoyé à de vraies personnes." },
    connecte: { libelle: "Connecté", type: "ok", sens: "La connexion est active." },
    bientot: { libelle: "Bientôt", type: "neutre", sens: "Pas encore disponible. Tu n'as rien à faire pour l'instant." }
  };

  function statutDe(c) {
    return STATUTS[c && c.statut] || { libelle: String((c && c.statut) || "Inconnu"), type: "neutre", sens: "" };
  }

  function carte(c) {
    var s = statutDe(c);
    var nom = e(c.nom || c.id || "Connexion");
    return '<li class="cnx-carte' + (c.statut === "bientot" ? " cnx-a-venir" : "") + '">' +
      '<article aria-labelledby="cnx-' + e(c.id) + '">' +
      '<div class="cnx-tete"><h2 id="cnx-' + e(c.id) + '">' + nom + "</h2>" + MK.pastille(s.libelle, s.type) + "</div>" +
      (c.detail ? '<p class="cnx-detail">' + e(c.detail) + "</p>" : "") +
      (s.sens ? '<div class="cnx-sens"><span>Ce que ça veut dire</span><strong>' + e(s.sens) + "</strong></div>" : "") +
      "</article></li>";
  }

  function bandeau(liste) {
    var simule = liste.some(function (c) { return c.statut === "simule"; });
    var connecte = liste.some(function (c) { return c.statut === "connecte"; });
    var texte;
    if (simule) texte = "Tu es en démonstration : WhatsApp est simulé et aucun message réel ne part vers de vrais clients.";
    else if (connecte) texte = "Les connexions marquées « Connecté » sont actives. Les autres arrivent plus tard.";
    else return "";
    return '<div class="bandeau info cnx-bandeau"><span class="bandeau-ico">' + MK.icone("connexions", { taille: 24 }) + "</span>" +
      '<div class="bandeau-corps"><div class="bandeau-titre">' + (simule ? "Mode démonstration" : "Connexions actives") + "</div>" +
      '<div class="bandeau-texte">' + e(texte) + "</div></div></div>";
  }

  function rendre(el) {
    el.innerHTML = '<div class="cnx-page">' +
      '<header class="entete-ecran"><div><h1>Connexions</h1>' +
      '<p class="sous">Ce à quoi Moki est relié, et ce qui reste à venir.</p></div></header>' +
      '<div class="cnx-corps" data-corps>' + MK.squelette(4) + "</div></div>";
    var corps = el.querySelector("[data-corps]");
    var actif = true;

    function charger() {
      corps.innerHTML = MK.squelette(4);
      return MK.api("/api/connexions").then(function (r) {
        if (!actif) return;
        var liste = (r && r.connexions) || [];
        if (!liste.length) {
          corps.innerHTML = MK.etatVide({ icone: "connexions", titre: "Aucune connexion à afficher", texte: "Les connexions de ton commerce apparaîtront ici." });
          return;
        }
        corps.innerHTML = bandeau(liste) +
          '<ul class="cnx-grille">' + liste.map(carte).join("") + "</ul>" +
          '<div class="cnx-aide"><p>Une question sur une connexion ?</p>' +
          '<a class="btn secondaire" href="' + e(MK.lien("aide")) + '">' + MK.icone("aide", { taille: 20 }) + "Ouvrir l'aide</a></div>";
      }, function (err) {
        if (!actif) return;
        corps.textContent = "";
        corps.appendChild(MK.etatErreur(err, charger));
      });
    }

    charger();
    return function () { actif = false; };
  }

  MK.ecran("connexions", { titre: "Connexions", onglet: "reglages", retour: "reglages", rendre: rendre });
})();
