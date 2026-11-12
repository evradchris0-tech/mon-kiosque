"""Fonctionnalités du cahier « Je dois pouvoir… » pour la démo : dépenses, perso/pro, bilan, dossier, impôt, rappels, appli."""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import demo
from app.api.main import creer_app
from app.core.config import Parametres
from app.db.base import Base, creer_moteur, fabrique_sessions
from app.db.modeles import Client, Depense, Produit
from app.domaine import clients as dom_clients
from app.domaine import pme as dom_pme
from app.integrations.whatsapp.interface import MessageEntrant
from app.moki.schemas import Intention
from app.services import traiter_entrant_complet
from app.workers import rappels_fiscaux
from tests.conftest import NUM_A, NUM_B

F = " "


def n(m: int) -> str:
    return f"{m:,}".replace(",", F) + " F"


def test_b2_depense_et_c1_perso_c2_retrait_hors_charges(banc):
    banc.envoyer("j'ai vendu 3 paires à 10000 cash")
    r = banc.envoyer("j'ai payé 20 000 de loyer")
    assert n(20000) in r[0] and "loyer" in r[0] and "professionnelle" in r[0]
    bilan = banc.envoyer("mon bénéfice")[0]
    assert n(10000) in bilan  # bénéfice = 30 000 - 20 000 ; trésorerie aussi 10 000
    r = banc.envoyer("c'est perso")
    assert "retrait personnel" in r[0]
    bilan = banc.envoyer("mon bénéfice")[0]
    assert "Bénéfice du mois : " + n(30000) in bilan  # le retrait perso n'est plus une charge
    assert "Retraits personnels du mois : " + n(20000) in bilan
    assert "Trésorerie (argent disponible) : " + n(10000) in bilan  # l'argent sorti reste sorti


def test_depense_sans_montant_ou_sans_motif_pose_une_question(banc):
    assert "pour quoi" in banc.envoyer("j'ai payé 20000")[0].lower()
    with banc.session() as s:
        assert s.scalar(select(func.count(Depense.id))) == 0


def test_achat_de_stock_hors_benefice_mais_dans_la_tresorerie(banc):
    banc.envoyer("j'ai vendu 2 poulets à 5000 cash")
    banc.envoyer("j'ai acheté du stock 4000")
    bilan = banc.envoyer("mon bénéfice")[0]
    assert "Bénéfice du mois : " + n(10000) in bilan
    assert "Trésorerie (argent disponible) : " + n(6000) in bilan


def test_annuler_une_depense(banc):
    banc.envoyer("j'ai payé 20 000 de loyer")
    assert "Annulé" in banc.envoyer("annuler")[0]
    with banc.session() as s:
        assert s.scalars(select(Depense)).one().statut == "annulee"


def test_resume_donne_charges_et_benefice(banc):
    banc.envoyer("j'ai vendu 3 paires à 10000 cash")
    banc.envoyer("j'ai payé 20 000 de loyer")
    r = banc.envoyer("j'ai fait combien aujourd'hui ?")[0]
    assert n(30000) in r and "Charges : " + n(20000) in r and "Bénéfice estimé : " + n(10000) in r


def test_a3_modifier_et_supprimer_un_produit(banc):
    banc.envoyer("ajoute sandales rouges 7500")
    assert "8" in banc.envoyer("change le prix des sandales rouges à 8000")[0]
    with banc.session() as s:
        assert s.scalars(select(Produit)).one().prix == 8000
    assert "retiré" in banc.envoyer("supprime sandales rouges")[0]
    with banc.session() as s:
        assert s.scalars(select(Produit)).one().actif is False


def test_h1_impot_indicatif_avec_mention_dgi(banc):
    banc.envoyer("j'ai vendu 3 paires à 10000 cash")
    r = banc.envoyer("mon impôt")[0]
    assert "IGS" in r and "confirmer avec la DGI" in r and "Prochaine échéance" in r


def test_demande_de_conseil_fiscal_reste_refusee(banc):
    assert "pas formé pour ça" in banc.envoyer("je dois déclarer mes impôts comment ?")[0]


def test_h2_rappels_15_et_3_jours_une_seule_fois(banc):
    banc.horloge.fixer(datetime(2026, 11, 12, 8, 0))  # 3 jours avant le 15
    assert rappels_fiscaux.executer(banc.fabrique, banc.canal, banc.horloge) == 2
    assert rappels_fiscaux.executer(banc.fabrique, banc.canal, banc.horloge) == 0
    assert any("Rappel" in t for t in banc.canal.textes(NUM_A))
    banc.horloge.fixer(datetime(2026, 10, 31, 8, 0))  # 15 jours avant le 15 novembre
    assert rappels_fiscaux.executer(banc.fabrique, banc.canal, banc.horloge) == 2
    banc.horloge.fixer(datetime(2026, 11, 8, 8, 0))  # 7 jours : pas de rappel
    assert rappels_fiscaux.executer(banc.fabrique, banc.canal, banc.horloge) == 0


