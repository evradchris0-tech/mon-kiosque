/* Mon Kiosque : écran Historique (route « historique », retour « reglages »).
   Données : GET /api/historique?type=&q=&limite=&avant= et GET /api/historique/{type}/{id}. Contrat : docs/06-interface-pro.md §4 et §5. */
(function () {
  "use strict";
  var MK = window.MK;
  if (!MK) return;
  var e = MK.echapper, f = MK.fmt;

  var LIMITE = 30;
  var FILTRES = [["tout", "Tout"], ["vente", "Ventes"], ["depense", "Dépenses"], ["facture", "Factures"], ["paiement", "Paiements"]];
  var TYPES = { vente: "Vente", depense: "Dépense", facture: "Facture", paiement: "Paiement" };
  var STATUTS = { annule: ["Annulé", "neutre"], en_attente: ["En attente", "attention"], retard: ["En retard", "urgent"] };

  function typeValide(t) { return FILTRES.some(function (x) { return x[0] === t; }); }

  /* Montant signé : entrée en vert, sortie en rouge, le reste (à recevoir) sans signe. */
  function montantSigne(el) {
    var m = Number(el.montant) || 0;
    if (el.sens === "entree") return { texte: "+" + f.fcfa(m), classe: "positif" };
    if (el.sens === "sortie") return { texte: "−" + f.fcfa(m), classe: "negatif" };
    return { texte: f.fcfa(m), classe: "his-neutre" };
  }

  function titreJour(iso) {
    var r = f.relatif(iso);
    if (r === "aujourd'hui") return "Aujourd'hui";
    if (r === "hier") return "Hier";
    var l = f.dateLongue(iso);
    return l ? l.charAt(0).toUpperCase() + l.slice(1) : "Date inconnue";
  }

  function pastilleStatut(el) {
    var s = STATUTS[el.statut];
    return s ? MK.pastille(s[0], s[1]) : "";
  }

  function ligneHtml(el) {
    var m = montantSigne(el);
    var annule = el.statut === "annule";
    var sous = f.heure(el.date) + " · " + (TYPES[el.type] || "Opération") + (el.client ? " · " + el.client : "");
    return '<li><button type="button" class="ligne cliquable double his-ligne' + (annule ? " his-annule" : "") + '" data-id="' + e(el.id) + '">' +
      '<span class="ligne-corps"><span class="ligne-titre his-titre">' + e(el.titre) + "</span>" +
      '<span class="ligne-sous">' + e(sous) + "</span>" +
      (el.detail ? '<span class="ligne-sous his-detail">' + e(el.detail) + "</span>" : "") + "</span>" +
      '<span class="ligne-fin"><span class="his-montant ' + m.classe + '">' + e(m.texte) + "</span>" + pastilleStatut(el) + "</span></button></li>";
  }

  /* ---------- détail dans une feuille ---------- */
  function detailHtml(d) {
    var el = d.element || {};
    var m = montantSigne(el);
    var lignes = Array.isArray(d.lignes) ? d.lignes : [];
    var notes = Array.isArray(d.notes) ? d.notes : [];
    var redondant = lignes.length === 1 && Number(lignes[0].quantite) === 1 && lignes[0].libelle === el.titre;
    var html = '<div class="his-det-tete"><div class="his-det-montant ' + m.classe + (el.statut === "annule" ? " his-annule" : "") + '">' + e(m.texte) + "</div>" + pastilleStatut(el) + "</div>" +
      '<dl class="his-kv">' +
      '<div><dt>Date</dt><dd>' + e(f.dateLongue(el.date)) + " à " + e(f.heure(el.date)) + "</dd></div>" +
      '<div><dt>Type</dt><dd>' + e(TYPES[el.type] || "Opération") + "</dd></div>" +
      (el.client ? '<div><dt>Client</dt><dd>' + e(el.client) + "</dd></div>" : "") + "</dl>";
    if (el.detail) html += '<p class="his-det-texte">' + e(el.detail) + "</p>";
    if (lignes.length && !redondant) {
      html += '<h3 class="his-det-titre">Détail</h3><ul class="his-lignes">';
      lignes.forEach(function (l) {
        html += "<li><span class=\"his-l-lib\">" + e(l.libelle) + '<span class="his-l-sous">' + e(String(l.quantite)) + " × " + e(f.fcfa(l.prix_unitaire)) + '</span></span><span class="his-l-val montant">' + e(f.fcfa(l.montant)) + "</span></li>";
      });
      html += '<li class="his-l-total"><span class="his-l-lib">Total</span><span class="his-l-val montant">' + e(f.fcfa(el.montant)) + "</span></li></ul>";
    }
    if (notes.length) {
      html += '<h3 class="his-det-titre">À savoir</h3><ul class="his-notes">' + notes.map(function (n) { return "<li>" + e(n) + "</li>"; }).join("") + "</ul>";
    }
    if (d.annulable) {
      html += '<div class="his-annuler"><p><b>Tu t\'es trompé ?</b> Pour annuler, dis « annuler » à Moki dans les 10 minutes.</p>' +
        '<button type="button" class="btn secondaire plein" data-annuler>Annuler avec Moki</button></div>';
    }
    return html;
  }

  function ouvrirDetail(el) {
    var parts = String(el.id || "").split("-");
    var feuille = MK.feuille({ titre: el.titre || "Détail", contenu: MK.squelette(3) });

    function charger() {
      feuille.corps.innerHTML = MK.squelette(3);
      MK.api("/api/historique/" + encodeURIComponent(el.type || parts[0]) + "/" + encodeURIComponent(parts[parts.length - 1])).then(function (d) {
        feuille.corps.innerHTML = detailHtml(d || {});
        var b = feuille.corps.querySelector("[data-annuler]");
        if (b) b.addEventListener("click", function () { feuille.fermer(); MK.amorcerAssistant("annuler"); });
      }, function (err) {
        feuille.corps.textContent = "";
        feuille.corps.appendChild(MK.etatErreur(err, charger));
      });
    }
    charger();
  }

  /* ---------- écran ---------- */
  MK.ecran("historique", {
    titre: "Historique",
    onglet: "reglages",
    retour: "reglages",
    rendre: function (el, params) {
      var type = typeValide(params && params.type) ? params.type : "tout";
      var q = "";
      var version = 0, vivant = true, minuteur = null, suivant = null, derniereCle = null, ul = null, index = {};

      el.innerHTML =
        '<div class="entete-ecran"><div><h1>Historique</h1><p class="sous">Tout ce que tu as noté : ventes, dépenses, factures et paiements, du plus récent au plus ancien.</p></div></div>' +
        '<div class="his-filtres"><div class="segment plein his-segment" role="group" aria-label="Type d\'opération">' +
        FILTRES.map(function (x) { return '<button type="button" data-type="' + x[0] + '" aria-pressed="' + (x[0] === type) + '">' + x[1] + "</button>"; }).join("") + "</div>" +
        '<label class="champ-recherche">' + MK.icone("recherche", { taille: 20 }) + '<span class="sr-only">Chercher dans l\'historique</span>' +
        '<input type="search" data-q placeholder="Chercher un client, un produit…" autocomplete="off" enterkeyhint="search"></label></div>' +
        '<p class="sr-only" role="status" data-statut></p><div class="his-zone" data-zone></div>';
      var zone = el.querySelector("[data-zone]");
      var statut = el.querySelector("[data-statut]");
      var champ = el.querySelector("[data-q]");
      var boutons = Array.prototype.slice.call(el.querySelectorAll("[data-type]"));

      function marquer() { boutons.forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-type") === type)); }); }

      function ajouter(elements) {
        var html = "";
        elements.forEach(function (x) {
          index[x.id] = x;
          var cle = f.dateLongue(x.date);
          if (cle !== derniereCle) {
            if (ul) { ul.insertAdjacentHTML("beforeend", html); html = ""; }
            var section = document.createElement("section");
            section.className = "his-jour";
            section.innerHTML = '<h2 class="his-jour-titre">' + e(titreJour(x.date)) + '</h2><ul class="liste his-liste"></ul>';
            zone.querySelector("[data-liste]").appendChild(section);
            ul = section.querySelector("ul");
            derniereCle = cle;
          }
          html += ligneHtml(x);
        });
        if (ul && html) ul.insertAdjacentHTML("beforeend", html);
      }

      function majPlus() {
        var pied = zone.querySelector("[data-plus]");
        if (!pied) return;
        pied.hidden = !suivant;
      }

      function vider() {
        suivant = null; derniereCle = null; ul = null; index = {};
      }

      function filtreActif() { return type !== "tout" || q.trim() !== ""; }

      function url(avant) {
        var p = ["type=" + encodeURIComponent(type), "limite=" + LIMITE];
        if (q.trim()) p.push("q=" + encodeURIComponent(q.trim()));
        if (avant) p.push("avant=" + encodeURIComponent(avant));
        return "/api/historique?" + p.join("&");
      }

      function afficherVide() {
        var d = document.createElement("div");
        if (filtreActif()) {
          d.innerHTML = MK.etatVide({ icone: "recherche", titre: "Aucune opération ne correspond", texte: q.trim() ? "Essaie un autre mot, ou retire un filtre." : "Il n'y a rien de ce type pour l'instant." });
          var b = document.createElement("button");
          b.type = "button"; b.className = "btn secondaire"; b.textContent = "Effacer les filtres";
          b.addEventListener("click", function () { type = "tout"; q = ""; champ.value = ""; marquer(); charger(); });
          d.querySelector(".vide").appendChild(b);
        } else {
          d.innerHTML = MK.etatVide({ icone: "historique", titre: "Rien dans l'historique pour l'instant", texte: "Dès que tu notes une vente ou une dépense avec Moki, elle apparaît ici.", action: { libelle: "Noter une vente avec Moki", ecran: "assistant" } });
        }
        zone.textContent = "";
        zone.appendChild(d.firstChild);
      }

      function charger() {
        var v = ++version;
        vider();
        zone.innerHTML = MK.squelette(6);
        statut.textContent = "Chargement de l'historique…";
        MK.api(url(null)).then(function (d) {
          if (!vivant || v !== version) return;
          var elements = (d && d.elements) || [];
          if (!elements.length) { afficherVide(); statut.textContent = "Aucune opération."; return; }
          zone.innerHTML = '<div data-liste></div><div class="his-plus" data-plus hidden><button type="button" class="btn secondaire" data-voirplus>Voir plus</button></div>';
          suivant = d.suivant || null;
          ajouter(elements);
          majPlus();
          statut.textContent = elements.length + (elements.length > 1 ? " opérations affichées." : " opération affichée.");
        }, function (err) {
          if (!vivant || v !== version) return;
          zone.textContent = "";
          zone.appendChild(MK.etatErreur(err, charger));
          statut.textContent = "L'historique n'a pas pu être chargé.";
        });
      }

      function voirPlus(bouton) {
        var v = version, avant = suivant;
        if (!avant) return;
        bouton.setAttribute("aria-busy", "true");
        MK.api(url(avant)).then(function (d) {
          if (!vivant || v !== version) return;
          bouton.removeAttribute("aria-busy");
          suivant = (d && d.suivant) || null;
          var elements = (d && d.elements) || [];
          ajouter(elements);
          majPlus();
          statut.textContent = elements.length + " opérations de plus affichées.";
        }, function (err) {
          if (!vivant || v !== version) return;
          bouton.removeAttribute("aria-busy");
          MK.toast(err && err.message ? err.message : "Impossible de charger la suite.", "erreur");
        });
      }

      boutons.forEach(function (b) {
        b.addEventListener("click", function () {
          var t = b.getAttribute("data-type");
          if (t === type) return;
          type = t; marquer(); charger();
        });
      });
      champ.addEventListener("input", function () {
        clearTimeout(minuteur);
        minuteur = setTimeout(function () { if (champ.value !== q) { q = champ.value; charger(); } }, 350);
      });
      champ.addEventListener("search", function () { clearTimeout(minuteur); if (champ.value !== q) { q = champ.value; charger(); } });

      zone.addEventListener("click", function (ev) {
        var plus = ev.target.closest("[data-voirplus]");
        if (plus) { voirPlus(plus); return; }
        var ligne = ev.target.closest("[data-id]");
        if (ligne && index[ligne.getAttribute("data-id")]) ouvrirDetail(index[ligne.getAttribute("data-id")]);
      });

      charger();
      return function () { vivant = false; clearTimeout(minuteur); };
    }
  });
})();
