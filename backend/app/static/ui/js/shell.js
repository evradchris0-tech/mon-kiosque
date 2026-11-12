/* Mon Kiosque : coquille (en-tête, barre d'onglets mobile, menu latéral desktop, cloche, bandeau hors ligne). */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;
  var CLE_REPLI = "mk_menu_replie";

  var ONGLETS = [
    { id: "accueil", lib: "Accueil", ico: "accueil" },
    { id: "suivi", lib: "Suivi", ico: "suivi" },
    { id: "assistant", lib: "Moki", ico: "assistant" },
    { id: "alertes", lib: "Alertes", ico: "alertes" },
    { id: "reglages", lib: "Réglages", ico: "parametres" }
  ];
  var MENU_HAUT = [
    { id: "accueil", lib: "Accueil", ico: "accueil" },
    { id: "suivi", lib: "Suivi", ico: "suivi" },
    { id: "assistant", lib: "Moki, l'assistant", ico: "assistant" },
    { id: "alertes", lib: "Alertes", ico: "alertes", badge: true }
  ];
  var MENU_COMMERCE = [
    { id: "chiffres", lib: "Chiffres", ico: "concurrence" },
    { id: "historique", lib: "Historique", ico: "historique" },
    { id: "documents", lib: "Documents", ico: "modeles" },
    { id: "connexions", lib: "Connexions", ico: "connexions" }
  ];
  var MENU_BAS = [
    { id: "aide", lib: "Aide", ico: "aide" },
    { id: "reglages", lib: "Réglages", ico: "parametres" }
  ];
  var CLES_MENU = {};
  MENU_HAUT.concat(MENU_COMMERCE, MENU_BAS).forEach(function (m) { CLES_MENU[m.id] = true; });

  var racine = null;
  var courant = { def: null, id: null };

  function lienMenu(m) {
    return '<a class="menu-lien" href="#/' + m.id + '" data-menu="' + m.id + '" title="' + e(m.lib) + '"' + (m.badge ? ' data-nb="0"' : "") + ">" +
      MK.icone(m.ico, { variante: "fonce", classe: "menu-ico-fonce" }) + '<span class="menu-lib">' + e(m.lib) + "</span>" +
      (m.badge ? '<span class="menu-lien-badge" data-badge hidden></span>' : "") + "</a>";
  }

  function monter() {
    var app = document.getElementById("app");
    if (!app || racine) return;
    app.innerHTML =
      '<a class="lien-evitement" href="#ecran" data-evitement>Aller au contenu</a>' +
      '<div class="coque" id="coque" data-replie="0" data-plein="0">' +
        '<nav class="menu" id="menu" aria-label="Menu principal">' +
          '<a class="menu-marque" href="#/accueil" aria-label="Mon Kiosque, accueil"><span class="logo"><img src="/ui/img/logo.svg" alt="" width="62" height="62"></span>' +
            '<span class="menu-marque-texte"><b>Mon Kiosque</b><small data-commerce></small></span></a>' +
          '<ul class="menu-liste">' + MENU_HAUT.map(function (m) { return "<li>" + lienMenu(m) + "</li>"; }).join("") + "</ul>" +
          '<div class="menu-titre">Mon commerce</div><div class="menu-filet" aria-hidden="true"></div>' +
          '<ul class="menu-liste">' + MENU_COMMERCE.map(function (m) { return "<li>" + lienMenu(m) + "</li>"; }).join("") + "</ul>" +
          '<div class="menu-bas"><ul class="menu-liste">' + MENU_BAS.map(function (m) { return "<li>" + lienMenu(m) + "</li>"; }).join("") + "</ul>" +
            '<button type="button" class="menu-lien menu-replier" id="btn-replier" aria-expanded="true" title="Replier le menu">' + MK.icone("replier", { variante: "fonce" }) + '<span class="menu-lib">Replier le menu</span></button></div>' +
        "</nav>" +
        '<div class="coque-centre">' +
          '<div class="hors-ligne" id="hors-ligne" role="status" hidden>Tu es hors connexion. Ce que tu vois peut ne pas être à jour.</div>' +
          '<header class="entete" id="entete">' +
            '<div class="ent-gauche">' +
              '<a class="logo ent-logo" href="#/accueil" aria-label="Mon Kiosque, accueil"><img src="/ui/img/logo.svg" alt="" width="62" height="62"></a>' +
              '<button type="button" class="bouton-rond ent-retour" id="btn-retour" aria-label="Retour" hidden>' + MK.icone("retour", { taille: 22 }) + '<span class="ent-retour-lib"></span></button>' +
              '<p class="ent-titre" id="ent-titre"></p>' +
              '<nav class="ent-fil" id="ent-fil" aria-label="Fil d\'Ariane"></nav>' +
            "</div>" +
            '<div class="ent-droite">' +
              '<a class="bouton-rond ent-recherche" id="btn-recherche" href="#/recherche" aria-label="Rechercher">' + MK.icone("recherche", { taille: 22 }) + '<span class="ent-recherche-lib">Rechercher…</span></a>' +
              '<a class="bouton-rond ent-cloche" id="btn-cloche" href="#/alertes" aria-label="Alertes">' + MK.icone("alertes", { taille: 22 }) + '<span class="badge" data-badge hidden></span></a>' +
            "</div>" +
          "</header>" +
          '<main id="ecran" tabindex="-1"></main>' +
        "</div>" +
        '<nav class="onglets" id="onglets" aria-label="Navigation principale">' +
          ONGLETS.map(function (o) {
            return '<a class="onglet" href="#/' + o.id + '" data-onglet="' + o.id + '"><span class="onglet-ico">' + MK.icone(o.ico, { taille: 24 }) +
              (o.id === "alertes" ? '<span class="badge" data-badge hidden></span>' : "") + "</span><span>" + e(o.lib) + "</span></a>";
          }).join("") +
        "</nav>" +
      "</div>";
    racine = document.getElementById("coque");

    var replie = MK.stockage.lire(CLE_REPLI) === "1";
    appliquerRepli(replie);
    document.getElementById("btn-replier").addEventListener("click", function () {
      var r = racine.getAttribute("data-replie") !== "1";
      appliquerRepli(r);
      MK.stockage.ecrire(CLE_REPLI, r ? "1" : "0");
    });
    document.getElementById("btn-retour").addEventListener("click", function () {
      var def = courant.def;
      if (def && def.retour) MK.aller(def.retour); else MK.retour();
    });
    app.querySelector("[data-evitement]").addEventListener("click", function (ev) {
      ev.preventDefault();
      document.getElementById("ecran").focus();
    });
    window.addEventListener("scroll", function () { document.getElementById("entete").classList.toggle("defile", window.scrollY > 4); }, { passive: true });

    window.addEventListener("offline", horsLigne);
    window.addEventListener("online", function () { horsLigne(); MK.toast("Connexion rétablie.", "ok"); });
    horsLigne();
    commerce();
    badge(MK.etat.alertesNonLues);
  }

  function appliquerRepli(r) {
    racine.setAttribute("data-replie", r ? "1" : "0");
    var b = document.getElementById("btn-replier");
    b.setAttribute("aria-expanded", r ? "false" : "true");
    var lib = r ? "Déplier le menu" : "Replier le menu";
    b.title = lib;
    b.querySelector(".menu-lib").textContent = lib;
  }

  function horsLigne() {
    var h = document.getElementById("hors-ligne");
    if (h) h.hidden = navigator.onLine !== false;
  }

  function commerce() {
    var c = racine && racine.querySelector("[data-commerce]");
    if (c) c.textContent = (MK.etat.pme && MK.etat.pme.nom_commerce) || "";
  }

  function badge(n) {
    if (!racine) return;
    var txt = n > 99 ? "99+" : String(n);
    racine.querySelectorAll("[data-badge]").forEach(function (b) { b.textContent = txt; b.hidden = !n; });
    var m = racine.querySelector('[data-menu="alertes"]');
    if (m) m.setAttribute("data-nb", String(n));
    var libelle = n ? "Alertes, " + n + (n > 1 ? " non lues" : " non lue") : "Alertes";
    var cloche = document.getElementById("btn-cloche");
    cloche.setAttribute("aria-label", libelle);
    var tab = racine.querySelector('[data-onglet="alertes"]');
    tab.setAttribute("aria-label", libelle);
  }

  function marquer(el, actif) {
    if (actif) el.setAttribute("aria-current", "page"); else el.removeAttribute("aria-current");
  }

  function maj(o) {
    if (!racine) return;
    var def = o.def, id = o.id;
    courant = o;
    racine.setAttribute("data-plein", def.plein ? "1" : "0");
    document.body.setAttribute("data-ecran", id);
    var cle = CLES_MENU[id] ? id : def.onglet || null;

    racine.querySelectorAll("[data-onglet]").forEach(function (a) { marquer(a, a.getAttribute("data-onglet") === (def.onglet || (CLES_MENU[id] ? id : null))); });
    racine.querySelectorAll("[data-menu]").forEach(function (a) {
      var ico = a.querySelector(".ico");
      var actif = a.getAttribute("data-menu") === cle;
      marquer(a, actif);
      if (ico) ico.src = ico.src.replace(/-(clair|fonce)\.png/, actif ? "-clair.png" : "-fonce.png");
    });
    marquer(document.getElementById("btn-cloche"), id === "alertes");
    marquer(document.getElementById("btn-recherche"), id === "recherche");

    var titre = def.titre || "";
    document.getElementById("ent-titre").textContent = titre;
    var parent = def.retour ? MK.ecrans[def.retour] : null;
    var retour = document.getElementById("btn-retour");
    var logo = racine.querySelector(".ent-logo");
    retour.hidden = !def.retour;
    logo.hidden = !!def.retour;
    var libParent = (parent && parent.titre) || "Retour";
    retour.setAttribute("aria-label", "Retour : " + libParent);
    retour.querySelector(".ent-retour-lib").textContent = libParent;
    var fil = document.getElementById("ent-fil");
    fil.innerHTML = def.retour ? '<a href="#/' + e(def.retour) + '">' + e(libParent) + "</a> › <b>" + e(titre) + "</b>" : (id === "accueil" ? "" : "<b>" + e(titre) + "</b>");
  }

  MK.shell = { monter: monter, maj: maj, badge: badge, commerce: commerce };
})();
