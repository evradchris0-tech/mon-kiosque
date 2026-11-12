/* Mon Kiosque : fiche client (route « client », paramètre id). Données : GET /api/clients/{id}. */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;
  var NBSP = " ";

  var STATUTS_FACTURE = {
    payee: { libelle: "Payée", type: "ok" },
    envoyee: { libelle: "Envoyée", type: "info" },
    en_retard: { libelle: "En retard", type: "urgent" }
  };
  var STATUTS_ELEMENT = {
    annule: { libelle: "Annulé", type: "neutre" },
    en_attente: { libelle: "À encaisser", type: "attention" },
    retard: { libelle: "En retard", type: "urgent" }
  };

  /* 237677120045 -> +237 677 12 00 45 ; autre forme : telle quelle */
  function telephone(num) {
    var n = String(num || "").replace(/\D/g, "");
    if (/^237\d{9}$/.test(n)) return "+237" + NBSP + n.slice(3, 6) + NBSP + n.slice(6, 8) + NBSP + n.slice(8, 10) + NBSP + n.slice(10);
    return String(num || "");
  }

  function etatIntrouvable(el) {
    el.innerHTML = '<div class="vide page">' +
      '<div class="vide-ico">' + MK.icone("recherche", { taille: 26 }) + "</div>" +
      "<h1>Client introuvable</h1>" +
      "<p>Ce client n'existe pas ou plus. Ses ventes et ses factures restent dans ton historique.</p>" +
      '<div class="rangee"><a class="btn primaire" href="#/suivi">Retour au suivi</a></div></div>';
  }

  /* ---------- éléments d'historique : date, titre, montant signé ---------- */
  function montantSigne(x) {
    var m = MK.fmt.fcfa(x.montant);
    if (x.sens === "entree") return { texte: "+" + m, classe: " positif" };
    if (x.sens === "sortie") return { texte: "−" + m, classe: " negatif" };
    return { texte: m, classe: "" };
  }

  function liste(elements) {
    return '<ul class="liste cli-liste">' + elements.map(function (x) {
      var d = MK.fmt.date(x.date).split(" ");
      var m = montantSigne(x);
      var st = STATUTS_ELEMENT[x.statut];
      var annule = x.statut === "annule";
      return '<li class="ligne double' + (annule ? " cli-annule" : "") + '">' +
        '<span class="cli-date" aria-hidden="true"><b>' + e(d[0]) + "</b><span>" + e(d.slice(1).join(" ")) + "</span></span>" +
        '<div class="ligne-corps"><span class="ligne-titre">' + e(x.titre) + "</span>" +
        '<span class="ligne-sous"><span class="sr-only">' + e(MK.fmt.dateLongue(x.date)) + ". </span>" + e(x.detail || "") + "</span></div>" +
        '<div class="ligne-fin' + (annule ? "" : m.classe) + '"><span class="montant">' + e(m.texte) + "</span>" + (st ? MK.pastille(st.libelle, st.type) : "") + "</div></li>";
    }).join("") + "</ul>";
  }

  function listeFactures(factures) {
    return '<ul class="liste cli-liste">' + factures.map(function (f) {
      var st = STATUTS_FACTURE[f.statut] || { libelle: f.statut, type: "neutre" };
      return '<li><a class="ligne" href="' + e(MK.lien("facture", { id: f.id })) + '">' +
        '<div class="ligne-corps"><span class="ligne-titre">Facture n°' + NBSP + e(f.numero) + '</span><span class="ligne-sous">Voir le détail et les relances</span></div>' +
        '<div class="ligne-fin"><span class="montant">' + e(MK.fmt.fcfa(f.total)) + "</span>" + MK.pastille(st.libelle, st.type) + "</div></a></li>";
    }).join("") + "</ul>";
  }

  function section(id, titre, nb, corps, vide, classe) {
    return '<section class="cli-section ' + classe + '" aria-labelledby="' + id + '">' +
      '<h2 class="cli-titre" id="' + id + '">' + e(titre) + (nb ? '<span class="cli-nb">' + nb + "</span>" : "") + "</h2>" +
      (nb ? corps : '<div class="cli-vide">' + e(vide) + "</div>") + "</section>";
  }

  /* ---------- écran ---------- */
  function entete(c, dette) {
    var actions = "";
    if (dette > 0) actions += '<button type="button" class="btn primaire" data-relancer>Relancer</button>';
    actions += '<button type="button" class="btn ' + (dette > 0 ? "secondaire" : "primaire") + '" data-facture>Nouvelle facture</button>';
    var infos = [];
    if (c.quartier) infos.push("<span>" + e(c.quartier) + "</span>");
    if (c.telephone) infos.push('<a class="cli-tel" href="tel:+' + e(String(c.telephone).replace(/\D/g, "")) + '">' + e(telephone(c.telephone)) + "</a>");
    if (!infos.length) infos.push("<span>Pas de quartier ni de téléphone enregistrés</span>");
    return '<header class="carte cli-tete"><div class="cli-tete-g">' +
      '<div class="surtitre">Client</div>' +
      '<div class="cli-nom"><h1>' + e(c.nom) + "</h1>" + (c.inactif ? MK.pastille("Inactif", "neutre") : "") + "</div>" +
      '<div class="cli-infos">' + infos.join('<span class="cli-point" aria-hidden="true"></span>') + "</div></div>" +
      '<div class="cli-actions">' + actions + "</div></header>";
  }

  function chiffres(c, dette) {
    var dernier = c.dernier_achat
      ? "Dernier achat " + MK.fmt.relatif(c.dernier_achat) + " (" + MK.fmt.date(c.dernier_achat) + ")" + (c.inactif ? " : ce client est inactif." : ".")
      : "Aucun achat enregistré pour l'instant.";
    return '<section class="cli-chiffres" aria-label="Chiffres du client">' +
      '<div class="kpi cli-dette' + (dette > 0 ? " du" : "") + '"><span class="kpi-libelle">Il te doit</span><span class="kpi-valeur">' + e(MK.fmt.fcfa(dette)) + '</span><span class="kpi-note">' + (dette > 0 ? "À récupérer" : "Rien à payer, tout est réglé") + "</span></div>" +
      '<div class="kpi"><span class="kpi-libelle">Total des achats</span><span class="kpi-valeur">' + e(MK.fmt.fcfa(c.total_achats)) + "</span></div>" +
      '<div class="kpi"><span class="kpi-libelle">Nombre d\'achats</span><span class="kpi-valeur">' + e(c.nb_achats) + "</span></div>" +
      "</section>" +
      '<p class="cli-dernier">' + e(dernier) + "</p>";
  }

  function afficher(el, r) {
    var c = r.client || {};
    var dette = typeof r.dette === "number" ? r.dette : c.dette || 0;
    var achats = r.achats || [], factures = r.factures || [], paiements = r.paiements || [];
    el.innerHTML = '<article class="cli">' + entete(c, dette) + chiffres(c, dette) +
      '<div class="cli-grille">' +
        section("cli-t-fac", "Factures", factures.length, listeFactures(factures), "Aucune facture pour ce client.", "cli-s1") +
        section("cli-t-ach", "Achats récents", achats.length, liste(achats), "Aucun achat enregistré pour ce client.", "cli-s2") +
        section("cli-t-pay", "Paiements", paiements.length, liste(paiements), "Aucun paiement reçu de ce client.", "cli-s3") +
      "</div></article>";
    var rel = el.querySelector("[data-relancer]");
    if (rel) rel.addEventListener("click", function () { MK.amorcerAssistant("relance " + c.nom); });
    el.querySelector("[data-facture]").addEventListener("click", function () { MK.amorcerAssistant("facture " + c.nom + " "); });
  }

  MK.ecran("client", {
    titre: "Client",
    onglet: "suivi",
    retour: "suivi",
    rendre: function (el, params) {
      var id = String((params && params.id) || "");
      if (!/^\d+$/.test(id)) { etatIntrouvable(el); return; }
      el.innerHTML = '<div class="cli-sq">' + MK.squelette(5) + "</div>";
      return MK.api("/api/clients/" + id).then(function (r) {
        afficher(el, r);
      }, function (err) {
        el.textContent = "";
        if (err && err.status === 404) etatIntrouvable(el);
        else el.appendChild(MK.etatErreur(err, MK.recharger));
      });
    }
  });
})();
