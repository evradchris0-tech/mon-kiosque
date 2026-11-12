/* Mon Kiosque : écran Chiffres (route « chiffres », retour « reglages »).
   Données : GET /api/chiffres?periode=jour|semaine|mois|annee. Contrat : docs/06-interface-pro.md §4 et §5. */
(function () {
  "use strict";
  var MK = window.MK;
  if (!MK) return;
  var e = MK.echapper, f = MK.fmt;

  var PERIODES = [["jour", "Jour"], ["semaine", "Semaine"], ["mois", "Mois"], ["annee", "Année"]];
  var MODES = [["cash", "Espèces"], ["mobile_money", "Mobile money"], ["credit", "À crédit"], ["facture", "Factures"]];
  var SVG = "http://www.w3.org/2000/svg";

  function num(x) { return Number(x) || 0; }
  function periodeValide(p) { return PERIODES.some(function (x) { return x[0] === p; }); }
  function pct(part, total) { return total > 0 ? Math.round((part / total) * 100) : 0; }

  /* ---------- briques HTML ---------- */
  function kpi(libelle, valeur, note, o) {
    o = o || {};
    return '<div class="kpi' + (o.plein ? " plein" : "") + (o.classe ? " " + o.classe : "") + '">' +
      '<span class="kpi-libelle">' + e(libelle) + "</span>" +
      '<span class="kpi-valeur' + (o.negatif ? " negatif" : "") + '">' + e(valeur) + "</span>" +
      '<span class="kpi-note">' + e(note) + "</span></div>";
  }

  function barres(lignes, o) {
    o = o || {};
    var html = '<ul class="chi-barres">';
    lignes.forEach(function (l) {
      var part = o.total ? pct(l.val, o.total) : (o.max > 0 ? Math.round((l.val / o.max) * 100) : 0);
      html += '<li class="chi-barre"><div class="chi-barre-tete"><span class="chi-barre-lib">' + e(l.lib) + "</span>" +
        '<span class="chi-barre-val">' + e(f.fcfa(l.val)) + (o.total ? '<span class="chi-barre-pct">' + pct(l.val, o.total) + "&nbsp;%</span>" : "") + "</span></div>" +
        '<div class="barre-rail" aria-hidden="true"><div class="barre-rempli' + (o.orange ? " chi-orange" : "") + '" style="--v:0%" data-v="' + part + '"></div></div></li>';
    });
    return html + "</ul>";
  }

  function carte(id, titre, corps, classe) {
    return '<section class="carte chi-carte' + (classe ? " " + classe : "") + '" aria-labelledby="' + id + '"><h2 class="carte-titre" id="' + id + '">' + titre + "</h2>" + corps + "</section>";
  }

  /* ---------- graphique SVG : ventes contre charges ---------- */
  function noeud(nom, attrs) {
    var n = document.createElementNS(SVG, nom);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }
  function pasNet(max) {
    var brut = max / 4, mag = Math.pow(10, Math.floor(Math.log10(brut))), r = brut / mag;
    return (r <= 1 ? 1 : r <= 2 ? 2 : r <= 5 ? 5 : 10) * mag;
  }
  function barreArrondie(x, haut, larg, bas, classe) {
    var r = Math.min(3, larg / 2, bas - haut);
    return noeud("path", {
      "class": classe,
      d: "M" + x + "," + bas + "L" + x + "," + (haut + r) + "Q" + x + "," + haut + " " + (x + r) + "," + haut +
        "L" + (x + larg - r) + "," + haut + "Q" + (x + larg) + "," + haut + " " + (x + larg) + "," + (haut + r) + "L" + (x + larg) + "," + bas + "Z"
    });
  }

  function dessiner(zone, serie, resume) {
    zone.textContent = "";
    var max = 0;
    serie.forEach(function (p) { max = Math.max(max, num(p.ventes), num(p.charges)); });
    if (max <= 0) {
      var p = document.createElement("p");
      p.className = "chi-aide";
      p.textContent = "Aucun mouvement sur cette période.";
      zone.appendChild(p);
      return;
    }
    var W = Math.max(260, Math.floor(zone.clientWidth || 320));
    var H = W < 520 ? 232 : 288;
    var m = { g: 48, d: 8, h: 22, b: 30 };
    var pas = pasNet(max), haut = Math.ceil(max / pas - 1e-9) * pas;
    var iw = W - m.g - m.d, ih = H - m.h - m.b, gw = iw / serie.length;
    var bw = Math.min(32, Math.max(6, gw * 0.3)), ec = Math.max(2, Math.min(4, bw / 6));
    function y(v) { return m.h + ih - (v / haut) * ih; }

    var svg = noeud("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, role: "img", "aria-label": resume, "class": "chi-svg" });
    var titre = noeud("title", {});
    titre.textContent = "Ventes et charges par période";
    svg.appendChild(titre);

    for (var t = 0; t <= haut + 1e-9; t += pas) {
      svg.appendChild(noeud("line", { x1: m.g, x2: W - m.d, y1: y(t), y2: y(t), "class": t === 0 ? "chi-base" : "chi-grille" }));
      var lib = noeud("text", { x: m.g - 8, y: y(t) + 4, "text-anchor": "end", "class": "chi-axe" });
      lib.textContent = t === 0 ? "0" : f.fcfaCourt(t);
      svg.appendChild(lib);
    }

    var saut = Math.max(1, Math.ceil(34 / gw));
    var valeurs = gw >= 110 ? 2 : gw >= 50 ? 1 : 0;
    serie.forEach(function (p, i) {
      var cx = m.g + gw * i + gw / 2, base = y(0);
      [["ventes", cx - ec / 2 - bw, "chi-bar-v"], ["charges", cx + ec / 2, "chi-bar-c"]].forEach(function (b, k) {
        var v = num(p[b[0]]);
        if (v <= 0) return;
        var h = Math.max(2, base - y(v));
        var barre = barreArrondie(b[1], base - h, bw, base, "chi-bar " + b[2]);
        barre.style.animationDelay = (i * 25) + "ms";
        svg.appendChild(barre);
        if (valeurs > k) {
          var txt = noeud("text", { x: b[1] + bw / 2, y: base - h - 5, "text-anchor": "middle", "class": "chi-val" });
          txt.textContent = f.fcfaCourt(v);
          svg.appendChild(txt);
        }
      });
      if (i % saut === 0) {
        var x = noeud("text", { x: cx, y: H - 9, "text-anchor": "middle", "class": "chi-axe chi-axe-x" });
        x.textContent = p.libelle;
        svg.appendChild(x);
      }
    });
    zone.appendChild(svg);
  }

  function resumeSerie(serie) {
    return "Ventes et charges par période. " + serie.map(function (p) {
      return p.libelle + " : ventes " + f.fcfa(p.ventes) + ", charges " + f.fcfa(p.charges);
    }).join(" ; ") + ".";
  }

  function tableauSerie(serie) {
    var html = '<div class="table-cadre chi-tableau"><table class="table"><thead><tr><th scope="col">Période</th><th scope="col" class="droite">Ventes</th><th scope="col" class="droite">Charges</th></tr></thead><tbody>';
    serie.forEach(function (p) {
      html += '<tr><th scope="row" data-label="Période" class="chi-th-ligne">' + e(p.libelle) + '</th><td class="droite montant" data-label="Ventes">' + e(f.fcfa(p.ventes)) +
        '</td><td class="droite montant" data-label="Charges">' + e(f.fcfa(p.charges)) + "</td></tr>";
    });
    return html + "</tbody></table></div>";
  }

  /* ---------- corps de l'écran ---------- */
  function corpsHtml(d) {
    var ventes = num(d.ventes), charges = num(d.charges), benefice = num(d.benefice);
    var stock = num(d.stock), retraits = num(d.retraits_perso), tresorerie = num(d.tresorerie);
    var serie = Array.isArray(d.serie) ? d.serie : [];
    var modes = d.par_mode || {};
    var top = Array.isArray(d.top_produits) ? d.top_produits : [];
    var postes = Array.isArray(d.depenses_par_poste) ? d.depenses_par_poste : [];
    var perte = benefice < 0;
    var html = "";

    /* 1. Trois chiffres clés */
    html += '<section class="chi-kpis" aria-label="Chiffres clés · ' + e(d.libelle || "") + '">' +
      kpi("Ventes", f.fcfa(ventes), "Ce que tu as vendu", { classe: "chi-kpi-ventes" }) +
      kpi("Charges", f.fcfa(charges), "Ce que coûte ton commerce") +
      kpi("Bénéfice", f.fcfa(benefice), perte ? "Tu as dépensé plus que vendu" : "Ventes moins charges", { plein: !perte, negatif: perte }) +
      "</section>";

    /* 2. Deux blocs distincts : trésorerie et bénéfice */
    html += '<div class="chi-duo">' +
      '<section class="carte chi-bloc chi-bloc-treso" aria-labelledby="chi-t-treso">' +
        '<div class="chi-bloc-tete"><h2 class="carte-titre" id="chi-t-treso">Trésorerie</h2><span class="pastille ok">Argent disponible</span></div>' +
        '<div class="chi-grand montant">' + e(f.fcfa(tresorerie)) + "</div>" +
        '<p class="chi-formule">Encaissements <b>−</b> paiements réels</p>' +
        '<p class="chi-aide">C\'est l\'argent que tu as vraiment sous la main : ce qui est entré (espèces, mobile money, factures payées) moins ce que tu as vraiment payé. Une vente à crédit n\'y entre que le jour où le client règle.</p>' +
      "</section>" +
      '<section class="carte chi-bloc chi-bloc-benef" aria-labelledby="chi-t-benef">' +
        '<div class="chi-bloc-tete"><h2 class="carte-titre" id="chi-t-benef">Bénéfice</h2><span class="pastille info">Ce que ton commerce gagne</span></div>' +
        '<div class="chi-grand montant' + (perte ? " negatif" : "") + '">' + e(f.fcfa(benefice)) + "</div>" +
        '<dl class="chi-calcul"><div><dt>Ventes</dt><dd class="montant">' + e(f.fcfa(ventes)) + '</dd></div><div><dt>Charges</dt><dd class="montant">' + e(f.fcfa(-charges)) + '</dd></div>' +
        '<div class="chi-calcul-total"><dt>Bénéfice</dt><dd class="montant' + (perte ? " negatif" : "") + '">' + e(f.fcfa(benefice)) + "</dd></div></dl>" +
        '<p class="chi-aide">Ventes moins charges. Les achats de stock et tes retraits personnels n\'y entrent pas : ils sont comptés à part, plus bas.</p>' +
      "</section></div>";

    /* 3. Graphique ventes contre charges */
    html += carte("chi-t-serie", 'Ventes et charges <span class="petit muted chi-sous-titre">· ' + e(d.libelle || "") + "</span>",
      '<div class="chi-legende"><span><i class="chi-sw chi-sw-v"></i>Ventes</span><span><i class="chi-sw chi-sw-c"></i>Charges</span></div>' +
      '<div class="chi-graphe" data-graphe></div>' +
      (serie.length ? '<details class="chi-details"><summary>Voir les valeurs</summary>' + tableauSerie(serie) + "</details>" : ""), "chi-carte-large");

    /* 4. Nombre de ventes et panier moyen */
    html += '<section class="chi-kpis chi-kpis-duo" aria-label="Rythme des ventes">' +
      kpi("Nombre de ventes", String(num(d.nb_ventes)), "Ventes notées sur la période") +
      kpi("Panier moyen", f.fcfa(num(d.panier_moyen)), "Montant moyen d'une vente") + "</section>";

    /* 5. Pro et perso */
    var tot = charges + stock + retraits;
    var segs = [["chi-s1", "Charges du commerce", charges], ["chi-s2", "Achats de stock", stock], ["chi-s3", "Retraits personnels", retraits]];
    html += carte("chi-t-pp", "Pro et perso",
      '<p class="chi-aide chi-intro">Ce qui sort de ta caisse, rangé en trois : le commerce, le stock, toi.</p>' +
      (tot > 0 ? '<div class="chi-pile" role="img" aria-label="' + e("Charges du commerce " + f.fcfa(charges) + ", achats de stock " + f.fcfa(stock) + ", retraits personnels " + f.fcfa(retraits)) + '">' +
        segs.map(function (s) { return s[2] > 0 ? '<span class="' + s[0] + '" style="flex-grow:' + s[2] + '"></span>' : ""; }).join("") + "</div>" : "") +
      '<ul class="chi-pp">' +
        '<li><i class="chi-sw chi-s1"></i><div class="chi-pp-corps"><span class="chi-pp-lib">Charges du commerce</span><span class="chi-pp-aide">Marché, salaires, loyer, électricité. Elles réduisent ton bénéfice.</span></div><span class="chi-pp-val montant">' + e(f.fcfa(charges)) + "</span></li>" +
        '<li><i class="chi-sw chi-s2"></i><div class="chi-pp-corps"><span class="chi-pp-lib">Achats de stock</span><span class="chi-pp-aide">Marchandises achetées pour revendre. Elles sortent de ta trésorerie mais pas de ton bénéfice.</span></div><span class="chi-pp-val montant">' + e(f.fcfa(stock)) + "</span></li>" +
        '<li><i class="chi-sw chi-s3"></i><div class="chi-pp-corps"><span class="chi-pp-lib">Retraits personnels</span><span class="chi-pp-aide"><b>Jamais comptés comme charge du commerce.</b> Ils réduisent seulement ta trésorerie.</span></div><span class="chi-pp-val montant">' + e(f.fcfa(retraits)) + "</span></li>" +
      "</ul>");

    /* 6. Encaissements par mode */
    var totalModes = 0;
    var lignesModes = MODES.map(function (m) { var v = num(modes[m[0]]); totalModes += v; return { lib: m[1], val: v }; });
    html += carte("chi-t-modes", "Comment tes clients paient",
      '<p class="chi-aide chi-intro">Répartition de tes encaissements par mode de paiement.</p>' + barres(lignesModes, { total: totalModes }) +
      '<p class="chi-note">À crédit et Factures : l\'argent n\'est pas encore dans ta caisse tant que le client n\'a pas payé.</p>');

    /* 7. Top produits et dépenses par poste */
    var maxTop = 0, maxPostes = 0;
    top.forEach(function (p) { maxTop = Math.max(maxTop, num(p.total)); });
    postes.forEach(function (p) { maxPostes = Math.max(maxPostes, num(p.total)); });
    html += carte("chi-t-top", "Produits qui rapportent le plus",
      top.length ? barres(top.map(function (p) { return { lib: p.nom, val: num(p.total) }; }), { max: maxTop }) : '<p class="chi-aide">Pas encore de produit vendu sur cette période.</p>');
    html += carte("chi-t-postes", "Où part ton argent",
      postes.length ? barres(postes.map(function (p) { return { lib: p.libelle, val: num(p.total) }; }), { max: maxPostes, orange: true }) : '<p class="chi-aide">Aucune dépense notée sur cette période.</p>');

    return html;
  }

  function estVide(d) {
    return !(num(d.ventes) || num(d.charges) || num(d.stock) || num(d.retraits_perso) || num(d.tresorerie) || num(d.nb_ventes));
  }

  /* ---------- écran ---------- */
  MK.ecran("chiffres", {
    titre: "Chiffres",
    onglet: "reglages",
    retour: "reglages",
    rendre: function (el, params) {
      var periode = periodeValide(params && params.periode) ? params.periode : "mois";
      var version = 0, vivant = true, observateur = null, largeur = 0, courant = null;

      el.innerHTML =
        '<div class="entete-ecran"><div><h1>Tes chiffres</h1><p class="sous">Où en est ton commerce : ce que tu vends, ce que ça coûte et l\'argent dont tu disposes.</p></div></div>' +
        '<div class="chi-barre-periode"><div class="segment plein" role="group" aria-label="Période">' +
        PERIODES.map(function (p) { return '<button type="button" data-periode="' + p[0] + '" aria-pressed="' + (p[0] === periode) + '">' + p[1] + "</button>"; }).join("") +
        '</div></div><p class="sr-only" role="status" data-statut></p><div class="chi-corps" data-corps></div>';
      var corps = el.querySelector("[data-corps]");
      var statut = el.querySelector("[data-statut]");
      var boutons = Array.prototype.slice.call(el.querySelectorAll("[data-periode]"));

      function arreterObservation() {
        if (observateur) { observateur.disconnect(); observateur = null; }
        window.removeEventListener("resize", redessiner);
      }
      function zoneGraphe() { return corps.querySelector("[data-graphe]"); }
      function redessiner() {
        var z = zoneGraphe();
        if (!z || !courant) return;
        var w = Math.floor(z.clientWidth);
        if (Math.abs(w - largeur) < 2) return;
        largeur = w;
        dessiner(z, courant.serie || [], resumeSerie(courant.serie || []));
      }
      function observer() {
        arreterObservation();
        var z = zoneGraphe();
        if (!z) return;
        largeur = Math.floor(z.clientWidth);
        if (typeof ResizeObserver === "function") { observateur = new ResizeObserver(redessiner); observateur.observe(z); }
        else window.addEventListener("resize", redessiner);
      }

      function afficher(d) {
        courant = d;
        if (estVide(d)) {
          corps.innerHTML = MK.etatVide({
            icone: "concurrence",
            titre: "Pas encore de données sur cette période",
            texte: "Dès que tu notes une vente ou une dépense avec Moki, tes chiffres apparaissent ici.",
            action: { libelle: "Noter une vente avec Moki", ecran: "assistant" }
          });
          statut.textContent = "Aucune donnée sur cette période.";
          arreterObservation();
          return;
        }
        corps.innerHTML = corpsHtml(d);
        var z = zoneGraphe();
        if (z) dessiner(z, d.serie || [], resumeSerie(d.serie || []));
        observer();
        setTimeout(function () {
          if (!vivant) return;
          Array.prototype.forEach.call(corps.querySelectorAll("[data-v]"), function (n) { n.style.setProperty("--v", n.getAttribute("data-v") + "%"); });
        }, 40);
        statut.textContent = "Chiffres chargés : " + (d.libelle || "");
      }

      function charger(p) {
        var v = ++version;
        periode = p;
        boutons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-periode") === p)); });
        arreterObservation();
        courant = null;
        corps.innerHTML = MK.squelette(5);
        statut.textContent = "Chargement des chiffres…";
        MK.api("/api/chiffres?periode=" + encodeURIComponent(p)).then(function (d) {
          if (!vivant || v !== version) return;
          afficher(d || {});
        }, function (err) {
          if (!vivant || v !== version) return;
          corps.textContent = "";
          corps.appendChild(MK.etatErreur(err, function () { charger(p); }));
          statut.textContent = "Les chiffres n'ont pas pu être chargés.";
        });
      }

      boutons.forEach(function (b) {
        b.addEventListener("click", function () {
          var p = b.getAttribute("data-periode");
          if (p !== periode) charger(p);
        });
      });
      charger(periode);

      return function () { vivant = false; arreterObservation(); };
    }
  });
})();
