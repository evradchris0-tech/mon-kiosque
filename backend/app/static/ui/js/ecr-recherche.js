/* Mon Kiosque : écran Recherche (clients, produits, factures). Contrat : docs/06-interface-pro.md §4 et §5. */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;

  var DELAI = 250;
  var MIN = 2;
  var SUGGESTIONS = ["Lycée", "Fouda", "poulet"];
  var STATUTS = {
    payee: { texte: "Payée", type: "ok" },
    envoyee: { texte: "Envoyée", type: "info" },
    en_retard: { texte: "En retard", type: "urgent" }
  };

  /* Retire accents et casse en gardant la correspondance 1 pour 1 des positions */
  function plat(s) {
    var out = "";
    for (var i = 0; i < s.length; i++) {
      var c = s.charAt(i).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
      out += c.length === 1 ? c : s.charAt(i).toLowerCase().charAt(0);
    }
    return out;
  }

  /* Remplit un noeud avec le texte, le terme trouvé entouré de <mark> (textContent uniquement) */
  function surligner(noeud, texte, terme) {
    texte = String(texte === null || texte === undefined ? "" : texte);
    var t = plat(terme.trim());
    var i = t ? plat(texte).indexOf(t) : -1;
    if (i < 0) { noeud.textContent = texte; return noeud; }
    noeud.appendChild(document.createTextNode(texte.slice(0, i)));
    var m = document.createElement("mark");
    m.className = "rec-mark";
    m.textContent = texte.slice(i, i + t.length);
    noeud.appendChild(m);
    noeud.appendChild(document.createTextNode(texte.slice(i + t.length)));
    return noeud;
  }

  function span(classe, texte) {
    var s = document.createElement("span");
    s.className = classe;
    if (texte !== undefined) s.textContent = texte;
    return s;
  }

  function initiale(texte) {
    var m = String(texte || "").match(/[A-Za-zÀ-ÿ0-9]/);
    return m ? m[0].toUpperCase() : "?";
  }

  /* Une ligne de résultat : { href, pastille, titre, sous, fin:{montant, statut} } */
  function ligne(o, terme) {
    var li = document.createElement("li");
    var a = document.createElement("a");
    a.className = "ligne rec-ligne";
    a.href = o.href;
    a.setAttribute("data-rec", "");
    var ico = span("ligne-ico rec-ico", o.pastille);
    ico.setAttribute("aria-hidden", "true");
    var corps = span("ligne-corps");
    corps.appendChild(surligner(span("ligne-titre"), o.titre, terme));
    if (o.sous) corps.appendChild(surligner(span("ligne-sous"), o.sous, terme));
    a.appendChild(ico);
    a.appendChild(corps);
    if (o.fin) {
      var fin = span("ligne-fin");
      fin.appendChild(span("montant", MK.fmt.fcfa(o.fin.montant)));
      var st = STATUTS[o.fin.statut];
      if (st) fin.insertAdjacentHTML("beforeend", MK.pastille(st.texte, st.type));
      a.appendChild(fin);
    }
    li.appendChild(a);
    return li;
  }

  function groupe(titre, lignes) {
    var s = document.createElement("section");
    s.className = "rec-groupe";
    var h = document.createElement("h2");
    h.className = "rec-groupe-titre";
    h.appendChild(document.createTextNode(titre + " "));
    h.appendChild(span("rec-compte", String(lignes.length)));
    var ul = document.createElement("ul");
    ul.className = "liste";
    lignes.forEach(function (l) { ul.appendChild(l); });
    s.appendChild(h);
    s.appendChild(ul);
    return s;
  }

  MK.ecran("recherche", {
    titre: "Recherche",
    onglet: null,
    retour: "accueil",
    rendre: function (el, params) {
      var vivant = true;
      var minuteur = null;
      var numero = 0;

      el.innerHTML =
        '<div class="rec-page">' +
          '<div class="entete-ecran"><div><h1>Rechercher</h1><p class="sous">Un client, un produit ou une facture.</p></div></div>' +
          '<form class="rec-form" role="search" autocomplete="off">' +
            '<label class="champ-recherche">' + MK.icone("recherche", { taille: 20 }) +
              '<span class="sr-only">Rechercher un client, un produit ou une facture</span>' +
              '<input type="search" name="q" placeholder="Nom, produit, numéro de facture…" enterkeyhint="search" autocapitalize="off" spellcheck="false" aria-controls="rec-zone" autofocus>' +
              '<button type="button" class="rec-effacer" hidden>Effacer</button>' +
            "</label>" +
          "</form>" +
          '<div class="rec-zone" id="rec-zone" aria-live="polite" aria-atomic="false"></div>' +
        "</div>";

      var champ = el.querySelector("input");
      var zone = el.querySelector("#rec-zone");
      var form = el.querySelector("form");
      var effacer = el.querySelector(".rec-effacer");

      function lignesRecherche() { return Array.prototype.slice.call(zone.querySelectorAll("[data-rec]")); }

      function initial() {
        zone.textContent = "";
        var bloc = document.createElement("div");
        bloc.className = "rec-initial";
        var p = document.createElement("p");
        p.className = "rec-aide";
        p.textContent = "Essaie :";
        bloc.appendChild(p);
        var puces = document.createElement("div");
        puces.className = "puces";
        SUGGESTIONS.forEach(function (mot) {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "puce";
          b.textContent = mot;
          b.addEventListener("click", function () { champ.value = mot; champ.focus(); lancer(); });
          puces.appendChild(b);
        });
        bloc.appendChild(puces);
        var note = document.createElement("p");
        note.className = "rec-note";
        note.textContent = "Tape au moins " + MIN + " lettres. Les accents et les majuscules n'ont pas d'importance.";
        bloc.appendChild(note);
        zone.appendChild(bloc);
      }

      function afficher(terme, r) {
        zone.textContent = "";
        var clients = (r && r.clients) || [], produits = (r && r.produits) || [], factures = (r && r.factures) || [];
        var total = clients.length + produits.length + factures.length;
        if (!total) {
          var vide = document.createElement("div");
          vide.innerHTML = MK.etatVide({ titre: "Aucun résultat pour « " + terme + " »", texte: "Vérifie l'orthographe, ou essaie une partie du nom ou le numéro de la facture.", icone: "recherche" });
          zone.appendChild(vide.firstChild);
          return;
        }
        var resume = span("rec-resume", total + (total > 1 ? " résultats" : " résultat"));
        resume.setAttribute("role", "status");
        zone.appendChild(resume);
        if (clients.length) zone.appendChild(groupe("Clients", clients.map(function (c) {
          return ligne({ href: MK.lien("client", { id: c.id }), pastille: initiale(c.nom), titre: c.nom, sous: c.detail }, terme);
        })));
        if (produits.length) zone.appendChild(groupe("Produits", produits.map(function (p) {
          return ligne({ href: MK.lien("suivi", { segment: "produits" }), pastille: initiale(p.nom), titre: p.nom, sous: p.detail }, terme);
        })));
        if (factures.length) zone.appendChild(groupe("Factures", factures.map(function (f) {
          return ligne({ href: MK.lien("facture", { id: f.id }), pastille: "N°", titre: "Facture n° " + f.numero, sous: f.client, fin: { montant: f.total, statut: f.statut } }, terme);
        })));
      }

      function lancer() {
        clearTimeout(minuteur);
        effacer.hidden = !champ.value;
        var terme = champ.value.trim();
        var mon = ++numero;
        if (terme.length < MIN) { initial(); return; }
        minuteur = setTimeout(function () {
          zone.innerHTML = MK.squelette(3);
          MK.api("/api/recherche?q=" + encodeURIComponent(terme)).then(function (r) {
            if (vivant && mon === numero) afficher(terme, r);
          }, function (err) {
            if (!vivant || mon !== numero) return;
            zone.textContent = "";
            zone.appendChild(MK.etatErreur(err, lancer));
          });
        }, DELAI);
      }

      champ.addEventListener("input", lancer);
      effacer.addEventListener("click", function () { champ.value = ""; champ.focus(); lancer(); });
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var premiere = lignesRecherche()[0];
        if (premiere) premiere.click();
      });
      champ.addEventListener("keydown", function (ev) {
        if (ev.key === "ArrowDown") {
          var l = lignesRecherche();
          if (l.length) { ev.preventDefault(); l[0].focus(); }
        } else if (ev.key === "Escape" && champ.value) {
          ev.preventDefault();
          champ.value = "";
          lancer();
        }
      });
      zone.addEventListener("keydown", function (ev) {
        if (ev.key !== "ArrowDown" && ev.key !== "ArrowUp") return;
        var l = lignesRecherche();
        var i = l.indexOf(document.activeElement);
        if (i < 0) return;
        ev.preventDefault();
        if (ev.key === "ArrowDown") { if (i < l.length - 1) l[i + 1].focus(); }
        else if (i > 0) l[i - 1].focus(); else champ.focus();
      });

      if (params && params.q) { champ.value = String(params.q).slice(0, 80); lancer(); } else initial();
      /* Le routeur redonne le focus à la zone principale après le rendu : on le reprend ensuite. */
      setTimeout(function () { if (vivant) champ.focus({ preventScroll: true }); }, 60);
      return function () { vivant = false; clearTimeout(minuteur); };
    }
  });
})();
