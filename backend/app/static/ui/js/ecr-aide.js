/* Mon Kiosque : écran Aide (route « aide »). Contenu statique ; les phrases d'exemple pré-remplissent Moki. */
(function () {
  "use strict";

  var e = MK.echapper;

  /* Ce que Moki sait faire : un thème = une carte. `icone` vient du dossier ui/icones (même icône que l'onglet du thème). */
  var THEMES = [
    {
      titre: "Ventes", icone: "suivi",
      texte: "Dis ce que tu as vendu, comme tu le dirais à voix haute.",
      phrases: ["j'ai vendu 3 paires à 5000", "j'ai fait combien aujourd'hui ?", "qui me doit ?"]
    },
    {
      titre: "Dépenses et perso/pro", icone: "historique",
      texte: "Moki sépare l'argent du commerce de celui de la maison.",
      phrases: ["j'ai payé 20 000 de loyer", "j'ai acheté du tissu à 15 000", "j'ai retiré 10 000 pour la maison"]
    },
    {
      titre: "Factures et relances", icone: "reservation",
      texte: "Moki prépare la facture ou la relance ; rien ne part sans ton OUI.",
      phrases: ["facture Lycée Technique, 30 repas à 2500", "l'état de mes factures", "relance Mme Fotso"]
    },
    {
      titre: "Chiffres et trésorerie", icone: "concurrence",
      texte: "Ventes, charges, bénéfice et argent disponible, à tout moment.",
      phrases: ["j'ai fait combien cette semaine ?", "mon bénéfice du mois", "combien j'ai en caisse ?"]
    },
    {
      titre: "Impôt et dossier de crédit", icone: "modeles",
      texte: "Ton historique devient un dossier propre pour une banque ou une microfinance.",
      phrases: ["prépare mon dossier de crédit", "mon impôt", "quand est ma prochaine échéance ?"],
      large: true
    }
  ];

  var ETAPES = [
    { titre: "Tu écris", texte: "Dans l'onglet Moki, avec tes mots : une vente, une dépense, une question. Le français, le franglais ou une faute de frappe ne posent pas de problème." },
    { titre: "Moki te montre ce qu'il a compris", texte: "Il reformule en clair, avec les montants calculés. Si une information manque, il te la demande au lieu de deviner." },
    { titre: "Tu confirmes", texte: "Tu réponds OUI pour valider, NON pour laisser tomber. C'est seulement à ce moment que l'action est faite." }
  ];

  var SECURITE = [
    { titre: "Aucun message client sans ton OUI", texte: "Moki n'envoie jamais une facture, une relance ou un lien de paiement à un client sans que tu aies dit OUI." },
    { titre: "Il demande quand il n'est pas sûr", texte: "Un montant, un nom ou un produit qu'il ne reconnaît pas : Moki te pose la question plutôt que d'inventer." },
    { titre: "Chaque commerce ne voit que ses données", texte: "Tes ventes, tes clients et tes factures sont réservés à ton commerce. Personne d'autre ne les voit." }
  ];

  var FAQ = [
    { q: "Mes données sont-elles en sécurité ?", r: "Oui. Seul ton commerce voit ses ventes, ses clients et ses factures. Moki n'envoie rien à tes clients sans ta confirmation, et tu peux te déconnecter à tout moment depuis les réglages." },
    { q: "Puis-je annuler ?", r: "Oui, pendant 10 minutes. Écris « annuler » à Moki juste après l'action. Passé ce délai, Moki te dit qu'il n'y a plus rien à annuler automatiquement." },
    { q: "Moki fait-il mes impôts ?", r: "Non. Moki calcule une estimation indicative à partir de tes ventes. Elle n'a pas de valeur officielle : confirme toujours le montant avec la DGI avant de payer ou de déclarer." },
    { q: "Que faire si je n'ai pas internet ?", r: "Écris quand même : tes messages sont conservés par WhatsApp et partent dès que le réseau revient. Moki utilise l'heure à laquelle tu as envoyé le message, pas celle où il le reçoit." },
    { q: "Les données de la démo sont-elles réelles ?", r: "Non. Dans la démo, les commerces, les clients, les montants et les messages sont fictifs. Rien n'est envoyé à de vraies personnes." }
  ];

  function carteTheme(t) {
    var boutons = t.phrases.map(function (p) {
      return '<li><button type="button" class="aid-phrase" data-phrase="' + e(p) + '"><span class="aid-phrase-txt">« ' + e(p) + " »</span></button></li>";
    }).join("");
    return '<section class="carte aid-theme' + (t.large ? " aid-large" : "") + '" aria-labelledby="aid-t-' + e(t.icone) + '">' +
      '<div class="aid-theme-tete"><span class="ligne-ico">' + MK.icone(t.icone, { taille: 20 }) + "</span>" +
      '<h3 id="aid-t-' + e(t.icone) + '">' + e(t.titre) + "</h3></div>" +
      '<p class="aid-theme-texte">' + e(t.texte) + "</p>" +
      '<ul class="aid-phrases">' + boutons + "</ul></section>";
  }

  function rendre(el) {
    var html = '<div class="aid-page">' +
      '<header class="entete-ecran"><div><h1>Aide</h1>' +
      '<p class="sous">Écris à Moki comme tu parles. Voici ce qu\'il sait faire, et comment ça se passe.</p></div></header>' +

      '<section class="aid-bloc" aria-labelledby="aid-faire"><div class="aid-surtitre" id="aid-faire">Ce que Moki sait faire</div>' +
      '<p class="aid-intro">Touche une phrase : elle s\'écrit dans Moki, tu peux la modifier avant de l\'envoyer.</p>' +
      '<div class="aid-themes">' + THEMES.map(carteTheme).join("") + "</div></section>" +

      '<section class="aid-bloc" aria-labelledby="aid-marche"><div class="aid-surtitre" id="aid-marche">Comment ça marche</div>' +
      '<ol class="aid-etapes">' + ETAPES.map(function (s, i) {
        return '<li class="aid-etape"><span class="aid-num" aria-hidden="true">' + (i + 1) + "</span>" +
          '<div><h3>' + e(s.titre) + "</h3><p>" + e(s.texte) + "</p></div></li>";
      }).join("") + "</ol></section>" +

      '<section class="aid-bloc" aria-labelledby="aid-secu"><div class="aid-surtitre" id="aid-secu">Tes règles de sécurité</div>' +
      '<ul class="aid-secu">' + SECURITE.map(function (s) {
        return '<li class="aid-regle"><h3>' + e(s.titre) + "</h3><p>" + e(s.texte) + "</p></li>";
      }).join("") + "</ul></section>" +

      '<section class="aid-bloc" aria-labelledby="aid-faq"><div class="aid-surtitre" id="aid-faq">Questions fréquentes</div>' +
      '<div class="aid-faq">' + FAQ.map(function (f) {
        return '<details class="aid-q"><summary>' + e(f.q) + "</summary><p>" + e(f.r) + "</p></details>";
      }).join("") + "</div></section>" +

      '<section class="carte aid-humain" aria-labelledby="aid-hum">' +
      '<div class="aid-humain-corps"><h2 id="aid-hum">Tu ne trouves pas la réponse ?</h2>' +
      "<p>Dis-le à Moki : quelqu'un de l'équipe te contacte rapidement. En attendant, Moki reste là.</p></div>" +
      '<button type="button" class="btn primaire" data-humain>' + MK.icone("assistant", { taille: 20 }) + "Parler à un humain</button></section>" +
      "</div>";

    el.innerHTML = html;

    el.addEventListener("click", function (ev) {
      var cible = ev.target.closest ? ev.target.closest("button") : null;
      if (!cible || !el.contains(cible)) return;
      if (cible.hasAttribute("data-humain")) { MK.envoyerAssistant("humain"); return; }
      var phrase = cible.getAttribute("data-phrase");
      if (phrase) MK.amorcerAssistant(phrase);
    });
  }

  MK.ecran("aide", { titre: "Aide", onglet: "reglages", retour: "reglages", rendre: rendre });
})();