def test_g1_g2_g3_dossier_de_credit_pdf(banc):
    banc.envoyer("j'ai vendu 3 paires à 10000 cash")
    r = banc.envoyer("prépare mon dossier de crédit")
    assert "dossier de crédit est prêt" in r[0] and "il manque" in r[0]  # G3 : historique trop court
    chemin = banc.dernier.documents[0]
    from pathlib import Path

    assert Path(chemin).read_bytes()[:4] == b"%PDF"


def test_f2_f3_envoi_direct_au_client_apres_confirmation(banc):
    with banc.session() as s:
        pme = dom_pme.pme_par_numero(s, NUM_A)
        pme.mode_relance = "direct"
        dom_clients.ajouter(s, pme, "Mme Fouda", telephone="6 77 55 44 33")
        s.commit()

    def dire(texte):
        entrant = MessageEntrant(wamid=f"x.{texte}.{len(banc.canal.envoyes)}", numero=NUM_A, type="texte", heure_envoi=banc.horloge.maintenant(), texte=texte)
        return traiter_entrant_complet(banc.fabrique, banc.deps, entrant)[0]

    dire("facture pour Mme Fouda, 4 plats à 3000")
    assert not any(m.numero == "237677554433" for m in banc.canal.envoyes)  # rien avant le OUI
    r = dire("oui")
    assert any("✅ Envoyé à Mme Fouda" in t and "simulé" in t for t in r)
    envoi = [m for m in banc.canal.envoyes if m.numero == "237677554433"]
    assert len(envoi) == 1 and envoi[0].document.endswith(".pdf") and "Paiement" in envoi[0].texte
    dire("relance Mme Fouda")
    assert len([m for m in banc.canal.envoyes if m.numero == "237677554433"]) == 1  # rien avant le OUI
    dire("oui")
    assert len([m for m in banc.canal.envoyes if m.numero == "237677554433"]) == 2


def test_e1_qui_me_doit_trie_par_montant_et_retard(banc):
    with banc.session() as s:
        from app.domaine.pme import pme_par_numero
        pme = pme_par_numero(s, NUM_A)
        dom_clients.ajouter(s, pme, "Mme Biya")
        dom_clients.ajouter(s, pme, "Mme Fouda")
        s.commit()
    banc.envoyer("Mme Biya a pris 2 poulets à 4000, elle paie demain")
    banc.envoyer("Mme Fouda a pris 3 poulets à 4000, elle paie demain")
    texte = banc.envoyer("qui me doit ?")[0]
    assert texte.index("Mme Fouda") < texte.index("Mme Biya")  # 12 000 avant 8 000


