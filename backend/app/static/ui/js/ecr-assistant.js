/* Mon Kiosque : écran Assistant (Moki). Conversation, suggestions, OUI/NON, cartes PDF, dictée, notifications. */
(function () {
  "use strict";
  var MK = window.MK;

  /* Suggestions : les questions s'envoient d'un geste ; les exemples qui enregistrent ou annulent
     quelque chose préremplissent le champ pour que la gérante corrige les chiffres avant d'envoyer. */
  var SUGGESTIONS = [
    { t: "j'ai vendu 3 paires à 5000", envoi: false },
    { t: "j'ai payé 20 000 de loyer", envoi: false },
    { t: "j'ai fait combien aujourd'hui ?", envoi: true },
    { t: "mon bénéfice", envoi: true },
    { t: "qui me doit ?", envoi: true },
    { t: "mes factures", envoi: true },
    { t: "facture Lycée Technique, 30 repas à 2500", envoi: false },
    { t: "prépare mon dossier de crédit", envoi: true },
    { t: "mon impôt", envoi: true },
    { t: "annuler", envoi: false }
  ];
  var ACCUEIL = "Salut ! Je suis Moki, l'assistant de ta caisse. Écris-moi comme tu parles : une vente, une dépense, une question sur tes chiffres.";
  var RE_MOT = /tape exactement le mot\s*:\s*([A-Za-zÀ-ÿ]+)/i;
  var RE_OUINON = /OUI\s*\/\s*NON\s*$/;
  var RE_RELANCE = /^([\s\S]*?Voici la relance pour (.+?) :)\s*\n\s*«\s*([\s\S]+?)\s*»([\s\S]*)$/;
  var RE_FACTURE = /^Voici (?:la facture pour (.+?)|ce que je prépare) :\s*\n([\s\S]+)$/;
  var RE_URL_SURE = /^(\/(?!\/)|https?:\/\/|blob:|data:application\/pdf)/i;
  var DELAI_SONDAGE = 8000;
  var PAUSE_ENTRE_BULLES = 350;

  /* Conversation conservée pendant la session (changer d'onglet ne la perd pas). */
  var conv = null;
  var ui = null; // références DOM de l'écran monté, null sinon

  function nouvelleConv() {
    return {
      jeton: MK.etat.token,
      msgs: [{ type: "texte", qui: "moki", texte: ACCUEIL, date: new Date().toISOString(), local: true }],
      occupe: false,
      curseur: null,
      brouillon: ""
    };
  }

  function reduireMouvement() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function el(tag, classe, texte) {
    var n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texte !== undefined && texte !== null) n.textContent = texte;
    return n;
  }

  /* ---------- contenu des bulles ---------- */
  function lignes(parent, texte, gras) {
    String(texte || "").split("\n").forEach(function (l) {
      var p = el("span", "ass-l");
      if (!l.trim()) p.className = "ass-l vide";
      else if (gras && /^Total\b/i.test(l.trim())) { var s = el("strong", "", l); p.appendChild(s); }
      else p.textContent = l;
      parent.appendChild(p);
    });
  }

  function carteFacture(parent, client, items, total) {
    var c = el("div", "ass-recap");
    c.appendChild(el("div", "ass-recap-titre", client ? "Facture pour " + client : "Facture"));
    var corps = el("ul", "ass-recap-lignes");
    items.forEach(function (it) { corps.appendChild(el("li", "", it)); });
    c.appendChild(corps);
    var m = /^Total\s*:?\s*(.+)$/i.exec(total);
    var pied = el("div", "ass-recap-total");
    pied.appendChild(el("span", "", "Total"));
    pied.appendChild(el("strong", "montant", m ? m[1] : total));
    c.appendChild(pied);
    parent.appendChild(c);
  }

  function apercuClient(parent, client, message) {
    var a = el("div", "ass-apercu");
    a.appendChild(el("div", "ass-apercu-lib", "Ce que recevra " + client));
    var b = el("div", "ass-apercu-bulle");
    lignes(b, message);
    a.appendChild(b);
    parent.appendChild(a);
  }

  /* Remplit une bulle de Moki : récapitulatif de facture et aperçu de relance si reconnus, sinon texte simple. */
  function contenuMoki(box, brut) {
    var texte = String(brut || "").replace(RE_OUINON, "").trim();
    var m = RE_RELANCE.exec(texte);
    if (m) {
      lignes(box, m[1]);
      apercuClient(box, m[2], m[3]);
      if (m[4].trim()) lignes(box, m[4].trim());
      return;
    }
    m = RE_FACTURE.exec(texte);
    if (m) {
      var corps = m[2].split("\n").map(function (x) { return x.trim(); }).filter(Boolean);
      var iTotal = -1;
      corps.forEach(function (l, i) { if (iTotal < 0 && /^Total\b/i.test(l)) iTotal = i; });
      if (iTotal > 0) {
        var client = m[1] || "";
        var items = corps.slice(0, iTotal);
        var f = /^Facture pour (.+)$/i.exec(items[0]);
        if (f) { client = f[1]; items.shift(); }
        if (items.length) {
          carteFacture(box, client, items, corps[iTotal]);
          var suite = corps.slice(iTotal + 1).join("\n");
          if (suite) lignes(box, suite);
          return;
        }
      }
    }
    lignes(box, texte, true);
  }

  function noeudMessage(msg, animer) {
    var cls = "ass-msg " + (msg.qui === "moi" ? "moi" : "moki") + (animer ? " nouveau" : "");
    if (msg.type === "doc") {
      var d = el("div", cls);
      msg.documents.forEach(function (doc) { d.appendChild(carteDocument(doc)); });
      return d;
    }
    if (msg.type === "frappe") {
      var fr = el("div", "ass-msg moki nouveau ass-frappe");
      fr.setAttribute("role", "status");
      var pts = el("span", "ass-points");
      pts.setAttribute("aria-hidden", "true");
      pts.innerHTML = "<i></i><i></i><i></i>";
      fr.appendChild(pts);
      fr.appendChild(el("span", "", "Moki réfléchit…"));
      return fr;
    }
    var wrap = el("div", cls);
    var bulle = el("div", "ass-bulle" + (msg.erreur ? " erreur" : ""));
    if (msg.qui === "moki" && !msg.erreur) contenuMoki(bulle, msg.texte);
    else lignes(bulle, msg.texte);
    if (msg.erreur && msg.reessayer) {
      var b = el("button", "btn secondaire petit ass-reessayer", "Réessayer");
      b.type = "button";
      b.setAttribute("data-reessayer", msg.reessayer);
      bulle.appendChild(b);
    }
    bulle.appendChild(el("time", "ass-heure", MK.fmt.heure(msg.date)));
    wrap.appendChild(bulle);
    return wrap;
  }

  function carteDocument(doc) {
    var nom = String((doc && doc.nom) || "Document");
    var url = String((doc && doc.url) || "");
    var c = el("div", "ass-doc");
    var ico = el("span", "ass-doc-ico");
    ico.innerHTML = MK.icone("modeles", { taille: 24 });
    var txt = el("div", "ass-doc-txt");
    txt.appendChild(el("b", "", nom));
    txt.appendChild(el("span", "", "Document PDF"));
    c.appendChild(ico);
    c.appendChild(txt);
    if (RE_URL_SURE.test(url)) {
      var a = el("a", "btn secondaire petit", "Ouvrir");
      a.href = url;
      a.target = "_blank";
      a.rel = "noopener";
      a.setAttribute("aria-label", "Ouvrir " + nom);
      c.appendChild(a);
    }
    return c;
  }

  /* ---------- actions rapides sous la dernière réponse ---------- */
  function actionEnAttente() {
    var i = conv.msgs.length - 1;
    while (i >= 0 && conv.msgs[i].type === "doc") i--;
    var dernier = i >= 0 ? conv.msgs[i] : null;
    if (!dernier || dernier.type !== "texte" || dernier.qui !== "moki" || dernier.erreur || dernier.local) return null;
    if (i !== conv.msgs.length - 1 && conv.msgs[conv.msgs.length - 1].type !== "doc") return null;
    var mot = RE_MOT.exec(dernier.texte);
    if (mot) return { mot: mot[1] };
    if (RE_OUINON.test(String(dernier.texte).trim())) return { ouinon: true };
    return null;
  }

  function majActions() {
    if (!ui) return;
    var z = ui.actions;
    z.textContent = "";
    var a = actionEnAttente();
    if (!a) { z.hidden = true; return; }
    z.hidden = false;
    if (a.mot) {
      var m = el("button", "btn primaire ass-act", a.mot);
      m.type = "button";
      m.setAttribute("data-r", a.mot);
      m.setAttribute("aria-label", "Confirmer en envoyant le mot " + a.mot);
      z.appendChild(el("span", "ass-act-aide", "Touche le mot pour confirmer, ou refuse :"));
      var rangee = el("div", "ass-act-rangee");
      rangee.appendChild(m);
      var n1 = el("button", "btn secondaire ass-act", "NON");
      n1.type = "button";
      n1.setAttribute("data-r", "non");
      rangee.appendChild(n1);
      z.appendChild(rangee);
    } else {
      var r2 = el("div", "ass-act-rangee");
      var o = el("button", "btn primaire ass-act", "OUI");
      o.type = "button";
      o.setAttribute("data-r", "oui");
      var n2 = el("button", "btn secondaire ass-act", "NON");
      n2.type = "button";
      n2.setAttribute("data-r", "non");
      r2.appendChild(o);
      r2.appendChild(n2);
      z.appendChild(r2);
    }
    z.querySelectorAll("button").forEach(function (b) { b.disabled = conv.occupe; });
  }

  function majSuggestions() {
    if (!ui) return;
    ui.puces.querySelectorAll("button").forEach(function (b) { b.disabled = conv.occupe; });
    ui.envoyer.disabled = conv.occupe;
    ui.envoyer.setAttribute("aria-busy", conv.occupe ? "true" : "false");
  }

  /* ---------- fil ---------- */
  function jourDe(iso) { return MK.fmt.dateLongue(iso); }

  function remplirFil() {
    ui.fil.textContent = "";
    var dernierJour = "";
    conv.msgs.forEach(function (m) {
      var j = jourDe(m.date);
      if (j && j !== dernierJour) { ui.fil.appendChild(el("div", "ass-jour", j)); dernierJour = j; }
      ui.fil.appendChild(noeudMessage(m, false));
    });
    majActions();
    majSuggestions();
    defiler(false);
  }

  function proche() { return ui.fil.scrollHeight - ui.fil.scrollTop - ui.fil.clientHeight < 140; }

  function defiler(doux) {
    if (!ui) return;
    var f = ui.fil;
    var fin = function () {
      if (doux && !reduireMouvement() && typeof f.scrollTo === "function") f.scrollTo({ top: f.scrollHeight, behavior: "smooth" });
      else f.scrollTop = f.scrollHeight;
    };
    fin();
    requestAnimationFrame(fin);
  }

  function ajouter(msg, forcerDefilement) {
    msg.date = msg.date || new Date().toISOString();
    var suivait = ui ? proche() : false;
    conv.msgs.push(msg);
    if (!ui) return;
    var dernier = conv.msgs.length > 1 ? conv.msgs[conv.msgs.length - 2] : null;
    var j = jourDe(msg.date);
    if (j && (!dernier || jourDe(dernier.date) !== j)) ui.fil.appendChild(el("div", "ass-jour", j));
    ui.fil.appendChild(noeudMessage(msg, true));
    majActions();
    if (forcerDefilement || suivait) defiler(true);
  }

  function pause(ms) { return new Promise(function (ok) { setTimeout(ok, ms); }); }

  /* ---------- envoi ---------- */
  function retirerFrappe() {
    if (ui) { var f = ui.fil.querySelector(".ass-frappe"); if (f) f.remove(); }
  }
  function retirerErreurs(texte) {
    conv.msgs = conv.msgs.filter(function (m) { return !(m.erreur && m.reessayer === texte); });
    if (ui) remplirFil();
  }

  function envoyer(texte, sansBulle) {
    texte = String(texte || "").trim();
    if (!texte || conv.occupe) return Promise.resolve();
    conv.occupe = true;
    if (!sansBulle) ajouter({ type: "texte", qui: "moi", texte: texte }, true);
    else retirerErreurs(texte);
    conv.brouillon = "";
    if (ui) { ui.champ.value = ""; ajuster(); }
    majActions();
    majSuggestions();
    if (ui) { ui.fil.appendChild(noeudMessage({ type: "frappe" }, true)); defiler(true); }

    return MK.api("/api/chat", { texte: texte }).then(function (r) {
      retirerFrappe();
      r = r || {};
      if (r.pme && MK.etat) { MK.etat.pme = r.pme; }
      var reps = r.reponses || [];
      var docs = (r.documents || []).filter(function (d) { return d && d.url; });
      var suite = Promise.resolve();
      reps.forEach(function (t, i) {
        suite = suite.then(function () { return i ? pause(PAUSE_ENTRE_BULLES) : null; }).then(function () { ajouter({ type: "texte", qui: "moki", texte: t }, true); });
      });
      return suite.then(function () {
        if (docs.length) ajouter({ type: "doc", qui: "moki", documents: docs }, true);
        if (!reps.length && !docs.length) ajouter({ type: "texte", qui: "moki", texte: "Je n'ai rien à te répondre là-dessus. Reformule en d'autres mots." }, true);
      });
    }).catch(function (err) {
      retirerFrappe();
      if (err && err.status === 401) return; // MK.api a déjà renvoyé vers la connexion
      var msg = err && err.message ? err.message : "Impossible de joindre Moki.";
      ajouter({ type: "texte", qui: "moki", erreur: true, reessayer: texte, texte: msg + " Ton message n'a pas été traité." }, true);
    }).then(function () {
      conv.occupe = false;
      majActions();
      majSuggestions();
    });
  }

  /* ---------- notifications de Moki (résumé de 19 h, rappels) ---------- */
  var minuteur = null;
  function sonder() {
    if (!ui || conv.occupe || document.hidden) return;
    var jeton = conv.jeton;
    var chemin = "/api/notifications" + (conv.curseur === null ? "" : "?apres=" + conv.curseur);
    MK.api(chemin).then(function (r) {
      if (!conv || conv.jeton !== jeton || !r) return;
      (r.notifications || []).forEach(function (n) {
        if (n && n.texte) ajouter({ type: "texte", qui: "moki", texte: n.texte });
      });
      if (r.dernier !== undefined && r.dernier !== null) conv.curseur = r.dernier;
    }).catch(function () { /* réseau instable : on réessaiera au prochain passage */ });
  }

  /* ---------- champ de saisie ---------- */
  function ajuster() {
    if (!ui) return;
    var c = ui.champ;
    c.style.height = "auto";
    c.style.height = Math.min(c.scrollHeight, 132) + "px";
  }

  /* Hauteur disponible : suit le clavier mobile (visualViewport) et libère la barre d'onglets quand il s'ouvre. */
  function ajusterViewport() {
    if (!ui) return;
    var vv = window.visualViewport;
    var h = vv ? vv.height : window.innerHeight;
    var clavier = !!vv && window.innerHeight - vv.height > 140 && window.innerWidth < 900;
    document.body.classList.toggle("ass-clavier", clavier);
    ui.racine.style.setProperty("--ass-h", Math.round(h) + "px");
    var ent = document.getElementById("entete"), ecr = document.getElementById("ecran");
    if (ent && ecr) {
      var haut = ent.getBoundingClientRect().bottom + window.scrollY + (parseFloat(getComputedStyle(ecr).paddingTop) || 0);
      ui.racine.style.setProperty("--ass-top", Math.round(haut) + "px");
    }
    if (clavier) { window.scrollTo(0, 0); defiler(false); }
  }

  function initDictee(bouton, champ) {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return null;
    var rec = null;
    try { rec = new SR(); } catch (x) { return null; }
    rec.lang = "fr-FR";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    var actif = false;
    function etat(a) {
      actif = a;
      bouton.setAttribute("aria-pressed", a ? "true" : "false");
      bouton.classList.toggle("ecoute", a);
      bouton.textContent = a ? "Écoute…" : "Dicter";
    }
    rec.onresult = function (ev) {
      var t = ev.results[0] && ev.results[0][0] ? ev.results[0][0].transcript : "";
      if (t) { champ.value = t; ajuster(); envoyer(t); }
    };
    rec.onend = function () { etat(false); };
    rec.onerror = function (ev) {
      etat(false);
      MK.toast(ev && ev.error === "not-allowed" ? "Autorise le micro pour dicter ton message." : "Je n'ai pas pu t'entendre. Réessaie ou écris.", "info");
    };
    bouton.addEventListener("click", function () {
      if (actif) { try { rec.stop(); } catch (x) { /* déjà arrêté */ } return; }
      try { rec.start(); etat(true); } catch (x) { /* déjà démarré */ }
    });
    return { arreter: function () { try { rec.abort(); } catch (x) { /* rien */ } } };
  }

  /* ---------- amorce (MK.amorcerAssistant / MK.envoyerAssistant) ---------- */
  function appliquerAmorce() {
    var a = MK.prendreAmorce && MK.prendreAmorce();
    if (!a || !a.texte || !ui) return;
    if (a.envoyer) envoyer(a.texte);
    else {
      ui.champ.value = a.texte;
      conv.brouillon = a.texte;
      ajuster();
      ui.champ.focus();
    }
  }

  /* ---------- écran ---------- */
  MK.ecran("assistant", {
    titre: "Moki",
    onglet: "assistant",
    rendre: function (vue) {
      if (!conv || conv.jeton !== MK.etat.token) conv = nouvelleConv();

      vue.innerHTML =
        '<section class="ass" aria-label="Conversation avec Moki">' +
          '<header class="ass-tete">' +
            '<span class="ass-avatar" aria-hidden="true">' + MK.icone("assistant", { taille: 28, variante: "fonce" }) + "</span>" +
            '<div class="ass-tete-txt"><h1>Moki</h1><p>Assistant de ta caisse</p></div>' +
          "</header>" +
          '<div class="ass-fil" id="ass-fil" role="log" aria-live="polite" aria-relevant="additions" aria-label="Messages" tabindex="0"></div>' +
          '<div class="ass-actions" id="ass-actions" hidden></div>' +
          '<div class="ass-bas">' +
            '<div class="ass-puces" id="ass-puces" role="group" aria-label="Suggestions"></div>' +
            '<form class="ass-saisie" id="ass-form" autocomplete="off">' +
              '<label class="sr-only" for="ass-champ">Ton message pour Moki</label>' +
              '<textarea id="ass-champ" rows="1" maxlength="1000" placeholder="Écris à Moki…" enterkeyhint="send"></textarea>' +
              '<button type="button" class="btn discret ass-dicter" id="ass-dicter" aria-pressed="false" hidden>Dicter</button>' +
              '<button type="submit" class="btn primaire ass-envoyer" id="ass-envoyer">Envoyer</button>' +
            "</form>" +
          "</div>" +
        "</section>";

      ui = {
        racine: vue.querySelector(".ass"),
        fil: vue.querySelector("#ass-fil"),
        actions: vue.querySelector("#ass-actions"),
        puces: vue.querySelector("#ass-puces"),
        champ: vue.querySelector("#ass-champ"),
        envoyer: vue.querySelector("#ass-envoyer"),
        dicter: vue.querySelector("#ass-dicter")
      };
      var etat = ui;

      SUGGESTIONS.forEach(function (s, i) {
        var b = el("button", "ass-puce", s.t);
        b.type = "button";
        b.setAttribute("data-i", String(i));
        etat.puces.appendChild(b);
      });

      etat.champ.value = conv.brouillon;
      remplirFil();
      ajuster();
      ajusterViewport();
      requestAnimationFrame(ajusterViewport);

      var dictee = initDictee(etat.dicter, etat.champ);
      if (dictee) etat.dicter.hidden = false;

      vue.querySelector("#ass-form").addEventListener("submit", function (ev) {
        ev.preventDefault();
        envoyer(etat.champ.value);
        etat.champ.focus();
      });
      etat.champ.addEventListener("input", function () { conv.brouillon = etat.champ.value; ajuster(); });
      etat.champ.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); envoyer(etat.champ.value); }
      });
      etat.puces.addEventListener("click", function (ev) {
        var b = ev.target.closest("button[data-i]");
        if (!b) return;
        var s = SUGGESTIONS[Number(b.getAttribute("data-i"))];
        if (!s) return;
        if (s.envoi) envoyer(s.t);
        else { etat.champ.value = s.t; conv.brouillon = s.t; ajuster(); etat.champ.focus(); }
      });
      etat.actions.addEventListener("click", function (ev) {
        var b = ev.target.closest("button[data-r]");
        if (b) envoyer(b.getAttribute("data-r"));
      });
      etat.fil.addEventListener("click", function (ev) {
        var b = ev.target.closest("button[data-reessayer]");
        if (b) envoyer(b.getAttribute("data-reessayer"), true);
      });

      var surAmorce = function () { appliquerAmorce(); };
      window.addEventListener("mk:assistant", surAmorce);
      var vv = window.visualViewport;
      if (vv) vv.addEventListener("resize", ajusterViewport);
      window.addEventListener("resize", ajusterViewport);

      appliquerAmorce();
      sonder();
      minuteur = setInterval(sonder, DELAI_SONDAGE);

      return function () {
        clearInterval(minuteur);
        minuteur = null;
        window.removeEventListener("mk:assistant", surAmorce);
        window.removeEventListener("resize", ajusterViewport);
        if (vv) vv.removeEventListener("resize", ajusterViewport);
        document.body.classList.remove("ass-clavier");
        if (dictee) dictee.arreter();
        if (conv) conv.brouillon = etat.champ.value;
        if (ui === etat) ui = null;
      };
    }
  });
})();
