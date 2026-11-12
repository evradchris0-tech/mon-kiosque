/* Mon Kiosque : écran Accueil (route « accueil »). Données : GET /api/accueil (docs/06-interface-pro.md §5). */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;
  var SVG = "http://www.w3.org/2000/svg";

  /* Icônes d'« À faire » selon le type ; seules les icônes du dossier ui/icones sont utilisées. */
  var ICONE_A_FAIRE = { relance: "suivi", echeance: "modeles", dossier: "modeles", info: "alertes" };

  /* Actions rapides : amorce = texte pré-rempli dans Moki ; sinon navigation. */
  var ACTIONS = [
    { cle: "vente", lib: "Noter une vente", ico: "assistant", amorce: "j'ai vendu ", principale: true },
    { cle: "depense", lib: "Noter une dépense", ico: "historique", amorce: "j'ai payé " },
    { cle: "facture", lib: "Faire une facture", ico: "modeles", amorce: "facture " },
    { cle: "relance", lib: "Relancer un client", ico: "suivi", ecran: "suivi", params: { segment: "impayes" } },
    { cle: "dossier", lib: "Dossier de crédit", ico: "reservation", ecran: "documents" }
  ];

  var ETAPES_DEBUT = [
    { lib: "Note une vente", texte: "« j'ai vendu 3 poulets à 3 500 F »", amorce: "j'ai vendu " },
    { lib: "Note une dépense", texte: "« j'ai payé le gaz 12 000 F »", amorce: "j'ai payé " },
    { lib: "Envoie une facture", texte: "« facture pour la cantine, 2 repas à 2 500 F »", amorce: "facture " }
  ];

  function lien(action) { return MK.lien(action.ecran, action.params); }
  function majuscule(t) { t = String(t || ""); return t.charAt(0).toUpperCase() + t.slice(1); }
  function somme(tab, cle) { return tab.reduce(function (s, x) { return s + (Number(x[cle]) || 0); }, 0); }
  function pluriel(n, un, plusieurs) { return n + " " + (n > 1 ? plusieurs : un); }

  /* ---------- en-tête ---------- */
  function entete(d) {
    var nom = d.gerante ? " " + d.gerante : "";
    var sous = [majuscule(d.date_locale), d.commerce].filter(Boolean).join(" · ");
    return '<div class="entete-ecran acc-entete"><div><h1>Bonjour' + e(nom) + "</h1>" +
      (sous ? '<p class="sous">' + e(sous) + "</p>" : "") + "</div>" +
      (d.demo ? "<div>" + MK.pastille("Données fictives", "info") + "</div>" : "") + "</div>";
  }

  /* ---------- bandeau d'alerte principale ---------- */
  function bandeau(a) {
    if (!a) return "";
    var niveau = ["urgent", "attention", "info"].indexOf(a.niveau) >= 0 ? a.niveau : "info";
    var corps = '<span class="bandeau-ico">' + MK.icone("alertes", { taille: 24 }) + "</span>" +
      '<span class="bandeau-corps"><span class="bandeau-titre">' + e(a.titre) + "</span>" +
      (a.texte ? '<span class="bandeau-texte">' + e(a.texte) + "</span>" : "") + "</span>";
    if (!a.action) return '<div class="bandeau ' + niveau + ' acc-alerte" role="status">' + corps + "</div>";
    return '<a class="bandeau ' + niveau + ' acc-alerte acc-alerte-lien" href="' + e(lien(a.action)) + '">' + corps +
      '<span class="acc-alerte-voir">Voir</span></a>';
  }

  /* ---------- KPI ---------- */
  function kpis(k) {
    var nb = Number(k.nb_ventes_jour) || 0;
    var benefice = Number(k.benefice_mois) || 0;
    var impayes = Number(k.impayes) || 0;
    function carte(o) {
      return '<a class="kpi acc-kpi' + (o.plein ? " plein" : "") + '" href="' + e(MK.lien(o.ecran, o.params)) + '">' +
        '<span class="kpi-libelle">' + e(o.lib) + "</span>" +
        '<span class="kpi-valeur ' + (o.classe || "") + '">' + e(MK.fmt.fcfa(o.valeur)) + "</span>" +
        '<span class="kpi-note">' + e(o.note) + "</span></a>";
    }
    return '<section class="acc-kpis" aria-label="Chiffres clés">' +
      carte({ lib: "Ventes du jour", valeur: k.ventes_jour, note: nb ? pluriel(nb, "vente", "ventes") + " aujourd'hui" : "Aucune vente pour l'instant", plein: true, ecran: "historique", params: { type: "vente" } }) +
      carte({ lib: "Trésorerie", valeur: k.tresorerie, note: "Ce que tu as en main", ecran: "chiffres" }) +
      carte({ lib: "Bénéfice du mois", valeur: benefice, note: "Ventes moins charges", classe: benefice < 0 ? "negatif" : "", ecran: "chiffres", params: { periode: "mois" } }) +
      carte({ lib: "Impayés", valeur: impayes, note: impayes > 0 ? "Ce que tes clients te doivent" : "Rien à relancer", classe: impayes > 0 ? "acc-attention" : "", ecran: "suivi", params: { segment: "impayes" } }) +
      "</section>";
  }

  /* ---------- actions rapides ---------- */
  function actions() {
    return '<section class="acc-section" aria-labelledby="acc-t-actions"><h2 class="acc-titre" id="acc-t-actions">Actions rapides</h2><div class="acc-actions">' +
      ACTIONS.map(function (a) {
        var interieur = '<span class="acc-action-ico">' + MK.icone(a.ico, { taille: 22 }) + '</span><span class="acc-action-lib">' + e(a.lib) + "</span>";
        var cls = "acc-action" + (a.principale ? " principale" : "");
        if (a.amorce !== undefined) return '<button type="button" class="' + cls + '" data-amorce="' + e(a.cle) + '">' + interieur + "</button>";
        return '<a class="' + cls + '" href="' + e(MK.lien(a.ecran, a.params)) + '">' + interieur + "</a>";
      }).join("") + "</div></section>";
  }

  /* ---------- « À faire » ---------- */
  function aFaire(liste) {
    var corps;
    if (!liste.length) {
      corps = '<div class="acc-rien"><b>Rien d\'urgent.</b><span>Tout est à jour, profite de ta journée.</span></div>';
    } else {
      corps = '<ul class="acc-liste">' + liste.map(function (t) {
        var ico = MK.icone(ICONE_A_FAIRE[t.type] || "alertes", { taille: 20 });
        var dedans = '<span class="ligne-ico">' + ico + '</span><span class="ligne-corps"><span class="ligne-titre">' + e(t.titre) + "</span>" +
          (t.texte ? '<span class="ligne-sous">' + e(t.texte) + "</span>" : "") + "</span>";
        if (t.action) return '<li><a class="ligne double" href="' + e(lien(t.action)) + '">' + dedans + "</a></li>";
        return '<li><div class="ligne double">' + dedans + "</div></li>";
      }).join("") + "</ul>";
    }
    return '<section class="carte acc-zone-afaire" aria-labelledby="acc-t-afaire"><div class="acc-titre-ligne"><h2 class="acc-titre" id="acc-t-afaire">À faire</h2>' +
      (liste.length ? '<span class="acc-compte">' + liste.length + "</span>" : "") + "</div>" + corps + "</section>";
  }

  /* ---------- courbe des 7 derniers jours (SVG pur) ---------- */
  function noeud(nom, attrs, texte) {
    var n = document.createElementNS(SVG, nom);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte !== undefined) n.textContent = texte;
    return n;
  }

  /* Barre aux coins supérieurs arrondis. */
  function trace(x, y, l, h, r) {
    r = Math.max(0, Math.min(r, l / 2, h));
    return "M" + x + " " + (y + h) + "V" + (y + r) + "Q" + x + " " + y + " " + (x + r) + " " + y + "H" + (x + l - r) + "Q" + (x + l) + " " + y + " " + (x + l) + " " + (y + r) + "V" + (y + h) + "Z";
  }

  function descriptionGraphe(serie) {
    var total = somme(serie, "ventes");
    return "Ventes des 7 derniers jours. " + serie.map(function (p) { return p.jour + " : " + MK.fmt.fcfa(p.ventes); }).join(", ") + ". Total : " + MK.fmt.fcfa(total) + ".";
  }

  function dessiner(zone, serie) {
    var largeur = Math.max(260, Math.round(zone.clientWidth) || 320);
    var hauteur = largeur < 480 ? 190 : 230;
    var haut = 26, bas = 30, marge = 4;
    var utile = hauteur - haut - bas;
    var max = Math.max.apply(null, serie.map(function (p) { return Number(p.ventes) || 0; }).concat([1]));
    var fente = (largeur - 2 * marge) / serie.length;
    var l = Math.min(52, Math.round(fente * 0.6));
    var svg = noeud("svg", { viewBox: "0 0 " + largeur + " " + hauteur, width: largeur, height: hauteur, role: "img", "aria-labelledby": "acc-g-t acc-g-d", focusable: "false", "class": "acc-svg" });
    svg.appendChild(noeud("title", { id: "acc-g-t" }, "Ventes des 7 derniers jours"));
    svg.appendChild(noeud("desc", { id: "acc-g-d" }, descriptionGraphe(serie)));
    var yBase = haut + utile;
    svg.appendChild(noeud("line", { x1: 0, x2: largeur, y1: yBase + .5, y2: yBase + .5, "class": "acc-g-base" }));
    svg.appendChild(noeud("line", { x1: 0, x2: largeur, y1: haut + .5, y2: haut + .5, "class": "acc-g-guide" }));
    serie.forEach(function (p, i) {
      var v = Number(p.ventes) || 0;
      var auj = i === serie.length - 1;
      var h = v > 0 ? Math.max(4, Math.round(utile * v / max)) : 0;
      var cx = Math.round(marge + fente * i + fente / 2);
      var groupe = noeud("g", { "class": "acc-g-col" + (auj ? " auj" : "") });
      if (h) groupe.appendChild(noeud("path", { d: trace(cx - Math.round(l / 2), yBase - h, l, h, 7), "class": "acc-g-barre" }));
      else groupe.appendChild(noeud("rect", { x: cx - Math.round(l / 2), y: yBase - 2, width: l, height: 2, rx: 1, "class": "acc-g-zero" }));
      groupe.appendChild(noeud("text", { x: cx, y: yBase - h - 8, "text-anchor": "middle", "class": "acc-g-val" }, v ? MK.fmt.fcfaCourt(v) : "0"));
      groupe.appendChild(noeud("text", { x: cx, y: hauteur - 8, "text-anchor": "middle", "class": "acc-g-jour" }, p.jour));
      svg.appendChild(groupe);
    });
    zone.textContent = "";
    zone.appendChild(svg);
  }

  function graphe(serie) {
    var total = somme(serie, "ventes");
    var meilleur = serie.reduce(function (m, p) { return (Number(p.ventes) || 0) > (Number(m.ventes) || 0) ? p : m; }, serie[0] || { ventes: 0 });
    var note = total > 0
      ? "Meilleur jour : " + meilleur.jour + ", " + MK.fmt.fcfa(meilleur.ventes) + "."
      : "Aucune vente sur les 7 derniers jours.";
    return '<section class="carte acc-zone-graphe" aria-labelledby="acc-t-graphe">' +
      '<div class="acc-titre-ligne acc-entete-carte"><h2 class="acc-titre" id="acc-t-graphe">Ventes des 7 derniers jours</h2>' +
      '<span class="acc-total montant">' + e(MK.fmt.fcfa(total)) + '<small> au total</small></span></div>' +
      '<div class="acc-graphe" data-graphe></div><p class="acc-note-graphe">' + e(note) + "</p></section>";
  }

  /* ---------- activité récente ---------- */
  function heureOuJour(iso) {
    var r = MK.fmt.relatif(iso);
    if (r === "aujourd'hui") return MK.fmt.heure(iso);
    if (r === "hier") return "Hier";
    return MK.fmt.date(iso);
  }

  function montantSigne(el) {
    var n = Math.abs(Number(el.montant) || 0);
    if (el.sens === "entree") return { texte: "+" + MK.fmt.fcfa(n), classe: "positif" };
    if (el.sens === "sortie") return { texte: "−" + MK.fmt.fcfa(n), classe: "negatif" };
    return { texte: MK.fmt.fcfa(n), classe: "" };
  }

  function activite(liste) {
    var lignes = liste.slice(0, 5).map(function (el) {
      var m = montantSigne(el);
      var annule = el.statut === "annule";
      var pastille = annule ? MK.pastille("Annulée", "neutre") : el.statut === "retard" ? MK.pastille("En retard", "urgent") : el.statut === "en_attente" ? MK.pastille("En attente", "attention") : "";
      var sous = [el.client, el.detail].filter(Boolean).join(" · ");
      return '<li><div class="ligne acc-ligne-act' + (annule ? " annule" : "") + '">' +
        '<span class="ligne-corps"><span class="ligne-titre">' + e(el.titre) + "</span>" +
        (sous ? '<span class="ligne-sous">' + e(sous) + "</span>" : "") + "</span>" +
        '<span class="ligne-fin"><span class="montant ' + m.classe + '">' + e(m.texte) + "</span>" +
        '<span class="acc-quand">' + (pastille ? pastille + " " : "") + e(heureOuJour(el.date)) + "</span></span></div></li>";
    }).join("");
    return '<section class="carte acc-zone-activite" aria-labelledby="acc-t-activite"><div class="acc-titre-ligne"><h2 class="acc-titre" id="acc-t-activite">Activité récente</h2>' +
      '<a class="acc-tout-voir" href="' + e(MK.lien("historique")) + '">Tout voir</a></div>' +
      '<ul class="acc-liste">' + lignes + "</ul></section>";
  }

  /* ---------- compte tout neuf : invitation + mise en route ---------- */
  function debut() {
    return '<section class="carte acc-debut" aria-labelledby="acc-t-debut">' +
      '<div class="acc-debut-tete"><span class="surtitre">Pour commencer</span><h2 id="acc-t-debut">Note ta première vente</h2>' +
      "<p>Écris-la comme tu la dirais à Moki, il s'occupe du reste : le total, le suivi et le bénéfice.</p>" +
      '<button type="button" class="btn primaire" data-amorce="vente">Noter ma première vente</button></div>' +
      '<ol class="acc-etapes" aria-label="Mise en route">' + ETAPES_DEBUT.map(function (s, i) {
        return '<li><button type="button" class="acc-etape" data-etape="' + i + '"><span class="acc-etape-num" aria-hidden="true">' + (i + 1) + "</span>" +
          '<span class="acc-etape-corps"><b>' + e(s.lib) + "</b><span>" + e(s.texte) + "</span></span></button></li>";
      }).join("") + "</ol></section>";
  }

  /* ---------- squelette ---------- */
  function squelette() {
    var kpi = '<div class="acc-sq-kpi"><div class="squelette"></div><div class="squelette"></div><div class="squelette"></div></div>';
    return '<div role="status" aria-busy="true"><span class="sr-only">Chargement de ton accueil…</span>' +
      '<div class="acc-sq-tete"><div class="squelette"></div><div class="squelette"></div></div>' +
      '<div class="acc-kpis">' + kpi + kpi + kpi + kpi + "</div>" +
      '<div class="acc-sq-bloc squelette"></div><div class="acc-sq-bloc squelette"></div></div>';
  }

  /* ---------- écran ---------- */
  MK.ecran("accueil", {
    titre: "Accueil",
    onglet: "accueil",
    rendre: function (el) {
      el.classList.add("acc");
      el.innerHTML = squelette();
      return MK.api("/api/accueil").then(function (d) {
        d = d || {};
        var k = d.kpis || {};
        var serie = Array.isArray(d.serie_7j) ? d.serie_7j : [];
        var recent = Array.isArray(d.activite_recente) ? d.activite_recente : [];
        var taches = Array.isArray(d.a_faire) ? d.a_faire : [];
        var neuf = !recent.length && somme(serie, "ventes") === 0;
        if (typeof d.non_lues === "number") MK.etat.alertesNonLues = d.non_lues;

        el.innerHTML = entete(d) + bandeau(d.alerte_principale) + kpis(k) + actions() +
          (neuf
            ? '<div class="acc-bas acc-bas-neuf">' + debut() + (taches.length ? aFaire(taches) : "") + "</div>"
            : '<div class="acc-bas">' + aFaire(taches) + (serie.length ? graphe(serie) : "") + (recent.length ? activite(recent) : "") + "</div>");

        el.addEventListener("click", function (ev) {
          var b = ev.target.closest ? ev.target.closest("[data-amorce],[data-etape]") : null;
          if (!b) return;
          if (b.hasAttribute("data-etape")) { MK.amorcerAssistant(ETAPES_DEBUT[Number(b.getAttribute("data-etape"))].amorce); return; }
          var a = ACTIONS.filter(function (x) { return x.cle === b.getAttribute("data-amorce"); })[0];
          if (a) MK.amorcerAssistant(a.amorce);
        });

        var zone = el.querySelector("[data-graphe]");
        if (!zone) return undefined;
        var largeurVue = 0;
        var tracer = function () {
          var l = Math.round(zone.clientWidth);
          if (l && l !== largeurVue) { largeurVue = l; dessiner(zone, serie); }
        };
        dessiner(zone, serie);
        largeurVue = Math.round(zone.clientWidth);
        if (typeof ResizeObserver === "function") {
          var obs = new ResizeObserver(tracer);
          obs.observe(zone);
          return function () { obs.disconnect(); };
        }
        window.addEventListener("resize", tracer);
        return function () { window.removeEventListener("resize", tracer); };
      });
    }
  });
})();
