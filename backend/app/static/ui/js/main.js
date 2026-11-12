/* Mon Kiosque : démarrage (session, service worker, routeur) et écran de revue #/__demo. */
(function () {
  "use strict";
  var MK = window.MK;
  var Q = new URLSearchParams(location.search);

  /* ---------- écran de revue : tous les composants communs ---------- */
  MK.ecran("__demo", {
    titre: "Composants",
    onglet: null,
    rendre: function (el) {
      var e = MK.echapper;
      el.innerHTML =
        '<div class="entete-ecran"><div><h1>Composants communs</h1><p class="sous">Écran de revue : tout ce que les écrans peuvent réutiliser.</p></div>' +
        '<div class="segment" role="group" aria-label="Période"><button type="button" aria-pressed="true">Jour</button><button type="button" aria-pressed="false">Semaine</button><button type="button" aria-pressed="false">Mois</button></div></div>' +
        '<div class="pile-l">' +

        '<section class="pile-s"><h2>Indicateurs</h2><div class="grille c4">' +
          '<div class="kpi plein"><div class="kpi-libelle">Ventes du jour</div><div class="kpi-valeur">' + MK.fmt.fcfa(67500) + '</div><div class="kpi-note">12 ventes aujourd\'hui</div></div>' +
          '<div class="kpi"><div class="kpi-libelle">Trésorerie</div><div class="kpi-valeur">' + MK.fmt.fcfa(845000) + '</div><div class="kpi-note positif">+7 % cette semaine</div></div>' +
          '<div class="kpi"><div class="kpi-libelle">Bénéfice du mois</div><div class="kpi-valeur">' + MK.fmt.fcfa(960000) + '</div><div class="kpi-note">' + MK.fmt.fcfaCourt(1480000) + ' de ventes</div></div>' +
          '<div class="kpi"><div class="kpi-libelle">Impayés</div><div class="kpi-valeur negatif">' + MK.fmt.fcfa(128000) + '</div><div class="kpi-note">3 clients</div></div>' +
        "</div></section>" +

        '<section class="pile-s"><h2>Bandeaux</h2>' +
          '<div class="bandeau urgent"><div class="bandeau-corps"><div class="bandeau-titre">Lycée Technique a 6 jours de retard</div><div class="bandeau-texte">80 000 F à encaisser, facture n° 47.</div>' +
          '<div class="bandeau-actions"><button type="button" class="btn danger petit">Relancer</button><button type="button" class="btn secondaire petit">Plus tard</button></div></div></div>' +
          '<div class="bandeau attention"><div class="bandeau-corps"><div class="bandeau-titre">Déclaration mensuelle dans 3 jours</div><div class="bandeau-texte">Ton estimation est prête.</div></div></div>' +
          '<div class="bandeau info"><div class="bandeau-corps"><div class="bandeau-titre">Pour information</div><div class="bandeau-texte">Le résumé du soir part à 19 h.</div></div></div>' +
          '<div class="bandeau ok"><div class="bandeau-corps"><div class="bandeau-titre">Facture payée</div><div class="bandeau-texte">45 000 F reçus par Orange Money.</div></div></div>' +
        "</section>" +

        '<section class="pile-s"><h2>Boutons et pastilles</h2><div class="carte pile">' +
          '<div class="rangee"><button type="button" class="btn primaire">Envoyer la facture</button><button type="button" class="btn secondaire">Modifier</button><button type="button" class="btn discret">Annuler</button><button type="button" class="btn danger">Supprimer</button><button type="button" class="btn" disabled>Désactivé</button><button type="button" class="btn primaire" aria-busy="true">Envoi</button></div>' +
          '<div class="rangee">' + MK.pastille("Payée", "ok") + MK.pastille("Attention", "attention") + MK.pastille("En retard · 6 jours", "urgent") + MK.pastille("Envoyée", "info") + MK.pastille("Brouillon", "neutre") + "</div>" +
        "</div></section>" +

        '<section class="pile-s"><h2>Listes</h2><ul class="liste">' +
          '<li><a class="ligne" href="#/__demo"><span class="ligne-ico">' + MK.icone("historique", { taille: 20 }) + '</span><span class="ligne-corps"><span class="ligne-titre">Facture n° 47 · Lycée Technique d\'Essos</span><span class="ligne-sous">Échue depuis 6 jours</span></span><span class="ligne-fin"><span class="montant">' + MK.fmt.fcfa(80000) + "</span>" + MK.pastille("En retard", "urgent") + "</span></a></li>" +
          '<li><a class="ligne" href="#/__demo"><span class="ligne-ico">' + MK.icone("suivi", { taille: 20 }) + '</span><span class="ligne-corps"><span class="ligne-titre">Facture n° 48 · Cantine Mvog-Ada</span><span class="ligne-sous">À régler avant le 25 nov.</span></span><span class="ligne-fin"><span class="montant">' + MK.fmt.fcfa(36000) + "</span>" + MK.pastille("Envoyée", "info") + "</span></a></li>" +
          '<li><button type="button" class="ligne"><span class="ligne-ico">' + MK.icone("accueil", { taille: 20 }) + '</span><span class="ligne-corps"><span class="ligne-titre">Vente de 3 poulets DG</span><span class="ligne-sous">Aujourd\'hui, 13:05 · mobile money</span></span><span class="ligne-fin"><span class="montant positif">+' + MK.fmt.fcfa(10500) + "</span></span></button></li>" +
        "</ul></section>" +

        '<section class="pile-s"><h2>Champs</h2><div class="carte"><div class="grille">' +
          '<div class="champ"><label for="d1">Nom du commerce</label><input id="d1" type="text" value="Chez Marie"><span class="champ-aide">Il apparaît sur tes factures.</span></div>' +
          '<div class="champ erreur"><label for="d2">Numéro WhatsApp</label><input id="d2" type="tel" value="2376" aria-invalid="true" aria-describedby="d2e"><span class="champ-erreur" id="d2e">Il manque des chiffres.</span></div>' +
          '<div class="champ"><label for="d3">Secteur</label><select id="d3"><option>Restauration</option><option>Commerce</option></select></div>' +
          '<label class="champ-recherche"><img class="ico" src="/ui/icones/vh-recherche-clair.png" width="20" height="20" alt=""><input type="search" placeholder="Chercher un client…" aria-label="Chercher un client"></label>' +
          '<div class="rangee"><button type="button" class="interrupteur" role="switch" aria-checked="true" aria-label="Résumé du soir"></button><span>Résumé du soir à 19 h</span></div>' +
        "</div></div></section>" +

        '<section class="pile-s"><h2>Tableau et barres</h2><div class="table-cadre"><table class="table"><thead><tr><th>Produit</th><th class="droite">Ventes</th><th class="droite">Total</th></tr></thead><tbody>' +
          '<tr><td data-label="Produit">Poulet DG</td><td class="droite montant" data-label="Ventes">154</td><td class="droite montant" data-label="Total">' + MK.fmt.fcfa(539000) + "</td></tr>" +
          '<tr><td data-label="Produit">Repas du jour</td><td class="droite montant" data-label="Ventes">164</td><td class="droite montant" data-label="Total">' + MK.fmt.fcfa(410000) + "</td></tr>" +
          '<tr><td data-label="Produit">Boissons</td><td class="droite montant" data-label="Ventes">367</td><td class="droite montant" data-label="Total">' + MK.fmt.fcfa(220000) + "</td></tr>" +
        '</tbody></table></div>' +
        '<div class="carte"><div class="barre-ligne"><span>Poulet DG</span><div class="barre-rail"><div class="barre-rempli" style="--v:100%"></div></div><span class="barre-valeur">' + MK.fmt.fcfaCourt(540000) + '</span></div>' +
          '<div class="barre-ligne"><span>Repas du jour</span><div class="barre-rail"><div class="barre-rempli" style="--v:76%"></div></div><span class="barre-valeur">' + MK.fmt.fcfaCourt(410000) + '</span></div>' +
          '<div class="barre-ligne"><span>Boissons</span><div class="barre-rail"><div class="barre-rempli orange" style="--v:41%"></div></div><span class="barre-valeur">' + MK.fmt.fcfaCourt(220000) + "</span></div></div></section>" +

        '<section class="pile-s"><h2>États</h2><div class="grille">' +
          MK.squelette(3) +
          MK.etatVide({ titre: "Aucune facture pour l'instant", texte: "Dès que tu en crées une, elle apparaît ici.", icone: "historique", action: { libelle: "Demander à Moki", ecran: "assistant" } }) +
        '</div><div data-erreur></div></section>' +

        '<section class="pile-s"><h2>Fenêtres et messages</h2><div class="rangee">' +
          '<button type="button" class="btn secondaire" data-feuille>Ouvrir une feuille</button>' +
          '<button type="button" class="btn secondaire" data-toast="ok">Toast succès</button>' +
          '<button type="button" class="btn secondaire" data-toast="erreur">Toast erreur</button>' +
          '<button type="button" class="btn secondaire" data-toast="info">Toast info</button></div></section>' +

        '<section class="pile-s"><h2>Formats</h2><div class="carte"><ul class="pile-s" style="margin:0;padding:0;list-style:none">' +
          "<li>fcfa(15000) : <b class=\"montant\">" + e(MK.fmt.fcfa(15000)) + "</b></li>" +
          "<li>fcfaCourt(83000) : <b>" + e(MK.fmt.fcfaCourt(83000)) + "</b> · fcfaCourt(1500000) : <b>" + e(MK.fmt.fcfaCourt(1500000)) + "</b></li>" +
          "<li>date : <b>" + e(MK.fmt.date(new Date().toISOString())) + "</b> · dateLongue : <b>" + e(MK.fmt.dateLongue(new Date().toISOString())) + "</b> · heure : <b>" + e(MK.fmt.heure(new Date().toISOString())) + "</b></li>" +
          "<li>jours(1) : <b>" + e(MK.fmt.jours(1)) + "</b> · jours(3) : <b>" + e(MK.fmt.jours(3)) + "</b></li>" +
        "</ul></div></section>" +
        "</div>";

      var err = new Error("Boom");
      err.status = 0;
      err.reseau = true;
      el.querySelector("[data-erreur]").appendChild(MK.etatErreur(err, function () { MK.toast("Nouvel essai lancé.", "info"); }));
      el.querySelectorAll(".segment > button").forEach(function (b) {
        b.addEventListener("click", function () {
          b.parentNode.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
        });
      });
      el.querySelectorAll(".interrupteur").forEach(function (b) {
        b.addEventListener("click", function () { b.setAttribute("aria-checked", b.getAttribute("aria-checked") === "true" ? "false" : "true"); });
      });
      el.querySelectorAll("[data-toast]").forEach(function (b) {
        var t = b.getAttribute("data-toast");
        b.addEventListener("click", function () { MK.toast(t === "erreur" ? "Tes changements n'ont pas été enregistrés. Réessaie." : t === "info" ? "Moki prépare ta facture." : "Facture envoyée au client.", t); });
      });
      el.querySelector("[data-feuille]").addEventListener("click", function () {
        MK.feuille({
          titre: "Envoyer la relance ?",
          contenu: "<p>Moki va préparer ce message pour le Lycée Technique d'Essos. Rien ne part sans ta confirmation.</p>",
          actions: [{ libelle: "Annuler" }, { libelle: "Je confirme", primaire: true, onclick: function () { MK.toast("Relance prête à transférer.", "ok"); } }]
        });
      });
    }
  });

  /* ---------- session ---------- */
  /* Valide le jeton auprès de /api/accueil. 401 : MK.api a déjà ramené à la connexion. Autre erreur (réseau, serveur) : on garde la session. */
  function restaurerSession() {
    if (MK.mock) {
      var cible = Q.get("ecran");
      if (cible && cible !== "connexion") {
        MK.ouvrirSession({ token: "mock", numero: "237677000001", pme: { nom_commerce: "Chez Marie", ville: "Yaoundé" }, demo: true });
        var params = {};
        Q.forEach(function (v, k) { if (["mock", "cas", "ecran"].indexOf(k) < 0) params[k] = v; });
        if (!location.hash || location.hash === "#") history.replaceState(null, "", location.pathname + location.search + MK.lien(cible, params));
        return MK.api("/api/alertes").then(function (r) { MK.etat.alertesNonLues = r.non_lues; }, function () { /* sans effet */ });
      }
      if (cible === "connexion" && (!location.hash || location.hash === "#")) history.replaceState(null, "", location.pathname + location.search + "#/connexion");
      return Promise.resolve();
    }
    if (!MK.etat.token) return Promise.resolve();
    return MK.api("/api/accueil").then(function (r) {
      MK.etat.pme = { nom_commerce: r.commerce, ville: null };
      MK.etat.demo = !!r.demo;
      MK.etat.alertesNonLues = r.non_lues || 0;
    }, function () { /* 401 déjà traité ; hors ligne ou serveur indisponible : les écrans afficheront leur propre erreur */ });
  }

  /* Compteur d'alertes : une fois par minute, et au retour sur l'onglet */
  function suivreAlertes() {
    function lire() {
      if (!MK.etat.token || document.hidden || navigator.onLine === false) return;
      MK.api("/api/alertes").then(function (r) { MK.etat.alertesNonLues = r.non_lues; }, function () { /* silencieux */ });
    }
    setInterval(lire, 60000);
    document.addEventListener("visibilitychange", lire);
  }

  function serviceWorker() {
    if (MK.mock || !("serviceWorker" in navigator)) return;
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/ui/sw.js", { scope: "/ui/" }).catch(function () { /* HTTP non sécurisé : l'appli marche sans installation */ });
    });
  }

  MK.shell.monter();
  restaurerSession().then(function () {
    MK.demarrer();
    suivreAlertes();
  });
  serviceWorker();
})();
