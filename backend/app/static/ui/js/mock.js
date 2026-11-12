/* Mon Kiosque : données factices (?mock=1) pour tous les endpoints du contrat (§5) et les existants.
   Commerce de démonstration : « Chez Marie », restaurant à Essos, Yaoundé, gérante Marie.
   Cas : ?cas=vide (listes vides) et ?cas=erreur (le serveur répond 500, sauf la connexion). */
(function () {
  "use strict";
  var MK = window.MK;
  if (!MK || !MK.mock) return;

  var LATENCE = 250;
  var NUMERO_DEMO = "237677000001";
  var vide = MK.cas === "vide";

  /* ---------- dates relatives à aujourd'hui (UTC naïf ; le Cameroun est à UTC+1) ---------- */
  function base() { var d = new Date(Date.now() + 3600000); return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()); }
  function iso(jours, h, mn) { return new Date(base() - jours * 86400000 + ((h || 0) - 1) * 3600000 + (mn || 0) * 60000).toISOString().slice(0, 19); }
  function jour(jours) { return new Date(base() - jours * 86400000).toISOString().slice(0, 10); }
  function prochain(jourDuMois, mois) { // prochaine date (AAAA-MM-JJ) : le jourDuMois du mois donné (1-12), ou du mois courant/suivant si mois est omis
    var b = new Date(base()), a = b.getUTCFullYear(), m = mois ? mois - 1 : b.getUTCMonth();
    var d = Date.UTC(a, m, jourDuMois);
    if (d < base()) d = mois ? Date.UTC(a + 1, m, jourDuMois) : Date.UTC(a, m + 1, jourDuMois);
    return new Date(d).toISOString().slice(0, 10);
  }
  function ecart(dateIso) { return Math.round((Date.parse(dateIso) - base()) / 86400000); }
  function abrev(jours) { return ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"][new Date(base() - jours * 86400000).getUTCDay()]; }
  function somme(tab, cle) { return tab.reduce(function (s, x) { return s + (cle ? x[cle] : x); }, 0); }
  function copie(o) { return JSON.parse(JSON.stringify(o)); }

  /* ---------- PDF de démonstration (un vrai PDF d'une page, en data: URL) ---------- */
  function pdf(titre) {
    var flux = "BT /F1 18 Tf 60 760 Td (" + titre.replace(/[()\\]/g, "") + ") Tj 0 -28 Td /F1 12 Tf (Document de demonstration, donnees fictives.) Tj ET";
    var objets = [
      "<< /Type /Catalog /Pages 2 0 R >>",
      "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
      "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
      "<< /Length " + flux.length + " >>\nstream\n" + flux + "\nendstream",
      "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    ];
    var s = "%PDF-1.4\n", pos = [];
    objets.forEach(function (o, i) { pos.push(s.length); s += (i + 1) + " 0 obj\n" + o + "\nendobj\n"; });
    var xref = s.length;
    s += "xref\n0 " + (objets.length + 1) + "\n0000000000 65535 f \n" + pos.map(function (p) { return ("0000000000" + p).slice(-10) + " 00000 n \n"; }).join("");
    s += "trailer\n<< /Size " + (objets.length + 1) + " /Root 1 0 R >>\nstartxref\n" + xref + "\n%%EOF";
    return "data:application/pdf;base64," + btoa(s);
  }

  /* ---------- clients, produits ---------- */
  var CLIENTS = [
    { id: 1, nom: "Lycée Technique d'Essos", telephone: "237677120045", quartier: "Essos", dette: 80000, nb_achats: 9, total_achats: 612000, dernier_achat: iso(20, 11, 30), inactif: false },
    { id: 2, nom: "Cantine Mvog-Ada", telephone: "237699330112", quartier: "Mvog-Ada", dette: 36000, nb_achats: 14, total_achats: 498000, dernier_achat: iso(1, 10, 0), inactif: false },
    { id: 3, nom: "Mme Biya", telephone: "237655447780", quartier: "Essos", dette: 12000, nb_achats: 22, total_achats: 164000, dernier_achat: iso(2, 13, 10), inactif: false },
    { id: 4, nom: "Bureau Essos Services", telephone: "237670218834", quartier: "Essos", dette: 0, nb_achats: 11, total_achats: 385000, dernier_achat: iso(1, 16, 30), inactif: false },
    { id: 5, nom: "Hôtel Le Relais", telephone: "237222205540", quartier: "Bastos", dette: 0, nb_achats: 6, total_achats: 540000, dernier_achat: iso(9, 9, 15), inactif: false },
    { id: 6, nom: "M. Tchoupo", telephone: "237691002233", quartier: "Nsimeyong", dette: 0, nb_achats: 31, total_achats: 142500, dernier_achat: iso(0, 12, 40), inactif: false },
    { id: 7, nom: "Pharmacie Les Palmiers", telephone: "237677884400", quartier: "Essos", dette: 0, nb_achats: 4, total_achats: 112000, dernier_achat: iso(38, 12, 0), inactif: true },
    { id: 8, nom: "Mme Ngo Bayiha", telephone: null, quartier: null, dette: 0, nb_achats: 3, total_achats: 21000, dernier_achat: iso(46, 18, 20), inactif: true }
  ];
  var PRODUITS = [
    { id: 1, nom: "Poulet DG", prix: 3500, ventes_30j: 154, ca_30j: 539000 },
    { id: 2, nom: "Repas du jour", prix: 2500, ventes_30j: 164, ca_30j: 410000 },
    { id: 3, nom: "Boissons", prix: 600, ventes_30j: 367, ca_30j: 220000 },
    { id: 4, nom: "Brochettes (10)", prix: 1500, ventes_30j: 107, ca_30j: 160500 },
    { id: 5, nom: "Poisson braisé", prix: 4000, ventes_30j: 37, ca_30j: 148000 },
    { id: 6, nom: "Ndolé", prix: 3000, ventes_30j: 41, ca_30j: 123000 },
    { id: 7, nom: "Riz sauté", prix: 2000, ventes_30j: 22, ca_30j: 44000 },
    { id: 8, nom: "Jus de gingembre", prix: 500, ventes_30j: 58, ca_30j: 29000 }
  ];

  /* ---------- historique (du plus récent au plus ancien) ---------- */
  function el(type, n, jours, h, mn, titre, detail, montant, sens, statut, client) {
    return { id: type + "-" + n, type: type, date: iso(jours, h, mn), titre: titre, detail: detail, montant: montant, sens: sens, statut: statut, client: client || null };
  }
  var HISTORIQUE = [
    el("vente", 42, 0, 14, 5, "Vente : Ndolé × 2", "2 × 3 000 F, mobile money", 6000, "entree", "ok", null),
    el("vente", 41, 0, 13, 50, "Vente : Repas du jour × 1", "1 × 2 500 F, espèces", 2500, "entree", "ok", "M. Tchoupo"),
    el("vente", 40, 0, 13, 20, "Vente : Boissons × 4", "4 × 600 F plus un jus, espèces", 2500, "entree", "ok", null),
    el("vente", 39, 0, 13, 5, "Vente : Poulet DG × 3", "3 × 3 500 F, mobile money", 10500, "entree", "ok", null),
    el("vente", 38, 0, 12, 40, "Vente : Repas du jour × 4", "4 × 2 500 F, mobile money", 10000, "entree", "ok", null),
    el("vente", 37, 0, 12, 25, "Vente : Poisson braisé × 1", "1 × 4 000 F, espèces", 4000, "entree", "ok", null),
    el("vente", 36, 0, 12, 10, "Vente : Riz sauté × 2", "2 × 2 000 F, espèces", 4000, "entree", "annule", null),
    el("vente", 35, 0, 11, 55, "Vente : Brochettes × 10", "10 × 1 500 F, espèces", 15000, "entree", "ok", null),
    el("vente", 34, 0, 11, 30, "Vente : Boissons × 5", "5 × 600 F plus un jus, espèces", 3500, "entree", "ok", null),
    el("vente", 33, 0, 10, 45, "Vente : Repas du jour × 2", "2 × 2 500 F, espèces", 5000, "entree", "ok", null),
    el("vente", 32, 0, 9, 30, "Vente : Boissons × 3", "3 × 500 F, espèces", 1500, "entree", "ok", null),
    el("vente", 31, 0, 8, 15, "Vente : Poulet DG × 2", "2 × 3 000 F, espèces", 6000, "entree", "ok", null),
    el("depense", 18, 0, 7, 50, "Marché : légumes et poisson", "Achat au marché d'Essos", 15000, "sortie", "ok", null),
    el("paiement", 9, 1, 16, 30, "Paiement reçu : Bureau Essos Services", "Facture n° 46, Orange Money", 45000, "entree", "ok", "Bureau Essos Services"),
    el("facture", 48, 1, 10, 0, "Facture n° 48 envoyée", "Cantine Mvog-Ada, 36 000 F à régler", 36000, "neutre", "en_attente", "Cantine Mvog-Ada"),
    el("vente", 30, 1, 13, 10, "Vente : Ndolé × 5", "5 × 3 000 F, espèces", 15000, "entree", "ok", null),
    el("depense", 17, 2, 9, 0, "Gaz : bouteille de 12,5 kg", "Recharge chez le dépositaire", 6500, "sortie", "ok", null),
    el("vente", 29, 2, 13, 10, "Vente à crédit : Repas du jour × 5", "5 × 2 500 F, à payer plus tard", 12500, "neutre", "en_attente", "Mme Biya"),
    el("vente", 28, 3, 12, 20, "Vente : Poulet DG × 6", "6 × 3 500 F, mobile money", 21000, "entree", "ok", null),
    el("depense", 16, 3, 7, 30, "Salaire : aide cuisinière", "Acompte de la semaine", 30000, "sortie", "ok", null),
    el("paiement", 8, 5, 15, 0, "Paiement reçu : Hôtel Le Relais", "Facture n° 45, virement", 120000, "entree", "ok", "Hôtel Le Relais"),
    el("facture", 47, 20, 11, 30, "Facture n° 47 envoyée", "Lycée Technique d'Essos, 80 000 F à régler", 80000, "neutre", "retard", "Lycée Technique d'Essos"),
    el("depense", 15, 6, 8, 10, "Électricité : facture de la quinzaine", "Paiement en agence", 17500, "sortie", "ok", null),
    el("vente", 27, 6, 12, 45, "Vente : Boissons × 24", "24 × 600 F, espèces", 14400, "entree", "ok", "M. Tchoupo"),
    el("facture", 46, 9, 9, 40, "Facture n° 46 envoyée", "Bureau Essos Services, 45 000 F", 45000, "neutre", "ok", "Bureau Essos Services"),
    el("vente", 26, 10, 13, 5, "Vente : Poisson braisé × 4", "4 × 4 000 F, mobile money", 16000, "entree", "ok", null),
    el("depense", 14, 11, 7, 40, "Marché : viande et épices", "Achat au marché d'Essos", 42000, "sortie", "ok", null),
    el("facture", 45, 14, 10, 20, "Facture n° 45 envoyée", "Hôtel Le Relais, 120 000 F", 120000, "neutre", "ok", "Hôtel Le Relais"),
    el("vente", 25, 15, 12, 0, "Vente : Repas du jour × 12", "12 × 2 500 F, espèces", 30000, "entree", "ok", null)
  ];
  var DETAIL_LIGNES = {
    "vente-39": [{ libelle: "Poulet DG", quantite: 3, prix_unitaire: 3500, montant: 10500 }],
    "vente-38": [{ libelle: "Repas du jour", quantite: 4, prix_unitaire: 2500, montant: 10000 }],
    "vente-35": [{ libelle: "Brochettes (10)", quantite: 10, prix_unitaire: 1500, montant: 15000 }],
    "vente-29": [{ libelle: "Repas du jour", quantite: 5, prix_unitaire: 2500, montant: 12500 }],
    "depense-18": [{ libelle: "Légumes (tomates, oignons, piments)", quantite: 1, prix_unitaire: 9000, montant: 9000 }, { libelle: "Poisson frais", quantite: 1, prix_unitaire: 6000, montant: 6000 }]
  };

  /* ---------- factures ---------- */
  var FACTURES = [
    { id: 7, numero: 47, client_id: 1, date: iso(20, 11, 30), echeance: jour(6), statut: "en_retard", lignes: [{ libelle: "Repas du jour (menu cantine)", quantite: 32, prix_unitaire: 2500 }], frais: [], relances: [{ date: iso(3, 9, 0), mode: "transfert", texte: "Bonjour, petit rappel : la facture n° 47 de 80 000 F est arrivée à échéance. Merci de nous dire quand le paiement part. Chez Marie." }], paiements: [] },
    { id: 8, numero: 48, client_id: 2, date: iso(1, 10, 0), echeance: jour(-13), statut: "envoyee", lignes: [{ libelle: "Repas du jour", quantite: 12, prix_unitaire: 2500 }, { libelle: "Jus de gingembre", quantite: 12, prix_unitaire: 500 }], frais: [], relances: [], paiements: [] },
    { id: 6, numero: 46, client_id: 4, date: iso(9, 9, 40), echeance: jour(-5), statut: "payee", lignes: [{ libelle: "Poulet DG", quantite: 10, prix_unitaire: 3500 }, { libelle: "Boissons", quantite: 16, prix_unitaire: 600 }], frais: [{ libelle: "Livraison (Essos)", montant: 400 }], relances: [], paiements: [{ date: iso(1, 16, 30), montant: 45000, source: "Orange Money" }] },
    { id: 5, numero: 45, client_id: 5, date: iso(14, 10, 20), echeance: jour(0), statut: "payee", lignes: [{ libelle: "Buffet de midi (réunion)", quantite: 30, prix_unitaire: 4000 }], frais: [], relances: [], paiements: [{ date: iso(5, 15, 0), montant: 120000, source: "Virement bancaire" }] },
    { id: 4, numero: 44, client_id: 7, date: iso(40, 9, 0), echeance: jour(25), statut: "payee", lignes: [{ libelle: "Plateaux repas", quantite: 14, prix_unitaire: 2000 }], frais: [], relances: [{ date: iso(30, 9, 0), mode: "direct", texte: "Bonjour, nous n'avons pas encore reçu le paiement de la facture n° 44 (28 000 F). Merci. Chez Marie." }], paiements: [{ date: iso(24, 11, 0), montant: 28000, source: "Espèces" }] }
  ];
  function totalFacture(f) { return somme(f.lignes.map(function (l) { return l.quantite * l.prix_unitaire; })) + somme(f.frais, "montant"); }
  function nomClient(id) { return CLIENTS.filter(function (c) { return c.id === id; })[0]; }
  function resumeFacture(f) {
    var c = nomClient(f.client_id);
    var retard = f.statut === "en_retard" ? Math.max(0, -ecart(f.echeance)) : 0;
    return { id: f.id, numero: f.numero, client: c.nom, client_id: c.id, total: totalFacture(f), statut: f.statut, jours_retard: retard, date: f.date, echeance: f.echeance };
  }
  function ficheFacture(f) {
    var r = resumeFacture(f), c = nomClient(f.client_id), n = String(f.numero);
    return {
      id: f.id, numero: f.numero, client: c.nom, client_id: c.id, telephone: c.telephone, date: f.date, echeance: f.echeance, statut: f.statut, jours_retard: r.jours_retard, total: r.total,
      lignes: f.lignes.map(function (l) { return { libelle: l.libelle, quantite: l.quantite, prix_unitaire: l.prix_unitaire, montant: l.quantite * l.prix_unitaire }; }),
      frais: copie(f.frais), relances: copie(f.relances), paiements: copie(f.paiements),
      message_client: "Bonjour " + c.nom + ", voici votre facture n° " + n + " de " + MK.fmt.fcfa(r.total) + ", à régler avant le " + MK.fmt.date(f.echeance) + ". Payer en ligne : https://pay.moki.example/f/" + n + ". Merci de votre confiance. Chez Marie, Essos.",
      lien_paiement: "https://pay.moki.example/f/" + n, paiement_simule: true, pdf_url: pdf("Facture n " + n + " - Chez Marie")
    };
  }

  /* ---------- alertes ---------- */
  var ALERTES = [
    { id: 1, type: "retard", niveau: "urgent", titre: "Lycée Technique a 6 jours de retard", texte: "La facture n° 47 de 80 000 F est échue. Une relance partirait avec ta confirmation.", date: iso(0, 7, 30), lue: false, action: { ecran: "facture", params: { id: 7 } } },
    { id: 2, type: "echeance", niveau: "attention", titre: "Déclaration mensuelle dans " + Math.max(0, ecart(prochain(15))) + " jours", texte: "La date limite est le " + MK.fmt.dateLongue(prochain(15)) + ". Ton estimation est prête.", date: iso(0, 7, 0), lue: false, action: { ecran: "documents", params: {} } },
    { id: 3, type: "charge", niveau: "attention", titre: "Tes achats de marché montent", texte: "Tu as dépensé 18 % de plus qu'il y a une semaine en ingrédients.", date: iso(1, 18, 0), lue: false, action: { ecran: "chiffres", params: { periode: "semaine" } } },
    { id: 4, type: "resume", niveau: "info", titre: "Résumé d'hier : 58 000 F de ventes", texte: "9 ventes, 15 000 F de dépenses. Bénéfice du jour : 43 000 F.", date: iso(1, 19, 0), lue: true, action: { ecran: "historique", params: {} } },
    { id: 5, type: "client", niveau: "info", titre: "Pharmacie Les Palmiers n'a pas commandé depuis 5 semaines", texte: "Un petit message de ta part peut la faire revenir.", date: iso(2, 8, 0), lue: true, action: { ecran: "client", params: { id: 7 } } },
    { id: 6, type: "info", niveau: "info", titre: "Ton dossier de crédit avance", texte: "Il te manque 1 mois de saisies régulières pour atteindre les 6 mois.", date: iso(4, 9, 0), lue: true, action: { ecran: "documents", params: {} } }
  ];
  function nbNonLues() { return vide ? 0 : ALERTES.filter(function (a) { return !a.lue; }).length; }

  /* ---------- paramètres ---------- */
  var PARAMETRES = {
    commerce: { nom_commerce: "Chez Marie", nom_gerante: "Marie Ngono", ville: "Yaoundé", quartier: "Essos", secteur: "Restauration", numero: NUMERO_DEMO },
    preferences: { mode_relance: "transfert", seuil_confirmation_renforcee: 100000, resume_du_soir: true, rappels_fiscaux: true },
    demo: true
  };

  /* ---------- chiffres ---------- */
  var PERIODES = {
    jour: { libelle: "Aujourd'hui", serie: [["8 h", 7500, 15000], ["10 h", 6500, 0], ["12 h", 31000, 0], ["14 h", 12500, 0], ["16 h", 6000, 0], ["18 h", 4000, 0]], nb: 12, retraits: 0, facteur: 0.045, parts: [0.59, 0.41, 0, 0] },
    semaine: { libelle: "7 derniers jours", serie: [[abrev(6), 41000, 12000], [abrev(5), 58000, 14000], [abrev(4), 83000, 21000], [abrev(3), 29000, 9000], [abrev(2), 47000, 15000], [abrev(1), 36500, 12000], [abrev(0), 67500, 15000]], nb: 64, retraits: 20000, facteur: 0.245, parts: [0.51, 0.33, 0.04, 0.12] },
    mois: { libelle: "Ce mois-ci", serie: [["S1", 310000, 110000], ["S2", 395000, 140000], ["S3", 360000, 125000], ["S4", 415000, 145000]], nb: 266, retraits: 150000, facteur: 1, parts: [0.49, 0.32, 0.04, 0.15] },
    annee: { libelle: "Cette année", serie: [["Jan", 980000, 360000], ["Fév", 1020000, 380000], ["Mar", 1110000, 410000], ["Avr", 1090000, 410000], ["Mai", 1180000, 440000], ["Juin", 1150000, 430000], ["Juil", 1210000, 460000], ["Août", 1260000, 475000], ["Sep", 1330000, 505000], ["Oct", 1390000, 510000], ["Nov", 1480000, 520000]], nb: 2380, retraits: 1100000, facteur: 8.9, parts: [0.485, 0.325, 0.03, 0.16] }
  };
  var TOP = [["Poulet DG", 540000], ["Repas du jour", 410000], ["Boissons", 220000], ["Brochettes", 160000], ["Poisson braisé", 150000]];
  var POSTES = [["Achats au marché", 0.51], ["Salaires", 0.25], ["Loyer", 0.115], ["Eau et électricité", 0.067], ["Transport", 0.058]];

  function chiffres(periode) {
    var p = PERIODES[periode] || PERIODES.mois;
    var cle = PERIODES[periode] ? periode : "mois";
    var ventes = somme(p.serie.map(function (x) { return x[1]; })), charges = somme(p.serie.map(function (x) { return x[2]; }));
    var mode = [Math.round(ventes * p.parts[0]), Math.round(ventes * p.parts[1]), Math.round(ventes * p.parts[2]), 0];
    mode[3] = ventes - mode[0] - mode[1] - mode[2];
    var postes = POSTES.map(function (x) { return { libelle: x[0], total: Math.round(charges * x[1] / 500) * 500 }; });
    postes[0].total += charges - somme(postes, "total");
    var libelle = p.libelle;
    return {
      periode: cle, libelle: libelle, ventes: ventes, charges: charges, benefice: ventes - charges, stock: 185000, retraits_perso: p.retraits, tresorerie: 845000,
      par_mode: { cash: mode[0], mobile_money: mode[1], credit: mode[2], facture: mode[3] }, nb_ventes: p.nb, panier_moyen: Math.round(ventes / p.nb),
      serie: p.serie.map(function (x) { return { libelle: x[0], ventes: x[1], charges: x[2] }; }),
      top_produits: TOP.map(function (x) { return { nom: x[0], total: Math.round(x[1] * p.facteur / 500) * 500 }; }),
      depenses_par_poste: postes
    };
  }
  function chiffresVide(periode) {
    var c = chiffres(periode);
    c.ventes = c.charges = c.benefice = c.stock = c.retraits_perso = c.tresorerie = c.nb_ventes = c.panier_moyen = 0;
    c.par_mode = { cash: 0, mobile_money: 0, credit: 0, facture: 0 };
    c.serie = c.serie.map(function (x) { return { libelle: x.libelle, ventes: 0, charges: 0 }; });
    c.top_produits = []; c.depenses_par_poste = [];
    return c;
  }

  /* ---------- accueil ---------- */
  function serie7j() {
    var v = [41000, 58000, 83000, 29000, 47000, 36500, 67500], s = [];
    for (var i = 6; i >= 0; i--) s.push({ jour: abrev(i), ventes: vide ? 0 : v[6 - i] });
    return s;
  }
  function accueil() {
    var impayes = somme(CLIENTS, "dette"), jours15 = ecart(prochain(15));
    var base = { gerante: "Marie", commerce: "Chez Marie", demo: true, date_locale: MK.fmt.dateLongue(iso(0, 12, 0)), serie_7j: serie7j(), non_lues: nbNonLues() };
    if (vide) {
      base.kpis = { ventes_jour: 0, nb_ventes_jour: 0, tresorerie: 0, benefice_mois: 0, impayes: 0 };
      base.alerte_principale = null; base.a_faire = []; base.activite_recente = [];
      return base;
    }
    base.kpis = { ventes_jour: 67500, nb_ventes_jour: 12, tresorerie: 845000, benefice_mois: 960000, impayes: impayes };
    base.alerte_principale = { id: 1, niveau: "urgent", titre: "Lycée Technique a 6 jours de retard", texte: "La facture n° 47 de 80 000 F n'est toujours pas payée. Veux-tu envoyer une relance ?", action: { ecran: "facture", params: { id: 7 } } };
    base.a_faire = [
      { id: "af1", type: "relance", titre: "Relancer le Lycée Technique", texte: "80 000 F attendus depuis 6 jours.", action: { ecran: "facture", params: { id: 7 } } },
      { id: "af2", type: "echeance", titre: "Déclaration mensuelle dans " + jours15 + " jours", texte: "À faire avant le " + MK.fmt.dateLongue(prochain(15)) + ".", action: { ecran: "documents", params: {} } },
      { id: "af3", type: "dossier", titre: "Dossier de crédit : encore 1 mois", texte: "5 mois de saisies sur les 6 demandés par les banques.", action: { ecran: "documents", params: {} } },
      { id: "af4", type: "info", titre: "Mme Biya te doit 12 000 F", texte: "Vente à crédit d'il y a 2 jours.", action: { ecran: "client", params: { id: 3 } } }
    ];
    base.activite_recente = HISTORIQUE.slice(0, 5).map(copie);
    return base;
  }

  /* ---------- tableau (existant, utilisé par la version stable) ---------- */
  function tableau() {
    var m = chiffres("mois"), j = chiffres("jour"), s = chiffres("semaine");
    return {
      commerce: "Chez Marie", demo: true,
      jour: { ventes: j.ventes, nb: j.nb_ventes, charges: j.charges, benefice: j.benefice },
      semaine: { ventes: s.ventes, nb: s.nb_ventes, charges: s.charges, benefice: s.benefice },
      mois: { ventes: m.ventes, nb: m.nb_ventes, charges: m.charges, benefice: m.benefice },
      tresorerie: 845000, benefice_mois: m.benefice, retraits_perso_mois: m.retraits_perso, impayes: somme(CLIENTS, "dette"),
      serie_7j: serie7j(), top_produits: m.top_produits.slice(0, 4),
      impayes_liste: [{ client: "Lycée Technique d'Essos", montant: 80000, detail: "facture n° 47" }, { client: "Cantine Mvog-Ada", montant: 36000, detail: "facture n° 48" }, { client: "Mme Biya", montant: 12000, detail: "vente à crédit" }],
      factures: FACTURES.slice(0, 3).map(function (f) { var r = resumeFacture(f); return { numero: r.numero, client: r.client, total: r.total, statut: r.statut, jours_retard: r.jours_retard }; }),
      echeance: { libelle: "Acompte IGS", date: prochain(15, 3).split("-").reverse().join("/"), jours: ecart(prochain(15, 3)) },
      impot: { estimation: 330000, note: "Estimation indicative, à confirmer avec la DGI" }, historique_mois: 5
    };
  }

  /* ---------- assistant (réponses scriptées) ---------- */
  var factureEnAttente = false;
  function chat(texte) {
    var t = String(texte || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
    var pmeInfo = { nom_commerce: "Chez Marie", ville: "Yaoundé" };
    function rep(reponses, documents) { return { reponses: reponses, documents: documents || [], pme: pmeInfo }; }
    if (/^(oui|ok|d'accord)$/.test(t)) {
      if (!factureEnAttente) return rep(["Je n'ai rien à confirmer pour l'instant. Dis-moi ce que tu veux faire."]);
      factureEnAttente = false;
      return rep(["C'est fait : la facture n° 49 de 75 000 F est prête pour le Lycée Technique. Je te la joins pour que tu la transfères à ton client."], [{ nom: "facture-049.pdf", url: pdf("Facture n 049 - Chez Marie") }]);
    }
    if (/^(non|annule|annuler)$/.test(t)) {
      var avait = factureEnAttente;
      factureEnAttente = false;
      return rep([avait ? "D'accord, je n'envoie rien. La facture n'est pas créée." : "Rien à annuler pour l'instant."]);
    }
    if (/facture/.test(t)) {
      factureEnAttente = true;
      return rep(["Voici ce que je prépare :\nFacture pour Lycée Technique d'Essos\n30 repas du jour × 2 500 F = 75 000 F\nTotal : 75 000 F\nJe crée la facture ? OUI / NON"]);
    }
    if (/dossier|credit|banque/.test(t)) {
      return rep(["Ton dossier de crédit est prêt à lire. Il vient uniquement de tes saisies : 5 mois sur 6 pour l'instant, donc les chiffres restent indicatifs."], [{ nom: "dossier-de-credit-chez-marie.pdf", url: pdf("Dossier de credit - Chez Marie") }]);
    }
    if (/doit|impaye|retard|relanc/.test(t)) {
      return rep(["Tes impayés : 128 000 F.\nLycée Technique d'Essos : 80 000 F (6 jours de retard)\nCantine Mvog-Ada : 36 000 F (pas encore échu)\nMme Biya : 12 000 F (vente à crédit)\nTu veux que je prépare une relance pour le Lycée ?"]);
    }
    if (/vendu|vente/.test(t)) {
      return rep(["C'est noté : 15 000 F en espèces. Total d'aujourd'hui : 82 500 F. Dis « annule » si tu t'es trompée."]);
    }
    if (/depense|achete|achat|paye/.test(t)) {
      return rep(["Dépense notée : 15 000 F, achats au marché. Ce mois-ci tu en es à 520 000 F de charges."]);
    }
    if (/faire|aide|aider|sais/.test(t)) {
      return rep(["Je peux noter tes ventes et tes dépenses, te dire combien tu as fait, préparer une facture, suivre qui te doit de l'argent et relancer tes clients. Écris-moi comme tu parles."]);
    }
    if (/bonjour|salut|coucou|bonsoir/.test(t)) return rep(["Bonjour Marie ! Aujourd'hui : 12 ventes, 67 500 F. Qu'est-ce que je note pour toi ?"]);
    if (/combien|fait|aujourd|bilan|resume/.test(t)) {
      return rep(["Aujourd'hui : 12 ventes, 67 500 F (40 000 F en espèces, 27 500 F en mobile money). Impayés en cours : 128 000 F."]);
    }
    return rep(["Je n'ai pas bien compris. Tu peux me dire par exemple « j'ai vendu 3 poulets à 3 500 », « combien j'ai fait aujourd'hui ? » ou « qui me doit ? »."]);
  }

  /* ---------- routeur ---------- */
  function erreur(status, message) { var e = new Error(message); e.status = status; return e; }
  function nombre(v, def) { var n = parseInt(v, 10); return isNaN(n) ? def : n; }
  function sans(s) { return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }

  function repondre(chemin, corps, methode) {
    var u = new URL(chemin, location.origin);
    var p = u.pathname.replace(/\/+$/, ""), q = u.searchParams, m;
    corps = corps || {};

    if (p === "/api/connexion" && methode === "POST") {
      var numero = String(corps.numero || "").replace(/\D/g, "");
      if (numero.length < 8 || numero.length > 15) throw erreur(422, "numéro invalide");
      return { token: "mock", numero: numero, pme: numero === "237699999999" ? null : { nom_commerce: "Chez Marie", ville: "Yaoundé" }, demo: true };
    }
    if (p === "/api/inscription" && methode === "POST") {
      ["nom_commerce", "ville", "secteur"].forEach(function (k) { if (!String(corps[k] || "").trim()) throw erreur(422, "Le champ « " + k.replace("_", " ") + " » est obligatoire."); });
      if (String(corps.nom_commerce).trim().toLowerCase() === "doublon") throw erreur(409, "Ce numéro a déjà un compte.");
      return { pme: { nom_commerce: String(corps.nom_commerce).trim(), ville: String(corps.ville).trim() } };
    }
    if (p === "/api/chat" && methode === "POST") return chat(corps.texte);
    if (p === "/api/tableau") return tableau();
    if (p === "/api/dossier") return { url: pdf("Dossier de credit - Chez Marie"), nom: "dossier-de-credit-chez-marie.pdf" };
    if (p === "/api/notifications") return { notifications: [], dernier: 42 };

    if (p === "/api/accueil") return accueil();

    if (p === "/api/alertes" && methode === "GET") return { non_lues: nbNonLues(), alertes: vide ? [] : copie(ALERTES) };
    if (p === "/api/alertes/lues" && methode === "POST") { ALERTES.forEach(function (a) { a.lue = true; }); return { non_lues: 0 }; }

    if (p === "/api/historique") {
      var type = q.get("type") || "tout", mot = sans(q.get("q")), limite = nombre(q.get("limite"), 30), avant = q.get("avant");
      var liste = vide ? [] : HISTORIQUE.filter(function (x) { return (type === "tout" || x.type === type) && (!mot || sans(x.titre + " " + x.detail + " " + (x.client || "")).indexOf(mot) >= 0); });
      if (avant) { var i = liste.map(function (x) { return x.id; }).indexOf(avant); liste = i >= 0 ? liste.slice(i + 1) : liste; }
      var page = liste.slice(0, limite);
      return { elements: copie(page), suivant: liste.length > limite ? page[page.length - 1].id : null };
    }
    if ((m = p.match(/^\/api\/historique\/([a-z]+)\/([\w-]+)$/))) {
      var cleEl = m[2].indexOf("-") >= 0 ? m[2] : m[1] + "-" + m[2];
      var trouve = HISTORIQUE.filter(function (x) { return x.id === cleEl; })[0];
      if (!trouve) throw erreur(404, "Opération introuvable.");
      var lignes = DETAIL_LIGNES[trouve.id] || [{ libelle: trouve.titre, quantite: 1, prix_unitaire: trouve.montant, montant: trouve.montant }];
      var notes = trouve.statut === "annule" ? ["Annulée par Marie après saisie."] : trouve.sens === "neutre" ? ["Pas encore encaissé : ce montant reste à recevoir."] : [];
      return { element: copie(trouve), lignes: copie(lignes), notes: notes, annulable: trouve.statut === "ok" && trouve.type !== "paiement" && base() - Date.parse(trouve.date) < 2 * 86400000 };
    }

    if (p === "/api/factures") {
      var st = q.get("statut") || "tout";
      return { factures: vide ? [] : FACTURES.filter(function (f) { return st === "tout" || f.statut === st; }).map(resumeFacture) };
    }
    if ((m = p.match(/^\/api\/factures\/(\d+)$/))) {
      var f = FACTURES.filter(function (x) { return String(x.id) === m[1]; })[0];
      if (!f || vide) throw erreur(404, "Facture introuvable.");
      return ficheFacture(f);
    }

    if (p === "/api/clients") return { clients: vide ? [] : copie(CLIENTS) };
    if ((m = p.match(/^\/api\/clients\/(\d+)$/))) {
      var c = CLIENTS.filter(function (x) { return String(x.id) === m[1]; })[0];
      if (!c || vide) throw erreur(404, "Client introuvable.");
      var duClient = HISTORIQUE.filter(function (x) { return x.client === c.nom; });
      return {
        client: copie(c),
        achats: copie(duClient.filter(function (x) { return x.type === "vente" || x.type === "facture"; })),
        factures: FACTURES.filter(function (x) { return x.client_id === c.id; }).map(function (x) { var r = resumeFacture(x); return { id: r.id, numero: r.numero, total: r.total, statut: r.statut }; }),
        paiements: copie(duClient.filter(function (x) { return x.type === "paiement"; })), dette: c.dette
      };
    }
    if (p === "/api/produits") return { produits: vide ? [] : copie(PRODUITS) };

    if (p === "/api/chiffres") return vide ? chiffresVide(q.get("periode")) : chiffres(q.get("periode") || "mois");

    if (p === "/api/documents") {
      var ca = chiffres("annee").ventes;
      return {
        dossier: { historique_mois: vide ? 0 : 5, requis: 6, manque_mois: vide ? 6 : 1, pret: false, fictives: true },
        impot: { estimation: Math.round(ca * 0.02), ca_annuel: ca, taux: 0.02, note: "Estimation indicative, à confirmer avec la DGI." },
        echeances: [
          { libelle: "Déclaration mensuelle", date: prochain(15), jours: ecart(prochain(15)) },
          { libelle: "Acompte IGS", date: prochain(15, 3), jours: ecart(prochain(15, 3)) }
        ]
      };
    }

    if (p === "/api/parametres") {
      if (methode === "PUT") {
        var com = corps.commerce || {}, pref = corps.preferences || {};
        Object.keys(com).forEach(function (k) {
          if (!(k in PARAMETRES.commerce) || k === "numero") return;
          var v = String(com[k] === null ? "" : com[k]).trim();
          if (v.length > 120) throw erreur(422, "« " + k.replace("_", " ") + " » est trop long (120 caractères au plus).");
          if (v === "" && (k === "nom_commerce" || k === "ville")) throw erreur(422, "« " + k.replace("_", " ") + " » ne peut pas être vide.");
        });
        if ("mode_relance" in pref && ["transfert", "direct"].indexOf(pref.mode_relance) < 0) throw erreur(422, "Mode d'envoi inconnu.");
        if ("seuil_confirmation_renforcee" in pref) {
          var seuil = Number(pref.seuil_confirmation_renforcee);
          if (!isFinite(seuil) || seuil < 1000 || seuil > 10000000) throw erreur(422, "Le seuil doit être compris entre 1 000 F et 10 000 000 F.");
          pref.seuil_confirmation_renforcee = Math.round(seuil);
        }
        Object.keys(com).forEach(function (k) { if (k in PARAMETRES.commerce && k !== "numero") PARAMETRES.commerce[k] = String(com[k] === null ? "" : com[k]).trim(); });
        Object.keys(pref).forEach(function (k) { if (k in PARAMETRES.preferences) PARAMETRES.preferences[k] = pref[k]; });
      }
      return copie(PARAMETRES);
    }

    if (p === "/api/connexions") {
      return { connexions: [
        { id: "whatsapp", nom: "WhatsApp", statut: "simule", detail: "Numéro de démonstration : les messages sont simulés dans l'application." },
        { id: "orange_money", nom: "Orange Money", statut: "bientot", detail: "Encaissement et suivi des paiements, bientôt disponible." },
        { id: "mtn_momo", nom: "MTN MoMo", statut: "bientot", detail: "Encaissement et suivi des paiements, bientôt disponible." },
        { id: "banque", nom: "Banque", statut: "bientot", detail: "Relevés pour ton dossier de crédit, prévu dans la feuille de route." },
        { id: "dgi", nom: "Impôts (DGI)", statut: "bientot", detail: "Déclarations en ligne, prévu dans la feuille de route." }
      ] };
    }

    if (p === "/api/recherche") {
      var mot2 = sans(q.get("q")).trim();
      if (mot2.length < 2 || vide) return { clients: [], produits: [], factures: [] };
      return {
        clients: CLIENTS.filter(function (x) { return sans(x.nom).indexOf(mot2) >= 0; }).map(function (x) { return { id: x.id, nom: x.nom, detail: (x.quartier || "Quartier inconnu") + (x.dette ? " · doit " + MK.fmt.fcfa(x.dette) : "") }; }),
        produits: PRODUITS.filter(function (x) { return sans(x.nom).indexOf(mot2) >= 0; }).map(function (x) { return { id: x.id, nom: x.nom, detail: MK.fmt.fcfa(x.prix) + " · " + x.ventes_30j + " vendus en 30 jours" }; }),
        factures: FACTURES.filter(function (x) { var r = resumeFacture(x); return sans(r.client).indexOf(mot2) >= 0 || String(r.numero).indexOf(mot2) >= 0; }).map(function (x) { var r = resumeFacture(x); return { id: r.id, numero: r.numero, client: r.client, total: r.total, statut: r.statut }; })
      };
    }

    throw erreur(404, "Route inconnue : " + p);
  }

  MK._mock = function (chemin, corps, methode) {
    return new Promise(function (resolve, reject) {
      setTimeout(function () {
        try {
          var p = new URL(chemin, location.origin).pathname;
          if (MK.cas === "erreur" && p !== "/api/connexion" && p !== "/api/inscription") throw erreur(500, "Le serveur ne répond pas pour le moment.");
          resolve(repondre(chemin, corps, methode));
        } catch (err) { reject(err); }
      }, LATENCE);
    });
  };
})();