def test_appli_web_donnees_de_demo_coherentes_et_etanches(banc, tmp_path):
    moteur = creer_moteur("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(moteur)
    fabrique = fabrique_sessions(moteur)
    p = Parametres(env="dev", acces_demo=True, demo_seed=True, dossier_factures=str(tmp_path / "f"), console_utilisateur="u", console_mot_de_passe="m")
    c = TestClient(creer_app(p, fabrique, banc.deps))
    assert c.get("/app").status_code == 200 and "Mon Kiosque" in c.get("/app").text
    assert c.get("/qr.png").content[:4] == b"\x89PNG"
    assert c.get("/api/tableau").status_code == 401

    jeton = c.post("/api/connexion", json={"numero": demo.NUMERO_DEMO}).json()["token"]
    h = {"Authorization": f"Bearer {jeton}"}
    t = c.get("/api/tableau", headers=h).json()
    assert t["demo"] is True and t["historique_mois"] >= 6 and t["tresorerie"] > 0
    assert t["benefice_mois"] == t["mois"]["benefice"] == t["mois"]["ventes"] - t["mois"]["charges"]
    assert len(t["serie_7j"]) == 7 and t["impayes"] == sum(i["montant"] for i in t["impayes_liste"])
    # D1/D7 : le chat donne les mêmes chiffres que le tableau
    r = c.post("/api/chat", headers=h, json={"texte": "j'ai fait combien ce mois ?"}).json()["reponses"][0]
    assert n(t["mois"]["ventes"]) in r and n(t["mois"]["benefice"]) in r
    # le chat modifie réellement le tableau
    avant = c.get("/api/tableau", headers=h).json()["tresorerie"]
    c.post("/api/chat", headers=h, json={"texte": "j'ai payé 20 000 de loyer"})
    assert c.get("/api/tableau", headers=h).json()["tresorerie"] == avant - 20000
    # dossier PDF
    d = c.get("/api/dossier", headers=h).json()
    pdf = c.get(d["url"])
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    # étanchéité : un autre commerce ne peut pas lire ce fichier
    with fabrique() as s:
        dom_pme.creer_pme(s, banc.horloge, nom_commerce="Autre", numero_whatsapp=NUM_B)
        s.commit()
    autre = c.post("/api/connexion", json={"numero": NUM_B}).json()["token"]
    assert c.get(f"/api/fichier?nom={d['nom']}", headers={"Authorization": f"Bearer {autre}"}).status_code == 404
    assert c.get("/api/fichier?nom=../../x.pdf", headers=h).status_code == 400


def test_appli_web_inscription_nouveau_numero(banc, tmp_path):
    moteur = creer_moteur("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(moteur)
    fabrique = fabrique_sessions(moteur)
    c = TestClient(creer_app(Parametres(env="dev", acces_demo=True, dossier_factures=str(tmp_path / "f")), fabrique, banc.deps))
    j = c.post("/api/connexion", json={"numero": "237655000111"}).json()
    assert j["pme"] is None
    h = {"Authorization": f"Bearer {j['token']}"}
    assert c.get("/api/tableau", headers=h).status_code == 404
    assert "Bienvenue" in c.post("/api/chat", headers=h, json={"texte": "Bonjour"}).json()["reponses"][0]
    c.post("/api/chat", headers=h, json={"texte": "Chez Paul"})
    c.post("/api/chat", headers=h, json={"texte": "Douala"})
    ok = c.post("/api/chat", headers=h, json={"texte": "boutique"}).json()
    assert "ouvert" in ok["reponses"][0] and ok["pme"]["nom_commerce"] == "Chez Paul"
    assert c.get("/api/tableau", headers=h).status_code == 200
    # un numéro = un compte
    with fabrique() as s:
        assert s.scalar(select(func.count(Client.id))) == 0


def test_connexion_demo_desactivee_par_defaut(banc, tmp_path):
    moteur = creer_moteur("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(moteur)
    c = TestClient(creer_app(Parametres(env="dev", dossier_factures=str(tmp_path)), fabrique_sessions(moteur), banc.deps))
    assert c.post("/api/connexion", json={"numero": "237655000111"}).status_code == 403


def test_intentions_nouvelles_connues():
    assert {Intention.DEPENSE, Intention.BILAN, Intention.DOSSIER_CREDIT, Intention.IMPOT, Intention.CHANGER_NATURE, Intention.ECHEANCES}


def test_nouvelle_phrase_pendant_une_confirmation_n_est_pas_avalee(banc):
    banc.envoyer("j'ai vendu 2 télévisions à 400000 cash")  # demande une confirmation (montant élevé)
    r = banc.envoyer("j'ai payé 20 000 de loyer")
    assert any("dépense de" in t for t in r)
    with banc.session() as s:
        assert s.scalar(select(func.count(Depense.id))) == 1
        from app.db.modeles import Vente
        assert s.scalar(select(func.count(Vente.id))) == 0  # la vente en attente n'a pas été enregistrée


def test_c_est_perso_ne_touche_pas_une_depense_ancienne(banc):
    banc.envoyer("j'ai payé 20 000 de loyer")
    banc.horloge.avancer(hours=2)
    assert "pas de dépense récente" in banc.envoyer("c'est perso")[0]
    with banc.session() as s:
        assert s.scalars(select(Depense)).one().nature == "pro"


def test_f4_etat_des_factures_dans_le_chat(banc):
    with banc.session() as s:
        dom_clients.ajouter(s, dom_pme.pme_par_numero(s, NUM_A), "Mme Fouda")
        s.commit()
    assert "pas encore de facture" in banc.envoyer("mes factures")[0]
    banc.envoyer("facture pour Mme Fouda, 4 plats à 3000")
    banc.envoyer("oui")
    r = banc.envoyer("mes factures")[0]
    assert "n° 001" in r and "Mme Fouda" in r and "envoyée" in r
    banc.horloge.avancer(days=10)
    assert "en retard (10 j)" in banc.envoyer("quelles factures sont en retard ?")[0]
    banc.envoyer("Mme Fouda a payé")
    banc.envoyer("oui")
    assert "payée" in banc.envoyer("mes factures")[0]


def test_b6_produit_inconnu_pose_une_question_puis_ajoute_au_catalogue(banc):
    banc.envoyer("ajoute poulet DG 4000")
    r = banc.envoyer("j'ai vendu 2 sandales à 7500 cash")
    assert "Je ne connais pas encore « sandales »" in r[0] and "OUI / NON" in r[0]
    with banc.session() as s:
        from app.db.modeles import Vente
        assert s.scalar(select(func.count(Vente.id))) == 0  # rien n'est enregistré avant la réponse
    assert n(15000) in banc.envoyer("oui")[0]
    with banc.session() as s:
        assert {p.nom for p in s.scalars(select(Produit))} == {"poulet DG", "sandales"}


def test_b6_produit_connu_ou_catalogue_vide_ne_pose_pas_de_question(banc):
    assert "Je ne connais pas" not in banc.envoyer("j'ai vendu 2 sandales à 7500 cash")[0]  # catalogue vide
    banc.envoyer("ajoute poulet DG 4000")
    assert n(8000) in banc.envoyer("j'ai vendu 2 poulets à 4000 cash")[0]  # « poulets » = « poulet DG »


def test_b6_produit_inconnu_refus_n_enregistre_rien(banc):
    banc.envoyer("ajoute poulet DG 4000")
    banc.envoyer("j'ai vendu 2 sandales à 7500 cash")
    banc.envoyer("non")
    with banc.session() as s:
        from app.db.modeles import Vente
        assert s.scalar(select(func.count(Vente.id))) == 0
        assert {p.nom for p in s.scalars(select(Produit))} == {"poulet DG"}


def test_d6_h2_declenchement_manuel_notifications_et_planificateur(banc, tmp_path):
    moteur = creer_moteur("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(moteur)
    fabrique = fabrique_sessions(moteur)
    p = Parametres(env="dev", acces_demo=True, planificateur=True, dossier_factures=str(tmp_path / "f"), console_utilisateur="u", console_mot_de_passe="m")
    with fabrique() as s:
        dom_pme.creer_pme(s, banc.horloge, nom_commerce="Chez Marie", numero_whatsapp=NUM_A)
        s.commit()
    banc.horloge.fixer(datetime(2026, 11, 12, 8, 0))  # 3 jours avant le 15 : rappel fiscal attendu
    with TestClient(creer_app(p, fabrique, banc.deps)) as c:  # `with` démarre le planificateur sans le casser
        jeton = c.post("/api/connexion", json={"numero": NUM_A}).json()["token"]
        h = {"Authorization": f"Bearer {jeton}"}
        curseur = c.get("/api/notifications", headers=h).json()["dernier"]
        assert c.post("/console/declencher/resume").status_code == 401
        assert c.post("/console/declencher/resume", auth=("u", "m")).json()["envoyes"] == 1
        assert c.post("/console/declencher/resume", auth=("u", "m")).json()["envoyes"] == 0  # une seule fois
        assert c.post("/console/declencher/rappels", auth=("u", "m")).json()["envoyes"] == 1
        assert c.post("/console/declencher/inconnu", auth=("u", "m")).status_code == 404
        notifs = c.get(f"/api/notifications?apres={curseur}", headers=h).json()["notifications"]
        assert len(notifs) == 2 and any("Résumé du soir" in x["texte"] for x in notifs) and any("Rappel" in x["texte"] for x in notifs)
        assert c.get(f"/api/notifications?apres={c.get('/api/notifications', headers=h).json()['dernier']}", headers=h).json()["notifications"] == []


def test_pwa_manifeste_service_worker_icones_et_jeton_sans_etat(banc, tmp_path):
    def appli():
        moteur = creer_moteur("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(moteur)
        p = Parametres(env="dev", acces_demo=True, demo_seed=True, secret_jeton="secret-fixe", dossier_factures=str(tmp_path / "f"))
        return TestClient(creer_app(p, fabrique_sessions(moteur), banc.deps))

    a, b = appli(), appli()  # deux « instances » distinctes
    m = a.get("/manifest.webmanifest")
    assert m.status_code == 200 and m.json()["display"] == "standalone" and len(m.json()["icons"]) == 3
    assert "serviceWorker" not in a.get("/sw.js").text and "mon-kiosque" in a.get("/sw.js").text
    assert a.get("/icons/icon-512.png").content[:4] == b"\x89PNG" and a.get("/icons/../x.png").status_code in (404, 422)
    assert 'rel="manifest"' in a.get("/app").text
    jeton = a.post("/api/connexion", json={"numero": demo.NUMERO_DEMO}).json()["token"]
    assert b.get("/api/tableau", headers={"Authorization": f"Bearer {jeton}"}).status_code == 200  # jeton valable partout
    assert b.get("/api/tableau", headers={"Authorization": "Bearer " + jeton[:-2] + "00"}).status_code == 401  # jeton falsifié refusé
    assert b.get("/qr.png", headers={"host": "mon-kiosque.vercel.app"}).content[:4] == b"\x89PNG"
