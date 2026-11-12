/* Mon Kiosque : espace MK (api, état, routeur, outils, composants). Contrat : docs/06-interface-pro.md §3. */
(function () {
  "use strict";

  var Q = new URLSearchParams(location.search);
  var MK = (window.MK = {});
  var CLE_JETON = "moki_token";
  var NBSP = " "; // espace fine insécable

  MK.mock = Q.get("mock") === "1";
  MK.cas = Q.get("cas") || ""; // "vide" | "erreur" (mode mock)

  /* ---------- stockage (jamais bloquant) ---------- */
  MK.stockage = {
    lire: function (cle) { try { return localStorage.getItem(cle); } catch (e) { return null; } },
    ecrire: function (cle, valeur) {
      try { if (valeur === null || valeur === undefined) localStorage.removeItem(cle); else localStorage.setItem(cle, String(valeur)); } catch (e) { /* stockage indisponible */ }
    }
  };

  /* ---------- état ---------- */
  var jeton = MK.mock ? null : MK.stockage.lire(CLE_JETON);
  var pme = null;
  var nonLues = 0;
  function shell(nom, arg) { if (MK.shell && typeof MK.shell[nom] === "function") MK.shell[nom](arg); }

  MK.etat = { demo: false, numero: null };
  Object.defineProperties(MK.etat, {
    // Affecter le jeton le conserve (hors mode mock) ; l'effacer déconnecte sans rien d'autre.
    token: { enumerable: true, get: function () { return jeton; }, set: function (v) { jeton = v || null; if (!MK.mock) MK.stockage.ecrire(CLE_JETON, jeton); } },
    pme: { enumerable: true, get: function () { return pme; }, set: function (v) { pme = v || null; shell("commerce"); } },
    alertesNonLues: { enumerable: true, get: function () { return nonLues; }, set: function (v) { nonLues = Math.max(0, Number(v) || 0); shell("badge", nonLues); } }
  });

  /* Ouvre une session après /api/connexion : { token, numero, pme, demo } */
  MK.ouvrirSession = function (r) {
    r = r || {};
    MK.etat.token = r.token;
    MK.etat.numero = r.numero || null;
    MK.etat.demo = !!r.demo;
    MK.etat.pme = r.pme || null;
  };

  /* ---------- outils ---------- */
  function e(txt) {
    return String(txt === null || txt === undefined ? "" : txt).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }
  MK.echapper = e;

  MK.icone = function (nom, o) {
    o = o || {};
    var t = Number(o.taille) || 24;
    var v = o.variante === "fonce" ? "fonce" : "clair";
    var n = String(nom).replace(/[^a-z0-9-]/gi, "");
    return '<img class="ico' + (o.classe ? " " + e(o.classe) : "") + '" src="/ui/icones/vh-' + n + "-" + v + '.png" width="' + t + '" height="' + t + '" alt="" aria-hidden="true">';
  };

  function qs(params) {
    var p = [];
    Object.keys(params || {}).forEach(function (k) {
      if (params[k] !== undefined && params[k] !== null && params[k] !== "") p.push(encodeURIComponent(k) + "=" + encodeURIComponent(params[k]));
    });
    return p.length ? "?" + p.join("&") : "";
  }
  /* "#/id?cle=val" : à mettre dans un href (passer par echapper si on l'écrit dans du HTML) */
  MK.lien = function (id, params) { return "#/" + id + qs(params); };

  /* ---------- formats ---------- */
  var MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  var MOIS_LONGS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  var JOURS = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];

  /* Les dates arrivent en UTC naïf ; le Cameroun est à UTC+1 toute l'année. Les « date » (AAAA-MM-JJ) restent telles quelles. */
  function parties(iso) {
    if (!iso) return null;
    var s = String(iso), a, d;
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
      a = s.split("-").map(Number);
      return { a: a[0], m: a[1], j: a[2], h: 0, mi: 0, sem: new Date(Date.UTC(a[0], a[1] - 1, a[2])).getUTCDay() };
    }
    d = new Date(/(Z|[+-]\d{2}:?\d{2})$/i.test(s) ? s : s + "Z");
    if (isNaN(d.getTime())) return null;
    d = new Date(d.getTime() + 3600000);
    return { a: d.getUTCFullYear(), m: d.getUTCMonth() + 1, j: d.getUTCDate(), h: d.getUTCHours(), mi: d.getUTCMinutes(), sem: d.getUTCDay() };
  }
  function numJour(p) { return Math.floor(Date.UTC(p.a, p.m - 1, p.j) / 86400000); }
  function deuxChiffres(n) { return (n < 10 ? "0" : "") + n; }
  function groupe(n) { return String(Math.abs(Math.round(n))).replace(/\B(?=(\d{3})+(?!\d))/g, NBSP); }

  MK.fmt = {
    nombre: function (n) { n = Math.round(Number(n) || 0); return (n < 0 ? "−" : "") + groupe(n); },
    fcfa: function (n) { n = Math.round(Number(n) || 0); return (n < 0 ? "−" : "") + groupe(n) + NBSP + "F"; },
    fcfaCourt: function (n) {
      n = Math.round(Number(n) || 0);
      var signe = n < 0 ? "−" : "", v = Math.abs(n);
      function dec(x) { return String(Math.round(x * 10) / 10).replace(".", ","); }
      if (v >= 1000000) return signe + dec(v / 1000000) + NBSP + "M";
      if (v >= 10000) return signe + Math.round(v / 1000) + NBSP + "k";
      if (v >= 1000) return signe + dec(v / 1000) + NBSP + "k";
      return signe + v;
    },
    date: function (iso) { var p = parties(iso); return p ? p.j + " " + MOIS[p.m - 1] : ""; },
    dateLongue: function (iso) { var p = parties(iso); return p ? JOURS[p.sem] + " " + p.j + " " + MOIS_LONGS[p.m - 1] : ""; },
    heure: function (iso) { var p = parties(iso); return p ? deuxChiffres(p.h) + ":" + deuxChiffres(p.mi) : ""; },
    relatif: function (iso) {
      var p = parties(iso);
      if (!p) return "";
      var m = parties(new Date().toISOString());
      var d = numJour(m) - numJour(p);
      if (d === 0) return "aujourd'hui";
      if (d === 1) return "hier";
      if (d === -1) return "demain";
      if (d < 0) return "dans " + (-d) + " j";
      if (d < 14) return "il y a " + d + " j";
      if (d < 60) return "il y a " + Math.floor(d / 7) + " sem.";
      return "il y a " + Math.floor(d / 30) + " mois";
    },
    jours: function (n) { n = Math.round(Number(n) || 0); return n + " jour" + (Math.abs(n) > 1 ? "s" : ""); }
  };

  /* ---------- API ---------- */
  function messageDetail(json, statut) {
    var d = json && json.detail;
    if (Array.isArray(d)) d = d.map(function (x) { return x && (x.msg || x.message) ? x.msg || x.message : String(x); }).join(" ; ");
    if (d && typeof d === "object") d = d.message || JSON.stringify(d);
    return d || "Erreur " + statut;
  }

  MK.api = function (chemin, corps, methode) {
    if (MK.mock) {
      return typeof MK._mock === "function" ? MK._mock(chemin, corps, methode || (corps !== undefined ? "POST" : "GET")) : Promise.reject(new Error("Mode mock indisponible."));
    }
    var opts = { method: methode || (corps !== undefined ? "POST" : "GET"), headers: {} };
    var avaitJeton = !!jeton;
    if (jeton) opts.headers.Authorization = "Bearer " + jeton;
    if (corps !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(corps); }
    var ctrl = typeof AbortController === "function" ? new AbortController() : null;
    var delai = null;
    if (ctrl) { opts.signal = ctrl.signal; delai = setTimeout(function () { ctrl.abort(); }, 25000); }
    return fetch(chemin, opts).then(function (r) {
      if (delai) clearTimeout(delai);
      return r.text().then(function (txt) {
        var json = null;
        try { json = txt ? JSON.parse(txt) : null; } catch (x) { json = null; }
        if (!r.ok) {
          var err = new Error(messageDetail(json, r.status));
          err.status = r.status;
          if (r.status === 401 && avaitJeton) { err.message = "Ta session a expiré. Reconnecte-toi."; MK.deconnecter(err.message); }
          throw err;
        }
        return json === null ? {} : json;
      });
    }, function () {
      if (delai) clearTimeout(delai);
      var err = new Error(navigator.onLine === false ? "Tu es hors connexion." : "Impossible de joindre le serveur.");
      err.status = 0;
      err.reseau = true;
      throw err;
    });
  };

  MK.deconnecter = function (message) {
    jeton = null;
    MK.stockage.ecrire(CLE_JETON, null);
    MK.etat.pme = null;
    MK.etat.numero = null;
    MK.etat.demo = false;
    MK.etat.alertesNonLues = 0;
    if (message) MK.toast(message, "info");
    MK.aller("connexion");
  };

  /* ---------- routeur par hash ---------- */
  var ecrans = {};
  var route = { id: null, params: {} };
  var profondeur = (history.state && typeof history.state.i === "number") ? history.state.i : 0; // rang de l'écran dans l'historique de l'onglet
  var rendus = 0;
  var rendu = 0;
  var nettoyage = null;
  var amorce = null;
  MK.params = {};
  MK.route = route;
  MK.ecrans = ecrans;

  MK.ecran = function (id, def) { ecrans[id] = def; };

  function lireHash() {
    var h = location.hash.replace(/^#\/?/, "");
    var i = h.indexOf("?");
    var params = {};
    var id = "";
    try { id = decodeURIComponent(i < 0 ? h : h.slice(0, i)); } catch (x) { id = h; }
    if (i >= 0) new URLSearchParams(h.slice(i + 1)).forEach(function (v, k) { params[k] = v; });
    return { id: id, params: params };
  }

  MK.aller = function (id, params) {
    var h = MK.lien(id, params);
    if (location.hash === h) rendre(); else location.hash = h;
  };
  MK.retour = function () {
    if (profondeur > 0) { history.back(); return; }
    var def = ecrans[route.id];
    MK.aller((def && def.retour) || "accueil");
  };
  MK.recharger = function () { rendre(); };


  function hote() { return document.getElementById("ecran") || document.getElementById("app"); }

  function rendre() {
    var mon = ++rendu;
    var r = lireHash();
    var id = r.id, params = r.params;
    if (!id) { id = jeton ? "accueil" : "connexion"; params = {}; }
    if (!jeton && id !== "connexion") { id = "connexion"; params = {}; }
    else if (jeton && id === "connexion") { id = "accueil"; params = {}; }
    var h = MK.lien(id, params);
    // Aller-retour : l'état conservé par le navigateur porte le rang ; une navigation neuve n'en a pas.
    if (history.state && typeof history.state.i === "number") profondeur = history.state.i; else if (rendus > 0) profondeur++;
    history.replaceState({ i: profondeur }, "", location.pathname + location.search + h);

    var def = ecrans[id];
    if (!def) { def = ecrans.introuvable; params = {}; }
    route.id = id;
    route.params = params;
    MK.params = params;

    if (typeof nettoyage === "function") { try { nettoyage(); } catch (x) { /* écran déjà quitté */ } }
    nettoyage = null;

    var parent = hote();
    var vue = document.createElement("div");
    vue.className = "ecran-vue ecran-" + id.replace(/[^a-z0-9_-]/gi, "");
    vue.setAttribute("aria-busy", "true");
    parent.textContent = "";
    parent.appendChild(vue);
    shell("maj", { def: def, id: id, params: params });
    document.title = (def.titre ? def.titre + " · " : "") + "Mon Kiosque";

    var suite = function (res) {
      if (mon !== rendu) { if (typeof res === "function") { try { res(); } catch (x) { /* rien */ } } return; }
      if (typeof res === "function") nettoyage = res;
      vue.removeAttribute("aria-busy");
    };
    var echec = function (err) {
      if (mon !== rendu) return;
      vue.removeAttribute("aria-busy");
      vue.textContent = "";
      vue.appendChild(MK.etatErreur(err, rendre));
    };
    try {
      var sortie = def.rendre(vue, params);
      if (sortie && typeof sortie.then === "function") sortie.then(suite, echec); else suite(sortie);
    } catch (err) { echec(err); }

    rendus++;
    if (rendus > 1) { window.scrollTo(0, 0); }
    try { parent.focus({ preventScroll: true }); } catch (x) { /* focus indisponible */ }
  }

  MK.demarrer = function () {
    window.addEventListener("hashchange", rendre);
    rendre();
  };

  /* ---------- composants JS ---------- */
  MK.pastille = function (texte, type) {
    var t = ["ok", "attention", "urgent", "info", "neutre"].indexOf(type) >= 0 ? type : "neutre";
    return '<span class="pastille ' + t + '">' + e(texte) + "</span>";
  };

  MK.squelette = function (nb) {
    var largeurs = [100, 100, 92, 100, 84, 96, 100, 78];
    var html = '<div class="squelette-groupe" role="status" aria-busy="true"><span class="sr-only">Chargement en cours…</span><div class="squelette"></div>';
    nb = nb === undefined ? 3 : Math.max(0, nb);
    for (var i = 0; i < nb; i++) html += '<div class="squelette" style="width:' + largeurs[i % largeurs.length] + '%"></div>';
    return html + "</div>";
  };

  MK.etatVide = function (o) {
    o = o || {};
    var a = o.action;
    return '<div class="vide">' +
      (o.icone ? '<div class="vide-ico">' + MK.icone(o.icone, { taille: 26 }) + "</div>" : "") +
      "<h2>" + e(o.titre || "Rien à afficher") + "</h2>" +
      (o.texte ? "<p>" + e(o.texte) + "</p>" : "") +
      (a ? '<a class="btn secondaire" href="' + e(MK.lien(a.ecran, a.params)) + '">' + e(a.libelle) + "</a>" : "") +
      "</div>";
  };

  MK.etatErreur = function (err, reessayer) {
    err = err || {};
    var st = err.status, titre, texte;
    if (st === 0 || err.reseau) {
      titre = "Pas de connexion";
      texte = "Impossible de joindre Mon Kiosque pour l'instant. Vérifie ta connexion Internet puis réessaie. Tes données sont en sécurité.";
    } else if (st >= 500) {
      titre = "Un problème est survenu de notre côté";
      texte = "Ce n'est pas de ton fait. Réessaie dans un instant ; si ça continue, écris à Moki.";
    } else if (st === 404) {
      titre = "Introuvable";
      texte = err.message || "Cet élément n'existe pas ou plus.";
    } else {
      titre = "Une erreur est survenue";
      texte = err.message || "Réessaie dans un instant.";
    }
    var div = document.createElement("div");
    div.className = "vide erreur";
    div.setAttribute("role", "alert");
    div.innerHTML = '<div class="vide-ico">' + MK.icone("alertes", { taille: 26 }) + "</div><h2>" + e(titre) + "</h2><p>" + e(texte) + "</p>" +
      (st !== undefined && err.message ? '<details class="vide-detail"><summary>Détail technique</summary><code>' + e((st ? st + " · " : "") + err.message) + "</code></details>" : "") +
      (typeof reessayer === "function" ? '<div class="rangee"><button type="button" class="btn primaire" data-reessayer>Réessayer</button></div>' : "");
    var b = div.querySelector("[data-reessayer]");
    if (b) b.addEventListener("click", function () { b.setAttribute("aria-busy", "true"); reessayer(); });
    return div;
  };

  /* ---------- toast ---------- */
  MK.toast = function (msg, type) {
    var cont = document.querySelector(".toasts");
    if (!cont) {
      cont = document.createElement("div");
      cont.className = "toasts";
      cont.setAttribute("role", "status");
      cont.setAttribute("aria-live", "polite");
      document.body.appendChild(cont);
    }
    var t = document.createElement("div");
    t.className = "toast " + (type === "erreur" ? "erreur" : type === "info" ? "info" : "ok");
    if (type === "erreur") t.setAttribute("role", "alert");
    t.textContent = msg;
    cont.appendChild(t);
    var fin = function () { t.classList.add("sortie"); setTimeout(function () { t.remove(); }, 220); };
    var minuteur = setTimeout(fin, 3500);
    t.addEventListener("click", function () { clearTimeout(minuteur); fin(); });
    return t;
  };

  /* ---------- feuille (bottom-sheet mobile, modale desktop) ---------- */
  var nbFeuilles = 0;
  var FOCALISABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

  MK.feuille = function (o) {
    o = o || {};
    var precedent = document.activeElement;
    var id = "feuille-titre-" + (++nbFeuilles);
    var fond = document.createElement("div");
    fond.className = "feuille-fond";
    fond.innerHTML = '<div class="feuille" role="dialog" aria-modal="true" aria-labelledby="' + id + '" tabindex="-1">' +
      '<div class="feuille-poignee" aria-hidden="true"></div>' +
      '<div class="feuille-entete"><h2 id="' + id + '">' + e(o.titre || "") + '</h2><button type="button" class="btn discret petit" data-fermer>Fermer</button></div>' +
      '<div class="feuille-corps"></div></div>';
    var f = fond.firstChild;
    var corps = f.querySelector(".feuille-corps");
    if (o.contenu && o.contenu.nodeType) corps.appendChild(o.contenu); else corps.innerHTML = o.contenu || "";
    var ferme = false;

    function fermer() {
      if (ferme) return;
      ferme = true;
      document.removeEventListener("keydown", touche, true);
      fond.classList.remove("ouverte");
      setTimeout(function () {
        fond.remove();
        if (--ouvertes <= 0) { ouvertes = 0; document.body.classList.remove("sans-defilement"); }
      }, 200);
      if (precedent && typeof precedent.focus === "function" && document.contains(precedent)) { try { precedent.focus({ preventScroll: true }); } catch (x) { /* rien */ } }
    }
    var ctrl = { fermer: fermer, el: f, corps: corps };

    var actions = o.actions || [];
    if (actions.length) {
      var pied = document.createElement("div");
      pied.className = "feuille-actions";
      actions.forEach(function (a) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "btn " + (a.primaire ? "primaire" : "secondaire");
        b.textContent = a.libelle;
        b.addEventListener("click", function () {
          var res;
          try { res = typeof a.onclick === "function" ? a.onclick(ctrl) : undefined; } catch (x) { MK.toast(x && x.message ? x.message : "Action impossible.", "erreur"); return; }
          if (res && typeof res.then === "function") {
            b.setAttribute("aria-busy", "true");
            res.then(function (v) { if (v !== false) fermer(); else b.removeAttribute("aria-busy"); }, function (x) { b.removeAttribute("aria-busy"); MK.toast(x && x.message ? x.message : "Action impossible.", "erreur"); });
          } else if (res !== false) fermer();
        });
        pied.appendChild(b);
      });
      f.appendChild(pied);
    }

    function touche(ev) {
      if (ev.key === "Escape") { ev.stopPropagation(); fermer(); return; }
      if (ev.key !== "Tab") return;
      var liste = Array.prototype.filter.call(f.querySelectorAll(FOCALISABLE), function (x) { return x.offsetParent !== null; });
      if (!liste.length) { ev.preventDefault(); return; }
      var premier = liste[0], dernier = liste[liste.length - 1];
      if (ev.shiftKey && (document.activeElement === premier || document.activeElement === f)) { ev.preventDefault(); dernier.focus(); }
      else if (!ev.shiftKey && document.activeElement === dernier) { ev.preventDefault(); premier.focus(); }
    }
    document.addEventListener("keydown", touche, true);
    fond.addEventListener("mousedown", function (ev) { if (ev.target === fond) fermer(); });
    f.querySelector("[data-fermer]").addEventListener("click", fermer);

    ouvertes++;
    document.body.classList.add("sans-defilement");
    document.body.appendChild(fond);
    requestAnimationFrame(function () {
      fond.classList.add("ouverte");
      var premier = corps.querySelector(FOCALISABLE);
      (premier || f).focus({ preventScroll: true });
    });
    return ctrl;
  };
  var ouvertes = 0;

  /* ---------- assistant ---------- */
  function versAssistant(texte, envoyer) {
    amorce = { texte: String(texte || ""), envoyer: !!envoyer };
    if (route.id === "assistant") window.dispatchEvent(new CustomEvent("mk:assistant", { detail: amorce }));
    else MK.aller("assistant");
  }
  MK.amorcerAssistant = function (texte) { versAssistant(texte, false); };
  MK.envoyerAssistant = function (texte) { versAssistant(texte, true); };
  /* L'écran assistant appelle ceci à son montage (et à chaque événement « mk:assistant ») : { texte, envoyer } ou null */
  MK.prendreAmorce = function () { var a = amorce; amorce = null; return a; };

  /* ---------- écran « introuvable » ---------- */
  MK.ecran("introuvable", {
    titre: "Page introuvable",
    onglet: null,
    rendre: function (el) {
      el.innerHTML = '<div class="vide page">' +
        '<div class="vide-ico">' + MK.icone("recherche", { taille: 26 }) + "</div>" +
        '<div class="surtitre">Page introuvable</div>' +
        "<h1>Cette page n'existe pas, ou plus</h1>" +
        "<p>L'adresse est peut-être incomplète. Tes ventes et tes factures n'ont pas bougé.</p>" +
        '<div class="rangee"><a class="btn primaire" href="#/accueil">Revenir à l\'accueil</a><a class="btn secondaire" href="#/suivi">Ouvrir le suivi</a></div></div>';
    }
  });
})();
