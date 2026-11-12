/* Mon Kiosque : fiche facture (route « facture », paramètre id). Données : GET /api/factures/{id}. */
(function () {
  "use strict";
  var MK = window.MK;
  var e = MK.echapper;
  var NBSP = " ";

  var STATUTS = {
    payee: { libelle: "Payée", type: "ok" },
    envoyee: { libelle: "Envoyée", type: "info" },
    en_retard: { libelle: "En retard", type: "urgent" }
  };
  var MODES = {
    transfert: "Transfert",
    direct: "Envoi direct"
  };

  function aDeLHeure(iso) { return String(iso || "").length > 10; }
  function dateHeure(iso) { return MK.fmt.date(iso) + (aDeLHeure(iso) ? " · " + MK.fmt.heure(iso) : ""); }

  /* 237677120045 -> +237 677 12 00 45 ; autre forme : telle quelle */
  function telephone(num) {
    var n = String(num || "").replace(/\D/g, "");
    if (/^237\d{9}$/.test(n)) return "+237" + NBSP + n.slice(3, 6) + NBSP + n.slice(6, 8) + NBSP + n.slice(8, 10) + NBSP + n.slice(10);
    return String(num || "");
  }

  function etatIntrouvable(el) {
    el.innerHTML = '<div class="vide page">' +
      '<div class="vide-ico">' + MK.icone("recherche", { taille: 26 }) + "</div>" +
      "<h1>Facture introuvable</h1>" +
      "<p>Cette facture n'existe pas ou plus. Elle a peut-être été annulée.</p>" +
      '<div class="rangee"><a class="btn primaire" href="#/suivi">Retour au suivi</a></div></div>';
  }

  /* ---------- frise d'état : Émise, Envoyée, relances, échéance dépassée, Payée ---------- */
  function etapes(f) {
    var liste = [
      { titre: "Facture émise", date: dateHeure(f.date), etat: "fait", tri: String(f.date || "") },
      { titre: "Envoyée à " + f.client, date: dateHeure(f.date), etat: "fait", tri: String(f.date || "") }
    ];
    var milieu = (f.relances || []).map(function (r) {
      return { titre: "Relance envoyée", date: dateHeure(r.date), note: MODES[r.mode] || r.mode, etat: "fait", tri: String(r.date || "") };
    });
    if (f.statut === "en_retard" && f.echeance) {
      milieu.push({ titre: "Échéance dépassée", date: MK.fmt.date(f.echeance), note: MK.fmt.jours(f.jours_retard) + " de retard", etat: "retard", tri: String(f.echeance) });
    }
    milieu.sort(function (a, b) { return a.tri < b.tri ? -1 : a.tri > b.tri ? 1 : 0; });
    liste = liste.concat(milieu);

    if (f.statut === "payee") {
      var ps = (f.paiements || []).slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; });
      var dernier = ps.length ? ps[ps.length - 1] : null;
      liste.push({ titre: "Payée", date: dernier ? dateHeure(dernier.date) : "", note: dernier ? dernier.source : "", etat: "fait" });
    } else {
      var attente = f.echeance ? "À régler avant le " + MK.fmt.date(f.echeance) : "Aucune échéance fixée";
      if (f.statut === "en_retard" && !f.echeance && f.jours_retard > 0) attente = MK.fmt.jours(f.jours_retard) + " de retard";
      liste.push({ titre: "En attente de paiement", date: attente, etat: "attente" });
    }
    return liste;
  }

  function frise(f) {
    var liste = etapes(f);
    var html = '<ol class="fac-frise">';
    liste.forEach(function (x, i) {
      var suivant = liste[i + 1];
      var relie = suivant && suivant.etat !== "attente" ? " relie" : "";
      html += '<li class="fac-pas ' + x.etat + relie + '"' + (x.etat === "attente" ? ' aria-current="step"' : "") + ">" +
        '<span class="fac-pt" aria-hidden="true"></span>' +
        '<div class="fac-pas-corps"><b>' + e(x.titre) + "</b>" +
        (x.date || x.note ? "<small>" + e(x.date) + (x.date && x.note ? " · " : "") + e(x.note || "") + "</small>" : "") + "</div></li>";
    });
    return html + "</ol>";
  }

  /* ---------- blocs ---------- */
  function blocDates(f) {
    var lignes = [];
    lignes.push(["Émise le", e(MK.fmt.dateLongue(f.date))]);
    if (f.echeance) {
      var rel = f.statut === "payee" ? "" : ' <span class="fac-rel">(' + e(MK.fmt.relatif(f.echeance)) + ")</span>";
      lignes.push(["Échéance", e(MK.fmt.dateLongue(f.echeance)) + rel]);
    } else {
      lignes.push(["Échéance", "Non précisée"]);
    }
    if (f.jours_retard > 0 && f.statut !== "payee") lignes.push(["Retard", '<span class="fac-retard">' + e(MK.fmt.jours(f.jours_retard)) + "</span>"]);
    if (f.statut === "payee" && f.paiements && f.paiements.length) {
      var d = f.paiements.slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; }).pop().date;
      lignes.push(["Payée le", e(MK.fmt.dateLongue(d))]);
    }
    return '<section class="carte fac-bloc fac-o1" aria-labelledby="fac-t-dates"><h2 class="carte-titre" id="fac-t-dates">Dates</h2><dl class="fac-kv">' +
      lignes.map(function (l) { return "<div><dt>" + e(l[0]) + "</dt><dd>" + l[1] + "</dd></div>"; }).join("") + "</dl></section>";
  }

  function blocFrise(f) {
    return '<section class="carte fac-bloc fac-o2" aria-labelledby="fac-t-frise"><h2 class="carte-titre" id="fac-t-frise">Où en est cette facture</h2>' + frise(f) + "</section>";
  }

  function blocLignes(f) {
    var corps = "";
    (f.lignes || []).forEach(function (l) {
      corps += "<tr><td class=\"fac-lib\">" + e(l.libelle) + '</td><td class="fac-qte" data-label="Quantité">' + e(l.quantite) + '</td><td class="fac-pu" data-label="Prix">' + e(MK.fmt.fcfa(l.prix_unitaire)) +
        '</td><td class="fac-mt montant">' + e(MK.fmt.fcfa(l.montant)) + "</td></tr>";
    });
    (f.frais || []).forEach(function (x) {
      corps += '<tr class="fac-frais"><td class="fac-lib"><span class="fac-tag">Frais</span> ' + e(x.libelle) + '</td><td class="fac-qte vide-cel"></td><td class="fac-pu vide-cel"></td><td class="fac-mt montant">' + e(MK.fmt.fcfa(x.montant)) + "</td></tr>";
    });
    return '<section class="carte fac-bloc fac-o3" aria-labelledby="fac-t-lignes"><h2 class="carte-titre" id="fac-t-lignes">Détail de la facture</h2>' +
      '<table class="fac-table"><thead><tr><th scope="col">Désignation</th><th scope="col" class="droite">Qté</th><th scope="col" class="droite">Prix</th><th scope="col" class="droite">Montant</th></tr></thead><tbody>' + corps + "</tbody>" +
      '<tfoot><tr><th scope="row" colspan="3">Total à payer</th><td class="fac-mt montant">' + e(MK.fmt.fcfa(f.total)) + "</td></tr></tfoot></table></section>";
  }

  function blocRelances(f) {
    var rel = f.relances || [];
    var corps;
    if (!rel.length) {
      corps = '<p class="fac-vide-txt">' + (f.statut === "payee" ? "Aucune relance n'a été nécessaire." : "Aucune relance envoyée pour l'instant.") + "</p>";
    } else {
      corps = '<ul class="fac-relances">' + rel.map(function (r) {
        return "<li><div class=\"fac-rel-tete\"><span class=\"gras\">" + e(dateHeure(r.date)) + "</span>" + MK.pastille(MODES[r.mode] || r.mode, "neutre") + "</div>" +
          '<blockquote class="fac-citation">' + e(r.texte) + "</blockquote></li>";
      }).join("") + "</ul>";
    }
    return '<section class="carte fac-bloc fac-o5" aria-labelledby="fac-t-rel"><h2 class="carte-titre" id="fac-t-rel">Relances envoyées</h2>' + corps + "</section>";
  }

  function blocPaiements(f) {
    var ps = f.paiements || [];
    var corps;
    if (!ps.length) {
      corps = '<p class="fac-vide-txt">Aucun paiement reçu pour l\'instant.</p>';
    } else {
      corps = '<ul class="liste fac-liste">' + ps.map(function (p) {
        return '<li class="ligne"><div class="ligne-corps"><span class="ligne-titre">' + e(p.source || "Paiement") + '</span><span class="ligne-sous">' + e(dateHeure(p.date)) + "</span></div>" +
          '<div class="ligne-fin positif">+' + e(MK.fmt.fcfa(p.montant)) + "</div></li>";
      }).join("") + "</ul>";
    }
    return '<section class="carte fac-bloc fac-o6" aria-labelledby="fac-t-pay"><h2 class="carte-titre" id="fac-t-pay">Paiements reçus</h2>' + corps + "</section>";
  }

  function blocMessage(f) {
    var pme = MK.etat && MK.etat.pme;
    var commerce = pme && pme.nom_commerce ? pme.nom_commerce : "Ton commerce";
    var texte = e(f.message_client || "").replace(/https?:\/\/[^\s]*[^\s.,;:!?)]/g, function (u) { return '<span class="fac-v">' + u + "</span>"; });
    return '<section class="carte fac-bloc fac-o4" aria-labelledby="fac-t-msg">' +
      '<h2 class="carte-titre" id="fac-t-msg">Ce que ton client voit</h2>' +
      '<div class="fac-tel">' +
        '<div class="fac-tel-barre"><span class="fac-av"><img src="/ui/img/logo.svg" width="26" height="26" alt=""></span>' +
          '<div><b>' + e(commerce) + "</b><small>Message WhatsApp</small></div></div>" +
        '<div class="fac-tel-fil"><span class="fac-jour">' + e(MK.fmt.dateLongue(f.date)) + "</span>" +
          '<div class="fac-bulle">' + texte + "</div>" +
          '<span class="fac-heure">' + e(MK.fmt.heure(f.date)) + "</span></div></div>" +
      '<div class="fac-lien">' +
        '<div class="fac-lien-tete"><span class="gras">Lien de paiement</span>' + (f.paiement_simule ? MK.pastille("Paiement simulé", "attention") : "") + "</div>" +
        '<div class="fac-lien-url"><code>' + e(f.lien_paiement) + '</code><button type="button" class="btn secondaire petit" data-copier>Copier</button></div>' +
        (f.paiement_simule ? '<p class="fac-lien-note">Ce lien est une simulation : il ne débite personne. Le vrai paiement par mobile money viendra plus tard.</p>' : "") +
      "</div></section>";
  }

  function entete(f) {
    var st = STATUTS[f.statut] || { libelle: f.statut, type: "neutre" };
    var libStatut = f.statut === "en_retard" && f.jours_retard > 0 ? st.libelle + " · " + MK.fmt.jours(f.jours_retard) : st.libelle;
    var payee = f.statut === "payee";
    var actions = "";
    actions += '<button type="button" class="btn primaire" data-relancer' + (payee ? ' disabled aria-describedby="fac-note"' : "") + ">Relancer ce client</button>";
    if (!payee) actions += '<button type="button" class="btn secondaire" data-payee>Marquer comme payée</button>';
    if (f.pdf_url) actions += '<a class="btn secondaire" data-pdf href="' + e(f.pdf_url) + '" target="_blank" rel="noopener">Ouvrir le PDF</a>';
    return '<header class="carte fac-tete">' +
      '<div class="fac-tete-g">' +
        '<div class="surtitre">Facture</div>' +
        '<div class="fac-titre"><h1>Facture n°' + NBSP + e(f.numero) + "</h1>" + MK.pastille(libStatut, st.type) + "</div>" +
        '<div class="fac-qui"><div><span class="fac-qui-lib">Client</span>' +
          '<a class="fac-client" href="' + e(MK.lien("client", { id: f.client_id })) + '">' + e(f.client) + "</a></div>" +
          (f.telephone ? '<div><span class="fac-qui-lib">Téléphone</span><a class="fac-tel-lien" href="tel:+' + e(String(f.telephone).replace(/\D/g, "")) + '">' + e(telephone(f.telephone)) + "</a></div>" : "") +
        "</div></div>" +
      '<div class="fac-tete-d"><span class="fac-total-lib">Total</span><span class="fac-total montant">' + e(MK.fmt.fcfa(f.total)) + "</span></div>" +
      '<div class="fac-actions">' + actions + "</div>" +
      (payee ? '<p class="fac-note" id="fac-note">Cette facture est payée : il n\'y a rien à relancer.</p>' : "") +
      "</header>";
  }

  /* Un PDF de démonstration est une URL data: que les navigateurs refusent d'ouvrir dans un nouvel onglet : on passe par un blob. */
  function ouvrirPdf(ev, lien) {
    var href = lien.getAttribute("href") || "";
    if (href.indexOf("data:") !== 0) return;
    ev.preventDefault();
    fetch(href).then(function (r) { return r.blob(); }).then(function (b) {
      window.open(URL.createObjectURL(b), "_blank", "noopener");
    }).catch(function () { MK.toast("Impossible d'ouvrir le PDF.", "erreur"); });
  }

  function brancher(el, f) {
    var r = el.querySelector("[data-relancer]");
    if (r && !r.disabled) r.addEventListener("click", function () { MK.amorcerAssistant("relance " + f.client); });
    var p = el.querySelector("[data-payee]");
    if (p) p.addEventListener("click", function () { MK.amorcerAssistant(f.client + " a payé"); });
    var pdf = el.querySelector("[data-pdf]");
    if (pdf) pdf.addEventListener("click", function (ev) { ouvrirPdf(ev, pdf); });
    var c = el.querySelector("[data-copier]");
    if (c) c.addEventListener("click", function () {
      var ok = function () { MK.toast("Lien copié.", "ok"); };
      var ko = function () { MK.toast("Copie impossible : sélectionne le lien à la main.", "info"); };
      try { navigator.clipboard.writeText(f.lien_paiement).then(ok, ko); } catch (x) { ko(); }
    });
  }

  function afficher(el, f) {
    el.innerHTML = '<article class="fac">' + entete(f) +
      '<div class="fac-grille">' +
        '<div class="fac-col">' + blocLignes(f) + blocRelances(f) + blocPaiements(f) + "</div>" +
        '<div class="fac-col">' + blocDates(f) + blocFrise(f) + blocMessage(f) + "</div>" +
      "</div></article>";
    brancher(el, f);
  }

  MK.ecran("facture", {
    titre: "Facture",
    onglet: "suivi",
    retour: "suivi",
    rendre: function (el, params) {
      var id = String((params && params.id) || "");
      if (!/^\d+$/.test(id)) { etatIntrouvable(el); return; }
      el.innerHTML = '<div class="fac-sq">' + MK.squelette(5) + "</div>";
      return MK.api("/api/factures/" + id).then(function (f) {
        afficher(el, f);
      }, function (err) {
        el.textContent = "";
        if (err && err.status === 404) etatIntrouvable(el);
        else el.appendChild(MK.etatErreur(err, MK.recharger));
      });
    }
  });
})();
