/* Mon Kiosque : écran Suivi (factures, impayés, clients, produits). Contrat : docs/06-interface-pro.md §4. */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;

  var SEGMENTS = [
    { id: "factures", lib: "Factures" },
    { id: "impayes", lib: "Impayés" },
    { id: "clients", lib: "Clients" },
    { id: "produits", lib: "Produits" }
  ];
  var ETATS = [
    { id: "tout", lib: "Toutes" },
    { id: "envoyee", lib: "Envoyées" },
    { id: "payee", lib: "Payées" },
    { id: "en_retard", lib: "En retard" }
  ];
  var URLS = {
    factures: "/api/factures?statut=tout&limite=100",
    clients: "/api/clients?limite=100",
    produits: "/api/produits?limite=100"
  };
  var ACTIONS = {
    factures: { lib: "Nouvelle facture", texte: "facture ", primaire: true },
    impayes: null,
    clients: { lib: "Ajouter un client", texte: "ajoute " },
    produits: { lib: "Ajouter un produit", texte: "ajoute " }
  };

  /* ---------- outils ---------- */
  function valide(liste, id, defaut) {
    for (var i = 0; i < liste.length; i++) if (liste[i].id === id) return id;
    return defaut;
  }
  function norm(s) { return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim(); }
  function pluriel(n, un, plusieurs) { return n + " " + (n > 1 ? plusieurs : un); }
  function lien(ecran, params) { return e(MK.lien(ecran, params)); }
  function telephone(t) {
    var c = String(t || "").replace(/\D/g, "");
    if (/^237\d{9}$/.test(c)) return "+237 " + c.slice(3, 6) + " " + c.slice(6, 8) + " " + c.slice(8, 10) + " " + c.slice(10, 12);
    return t ? String(t) : "";
  }
  function retard(n) { return (n > 0 ? n + " j de retard" : "En retard"); }
  function etatFacture(f) {
    if (f.statut === "payee") return MK.pastille("Payée", "ok");
    if (f.statut === "en_retard") return MK.pastille(retard(f.jours_retard), "urgent");
    return MK.pastille("Envoyée", "info");
  }
  function dernierAchat(c) { return c.dernier_achat ? "Dernier achat " + MK.fmt.relatif(c.dernier_achat) : "Aucun achat"; }

  /* Un bouton d'action posé dans un conteneur : le texte est écrit par nous, jamais par l'API. */
  function vide(o) {
    var d = document.createElement("div");
    d.innerHTML = MK.etatVide({ icone: o.icone || "suivi", titre: o.titre, texte: o.texte });
    var boite = d.firstChild;
    if (o.action) {
      var r = document.createElement("div");
      r.className = "rangee";
      var b = document.createElement("button");
      b.type = "button";
      b.className = "btn " + (o.action.primaire ? "primaire" : "secondaire");
      b.textContent = o.action.libelle;
      b.addEventListener("click", o.action.onclick);
      r.appendChild(b);
      boite.appendChild(r);
    }
    return boite;
  }

  /* ---------- gabarits : une liste en cartes (téléphone) et un tableau (à partir de 720 px) ---------- */
  function carte(o) {
    return '<li class="sui-carte' + (o.lien ? " clic" : "") + (o.alerte ? " alerte" : "") + '">' +
      '<div class="sui-haut">' + (o.lien ? '<a class="sui-lien sui-nom" href="' + o.lien + '">' + e(o.nom) + "</a>" : '<span class="sui-nom">' + e(o.nom) + "</span>") +
      (o.montant ? '<span class="sui-montant montant' + (o.negatif ? " negatif" : "") + '">' + o.montant + "</span>" : "") + "</div>" +
      '<div class="sui-bas"><span class="sui-sous">' + o.sous + "</span>" + (o.fin || "") + "</div></li>";
  }
  function cartes(lignes) { return '<ul class="sui-cartes">' + lignes.join("") + "</ul>"; }
  function tableau(legende, colonnes, lignes) {
    return '<div class="table-cadre sui-table-cadre"><table class="table sui-table"><caption class="sr-only">' + e(legende) + "</caption><thead><tr>" +
      colonnes.map(function (c) { return '<th scope="col"' + (c.droite ? ' class="droite"' : "") + ">" + e(c.lib) + "</th>"; }).join("") +
      "</tr></thead><tbody>" + lignes.join("") + "</tbody></table></div>";
  }
  function vues(htmlCartes, htmlTable) {
    return '<div class="sui-vue-cartes">' + htmlCartes + '</div><div class="sui-vue-table">' + htmlTable + "</div>";
  }

  /* ---------- Factures ---------- */
  function listeFactures(factures, etat) {
    var l = factures.filter(function (f) { return etat === "tout" || f.statut === etat; })
      .sort(function (a, b) { return String(b.date).localeCompare(String(a.date)) || b.id - a.id; });
    var c = l.map(function (f) {
      var ech = f.statut !== "payee" && f.echeance ? " · échéance " + MK.fmt.date(f.echeance) : "";
      return carte({
        nom: f.client, lien: lien("facture", { id: f.id }), montant: MK.fmt.fcfa(f.total), alerte: f.statut === "en_retard",
        sous: "N° " + e(f.numero) + " · " + e(MK.fmt.date(f.date)) + e(ech), fin: etatFacture(f)
      });
    });
    var t = l.map(function (f) {
      return '<tr class="sui-clic"><td class="tabulaire">' + e(f.numero) + '</td><th scope="row"><a class="sui-lien" href="' + lien("facture", { id: f.id }) + '">' + e(f.client) + "</a></th>" +
        "<td>" + e(MK.fmt.date(f.date)) + "</td><td>" + (f.echeance ? e(MK.fmt.date(f.echeance)) : "—") + '</td><td class="droite montant sui-montant">' + MK.fmt.fcfa(f.total) + "</td><td>" + etatFacture(f) + "</td></tr>";
    });
    return {
      n: l.length,
      html: vues(cartes(c), tableau("Factures", [{ lib: "N°" }, { lib: "Client" }, { lib: "Émise le" }, { lib: "Échéance" }, { lib: "Montant", droite: true }, { lib: "État" }], t))
    };
  }

  /* ---------- Impayés : les clients qui doivent, avec le retard de leurs factures ---------- */
  function calculerImpayes(clients, factures) {
    var par = {};
    (factures || []).forEach(function (f) {
      if (f.statut === "payee") return;
      var o = par[f.client_id] || (par[f.client_id] = { nums: [], retard: 0, enRetard: false });
      o.nums.push(f.numero);
      if (f.statut === "en_retard") { o.enRetard = true; o.retard = Math.max(o.retard, f.jours_retard || 0); }
    });
    return clients.filter(function (c) { return c.dette > 0; }).map(function (c) {
      var o = par[c.id] || { nums: [], retard: 0, enRetard: false };
      var detail;
      if (!factures) detail = "Somme à encaisser";
      else if (!o.nums.length) detail = "Vente à crédit";
      else if (o.nums.length === 1) detail = "Facture n° " + o.nums[0];
      else if (o.nums.length === 2) detail = "Factures n° " + o.nums[0] + " et n° " + o.nums[1];
      else detail = o.nums.length + " factures";
      var etat = o.enRetard ? MK.pastille(retard(o.retard), "urgent") : (factures ? MK.pastille(o.nums.length ? "Pas encore échu" : "À crédit", "neutre") : "");
      return { id: c.id, nom: c.nom, dette: c.dette, retard: o.retard, enRetard: o.enRetard, detail: detail, etat: etat, dernier: c.dernier_achat };
    }).sort(function (a, b) { return b.dette - a.dette || b.retard - a.retard || a.nom.localeCompare(b.nom, "fr"); });
  }

  function bouton(i, nom) {
    return '<button type="button" class="btn secondaire petit sui-relancer" data-relancer="' + i + '" aria-label="Relancer ' + e(nom) + '">Relancer</button>';
  }

  function vueImpayes(lignes) {
    var total = lignes.reduce(function (s, l) { return s + l.dette; }, 0);
    var tard = lignes.filter(function (l) { return l.enRetard; });
    var totalTard = tard.reduce(function (s, l) { return s + l.dette; }, 0);
    var kpis = '<div class="grille c2 sui-kpis">' +
      '<div class="kpi plein"><div class="kpi-valeur">' + MK.fmt.fcfa(total) + '</div><div class="kpi-libelle">À encaisser</div><div class="kpi-note">' + pluriel(lignes.length, "client te doit", "clients te doivent") + " de l'argent</div></div>" +
      '<div class="kpi"><div class="kpi-valeur' + (tard.length ? " negatif" : "") + '">' + MK.fmt.fcfa(totalTard) + '</div><div class="kpi-libelle">En retard</div><div class="kpi-note">' + (tard.length ? pluriel(tard.length, "client", "clients") + " à relancer en priorité" : "Aucune facture en retard") + "</div></div></div>";
    // Dans les cartes, le bouton prend sa propre ligne sous le détail.
    var c = lignes.map(function (l, i) {
      return carte({ nom: l.nom, lien: lien("client", { id: l.id }), montant: MK.fmt.fcfa(l.dette), negatif: true, alerte: l.enRetard, sous: e(l.detail) })
        .replace(/<\/li>$/, '<div class="sui-pied">' + (l.etat || "<span></span>") + bouton(i, l.nom) + "</div></li>");
    });
    var t = lignes.map(function (l, i) {
      return '<tr class="sui-clic"><th scope="row"><a class="sui-lien" href="' + lien("client", { id: l.id }) + '">' + e(l.nom) + "</a></th><td>" + e(l.detail) + "</td><td>" + (l.etat || "—") +
        '</td><td class="droite montant sui-montant negatif">' + MK.fmt.fcfa(l.dette) + '</td><td class="droite">' + bouton(i, l.nom) + "</td></tr>";
    });
    return kpis + '<h2 class="sui-titre">Qui te doit de l\'argent</h2>' +
      vues(cartes(c), tableau("Clients qui te doivent de l'argent", [{ lib: "Client" }, { lib: "Détail" }, { lib: "Retard" }, { lib: "Il te doit", droite: true }, { lib: "Action", droite: true }], t));
  }

  /* ---------- Clients ---------- */
  function listeClients(clients, q) {
    var nq = norm(q);
    var l = clients.filter(function (c) { return !nq || norm(c.nom + " " + (c.quartier || "") + " " + (c.telephone || "")).indexOf(nq) >= 0; })
      .sort(function (a, b) { return b.dette - a.dette || String(b.dernier_achat || "").localeCompare(String(a.dernier_achat || "")) || a.nom.localeCompare(b.nom, "fr"); });
    var c = l.map(function (x) {
      return carte({
        nom: x.nom, lien: lien("client", { id: x.id }), montant: x.dette > 0 ? "Doit " + MK.fmt.fcfa(x.dette) : "", negatif: true,
        sous: e((x.quartier ? x.quartier + " · " : "") + dernierAchat(x)), fin: x.inactif ? MK.pastille("Inactif", "attention") : ""
      });
    });
    var t = l.map(function (x) {
      return '<tr class="sui-clic"><th scope="row"><a class="sui-lien" href="' + lien("client", { id: x.id }) + '">' + e(x.nom) + "</a>" + (x.quartier ? '<span class="sui-sous2">' + e(x.quartier) + "</span>" : "") + "</th>" +
        "<td>" + (x.telephone ? e(telephone(x.telephone)) : "—") + "</td><td>" + e(x.dernier_achat ? MK.fmt.relatif(x.dernier_achat) : "—") + (x.inactif ? " " + MK.pastille("Inactif", "attention") : "") + "</td>" +
        '<td class="droite montant sui-montant">' + MK.fmt.fcfa(x.total_achats) + '</td><td class="droite montant sui-montant' + (x.dette > 0 ? " negatif" : "") + '">' + (x.dette > 0 ? MK.fmt.fcfa(x.dette) : "—") + "</td></tr>";
    });
    return {
      n: l.length,
      html: vues(cartes(c), tableau("Clients", [{ lib: "Client" }, { lib: "Téléphone" }, { lib: "Dernier achat" }, { lib: "Total acheté", droite: true }, { lib: "Dette", droite: true }], t))
    };
  }

  /* ---------- Produits ---------- */
  function vueProduits(produits) {
    var l = produits.slice().sort(function (a, b) { return b.ca_30j - a.ca_30j || a.nom.localeCompare(b.nom, "fr"); });
    var c = l.map(function (p) {
      return carte({
        nom: p.nom, montant: MK.fmt.fcfa(p.prix),
        sous: p.ventes_30j > 0 ? e(p.ventes_30j + " vendus en 30 j") : "Aucune vente en 30 j",
        fin: p.ventes_30j > 0 ? '<span class="sui-montant montant">' + MK.fmt.fcfa(p.ca_30j) + "</span>" : ""
      });
    });
    var t = l.map(function (p) {
      return '<tr><th scope="row">' + e(p.nom) + '</th><td class="droite montant sui-montant">' + MK.fmt.fcfa(p.prix) + '</td><td class="droite montant">' + e(p.ventes_30j) + '</td><td class="droite montant sui-montant">' + (p.ventes_30j > 0 ? MK.fmt.fcfa(p.ca_30j) : "—") + "</td></tr>";
    });
    return vues(cartes(c), tableau("Produits", [{ lib: "Produit" }, { lib: "Prix", droite: true }, { lib: "Vendus (30 j)", droite: true }, { lib: "Chiffre d'affaires (30 j)", droite: true }], t));
  }

  /* ---------- l'écran ---------- */
  MK.ecran("suivi", {
    titre: "Suivi",
    onglet: "suivi",
    rendre: function (el, params) {
      var S = { segment: valide(SEGMENTS, params.segment, "factures"), etat: valide(ETATS, params.etat, "tout"), q: "", p: {}, d: {}, jeton: 0, vivant: true };
      var impayes = [];

      el.innerHTML =
        '<div class="entete-ecran"><div><h1>Suivi</h1></div><div class="sui-action" data-action></div></div>' +
        '<div class="sui-segments"><div class="segment plein sui-seg" role="group" aria-label="Rubrique du suivi">' +
        SEGMENTS.map(function (s) { return '<button type="button" data-seg="' + s.id + '" aria-pressed="false"><span>' + e(s.lib) + '</span><span class="sui-n" data-n="' + s.id + '" hidden></span></button>'; }).join("") +
        '</div></div><div class="sui-zone" data-zone></div>';
      var zone = el.querySelector("[data-zone]");
      var zoneAction = el.querySelector("[data-action]");

      function ecrireHash() {
        var h = MK.lien("suivi", { segment: S.segment, etat: S.segment === "factures" && S.etat !== "tout" ? S.etat : "" });
        if (location.hash !== h) history.replaceState(null, "", location.pathname + location.search + h);
      }

      /* ----- données, chargées à la demande et gardées le temps de la visite ----- */
      function charger(cle, force) {
        if (!force && S.p[cle]) return S.p[cle];
        var p = MK.api(URLS[cle]).then(function (r) { S.d[cle] = (r && r[cle]) || []; return S.d[cle]; });
        S.p[cle] = p;
        p.catch(function () { if (S.p[cle] === p) delete S.p[cle]; });
        return p;
      }
      function pour(segment, force) {
        if (segment === "impayes") return Promise.all([charger("clients", force), charger("factures", force).catch(function () { return null; })]);
        return charger(segment, force);
      }

      function majCompteurs() {
        var n = {};
        if (S.d.factures) n.factures = S.d.factures.length;
        if (S.d.clients) { n.clients = S.d.clients.length; n.impayes = calculerImpayes(S.d.clients, S.d.factures || null).length; }
        if (S.d.produits) n.produits = S.d.produits.length;
        SEGMENTS.forEach(function (s) {
          var b = el.querySelector('[data-n="' + s.id + '"]');
          if (!b) return;
          b.hidden = n[s.id] === undefined;
          if (n[s.id] !== undefined) b.textContent = n[s.id];
        });
      }

      function majSegments() {
        el.querySelectorAll("[data-seg]").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-seg") === S.segment ? "true" : "false"); });
        var a = ACTIONS[S.segment];
        zoneAction.textContent = "";
        if (a) {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "btn " + (a.primaire ? "primaire" : "secondaire") + " petit";
          b.textContent = a.lib;
          b.addEventListener("click", function () { MK.amorcerAssistant(a.texte); });
          zoneAction.appendChild(b);
        }
      }

      /* ----- affichage d'un segment ----- */
      function afficher(force) {
        var mon = ++S.jeton;
        var segment = S.segment;
        majSegments();
        ecrireHash();
        zone.setAttribute("aria-busy", "true");
        zone.innerHTML = MK.squelette(5);
        pour(segment, force).then(function () {
          if (!S.vivant || mon !== S.jeton) return;
          zone.removeAttribute("aria-busy");
          majCompteurs();
          zone.textContent = "";
          ({ factures: montrerFactures, impayes: montrerImpayes, clients: montrerClients, produits: montrerProduits })[segment]();
          // Les compteurs des autres rubriques se remplissent en silence.
          ["factures", "clients", "produits"].forEach(function (cle) {
            if (!S.p[cle]) charger(cle).then(function () { if (S.vivant) majCompteurs(); }, function () { /* compteur laissé vide */ });
          });
        }, function (err) {
          if (!S.vivant || mon !== S.jeton) return;
          zone.removeAttribute("aria-busy");
          zone.textContent = "";
          zone.appendChild(MK.etatErreur(err, function () { afficher(true); }));
        });
      }

      function montrerFactures() {
        var factures = S.d.factures;
        if (!factures.length) {
          zone.appendChild(vide({
            titre: "Aucune facture pour l'instant", texte: "Dis à Moki quoi facturer et à qui. La facture ne part qu'après ta confirmation.",
            action: { libelle: "Faire une facture", primaire: true, onclick: function () { MK.amorcerAssistant("facture "); } }
          }));
          return;
        }
        var cpt = { tout: factures.length };
        factures.forEach(function (f) { cpt[f.statut] = (cpt[f.statut] || 0) + 1; });
        var barre = document.createElement("div");
        barre.className = "sui-barre";
        barre.innerHTML = '<div class="puces sui-filtres" role="group" aria-label="Filtrer les factures par état">' +
          ETATS.map(function (x) { return '<button type="button" class="puce" data-etat="' + x.id + '" aria-pressed="false">' + e(x.lib) + " · " + (cpt[x.id] || 0) + "</button>"; }).join("") + "</div>" +
          '<p class="sui-resume" role="status" aria-live="polite" data-resume></p>';
        var res = document.createElement("div");
        zone.appendChild(barre);
        zone.appendChild(res);

        var libelles = { tout: ["facture", "factures"], envoyee: ["facture envoyée", "factures envoyées"], payee: ["facture payée", "factures payées"], en_retard: ["facture en retard", "factures en retard"] };
        function dessiner() {
          barre.querySelectorAll("[data-etat]").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-etat") === S.etat ? "true" : "false"); });
          var r = listeFactures(factures, S.etat);
          barre.querySelector("[data-resume]").textContent = r.n + " " + libelles[S.etat][r.n > 1 ? 1 : 0];
          res.textContent = "";
          if (r.n) { res.innerHTML = r.html; return; }
          var msg = {
            envoyee: ["Aucune facture en attente", "Toutes tes factures envoyées ont été payées ou sont en retard."],
            payee: ["Aucune facture payée pour l'instant", "Les paiements reçus apparaîtront ici."],
            en_retard: ["Aucune facture en retard", "Tout est à jour : personne n'a dépassé son échéance."]
          }[S.etat];
          res.appendChild(vide({
            icone: "recherche", titre: msg[0], texte: msg[1],
            action: { libelle: "Voir toutes les factures", onclick: function () { S.etat = "tout"; ecrireHash(); dessiner(); } }
          }));
        }
        barre.addEventListener("click", function (ev) {
          var b = ev.target.closest("[data-etat]");
          if (!b) return;
          S.etat = b.getAttribute("data-etat");
          ecrireHash();
          dessiner();
        });
        dessiner();
      }

      function montrerImpayes() {
        impayes = calculerImpayes(S.d.clients, S.d.factures || null);
        if (!impayes.length) {
          zone.appendChild(vide({
            titre: "Personne ne te doit d'argent", texte: "Tes factures sont payées et tes clients sont à jour. Si une vente part à crédit, elle apparaîtra ici.",
            action: { libelle: "Voir les factures", onclick: function () { S.segment = "factures"; afficher(); } }
          }));
          return;
        }
        zone.innerHTML = vueImpayes(impayes);
      }

      function montrerClients() {
        var clients = S.d.clients;
        if (!clients.length) {
          zone.appendChild(vide({
            titre: "Pas encore de client", texte: "Ils s'ajoutent à chaque vente à crédit ou facture. Tu peux aussi en ajouter un en l'écrivant à Moki.",
            action: { libelle: "Ajouter un client", primaire: true, onclick: function () { MK.amorcerAssistant("ajoute "); } }
          }));
          return;
        }
        var barre = document.createElement("div");
        barre.className = "sui-barre sui-barre-recherche";
        barre.innerHTML = '<label class="champ-recherche">' + MK.icone("recherche", { taille: 20 }) + '<span class="sr-only">Rechercher un client</span>' +
          '<input type="search" placeholder="Rechercher un client" autocomplete="off" value="' + e(S.q) + '"></label>' +
          '<p class="sui-resume" role="status" aria-live="polite" data-resume></p>';
        var res = document.createElement("div");
        zone.appendChild(barre);
        zone.appendChild(res);
        var champ = barre.querySelector("input");
        function dessiner() {
          var r = listeClients(clients, S.q);
          barre.querySelector("[data-resume]").textContent = S.q.trim() ? (r.n ? r.n + " sur " + clients.length + " clients" : "Aucun résultat") : pluriel(r.n, "client", "clients");
          res.textContent = "";
          if (r.n) { res.innerHTML = r.html; return; }
          res.appendChild(vide({
            icone: "recherche", titre: "Aucun client ne correspond", texte: "Vérifie l'orthographe. La recherche porte sur le nom, le quartier et le téléphone.",
            action: { libelle: "Effacer la recherche", onclick: function () { S.q = ""; champ.value = ""; dessiner(); champ.focus(); } }
          }));
        }
        champ.addEventListener("input", function () { S.q = champ.value; dessiner(); });
        dessiner();
      }

      function montrerProduits() {
        var produits = S.d.produits;
        if (!produits.length) {
          zone.appendChild(vide({
            titre: "Pas encore de produit", texte: "Chaque produit vendu apparaît ici avec son prix et ses ventes des 30 derniers jours.",
            action: { libelle: "Ajouter un produit", primaire: true, onclick: function () { MK.amorcerAssistant("ajoute "); } }
          }));
          return;
        }
        zone.innerHTML = '<p class="sui-resume">' + pluriel(produits.length, "produit", "produits") + " · ventes des 30 derniers jours</p>" + vueProduits(produits);
      }

      /* ----- événements ----- */
      el.querySelector(".sui-seg").addEventListener("click", function (ev) {
        var b = ev.target.closest("[data-seg]");
        if (!b || b.getAttribute("data-seg") === S.segment) return;
        S.segment = b.getAttribute("data-seg");
        afficher();
      });
      zone.addEventListener("click", function (ev) {
        var b = ev.target.closest("[data-relancer]");
        if (!b) return;
        var l = impayes[Number(b.getAttribute("data-relancer"))];
        if (l) MK.amorcerAssistant("relance " + l.nom);
      });

      afficher();
      return function () { S.vivant = false; };
    }
  });
})();
