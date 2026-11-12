"""API des écrans v2 (docs/06-interface-pro.md §5) : formes, 401, étanchéité entre PME, cohérence des chiffres, validations."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select

from app.api.main import creer_app
from app.core.config import Parametres
from app.db.base import Base, creer_moteur, fabrique_sessions
from app.db.modeles import Client, Confirmation, Depense, Facture, Message, NumeroAutorise, Paiement, Pme, Preference, Produit, Vente
from app.domaine import clients as dom_clients
from app.domaine import factures as dom_factures
from app.domaine import pme as dom_pme
from app.workers import resume_du_soir
from tests.conftest import NUM_A, NUM_B

NUM_NOUVEAU = "237655000999"
FIN = " "  # espace fine insécable des montants


def fcfa(n: int) -> str:
    return f"{n:,}".replace(",", FIN) + " F"

CLES_ELEMENT = {"id", "type", "date", "titre", "detail", "montant", "sens", "statut", "client"}
CLES_CLIENT = {"id", "nom", "telephone", "quartier", "dette", "nb_achats", "total_achats", "dernier_achat", "inactif"}
ROUTES_PROTEGEES = [
    ("POST", "/api/inscription", {"nom_commerce": "X", "ville": "Y", "secteur": "Z"}),
    ("GET", "/api/accueil", None), ("GET", "/api/alertes", None), ("POST", "/api/alertes/lues", {}),
    ("GET", "/api/historique", None), ("GET", "/api/historique/vente/1", None),
    ("GET", "/api/factures", None), ("GET", "/api/factures/1", None),
    ("GET", "/api/clients", None), ("GET", "/api/clients/1", None), ("GET", "/api/produits", None),
    ("GET", "/api/chiffres", None), ("GET", "/api/documents", None),
    ("GET", "/api/parametres", None), ("PUT", "/api/parametres", {}),
    ("GET", "/api/connexions", None), ("GET", "/api/recherche?q=abc", None),
]


def fabriquer(banc, tmp_path, *, demo_seed: bool) -> SimpleNamespace:
    moteur = creer_moteur("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(moteur)
    fabrique = fabrique_sessions(moteur)
    p = Parametres(env="dev", acces_demo=True, demo_seed=demo_seed, secret_jeton="secret-fixe", dossier_factures=banc.deps.parametres.dossier_factures, console_utilisateur="u", console_mot_de_passe="m")
    c = TestClient(creer_app(p, fabrique, banc.deps))

    def jeton(numero: str) -> dict:
        return {"Authorization": "Bearer " + c.post("/api/connexion", json={"numero": numero}).json()["token"]}

    return SimpleNamespace(c=c, fabrique=fabrique, moteur=moteur, jeton=jeton, banc=banc, p=p)


@pytest.fixture
def app_demo(banc, tmp_path):
    """Base de démo « Chez Marie » (NUM_A) au jeudi 12 novembre 2026."""
    banc.horloge.fixer(datetime(2026, 11, 12, 9, 0))
    a = fabriquer(banc, tmp_path, demo_seed=True)
    a.h = a.jeton(NUM_A)
    return a


@pytest.fixture
def app_banc(banc, tmp_path):
    """Base vide avec deux PME (A = Chez Marie, B = Boutique Paul) pour les cas contrôlés ; horloge pilotable via banc.horloge."""
    a = fabriquer(banc, tmp_path, demo_seed=False)
    with a.fabrique() as s:
        dom_pme.creer_pme(s, banc.horloge, nom_commerce="Chez Marie", numero_whatsapp=NUM_A, nom_gerante="Marie Nkoulou", ville="Yaoundé")
        dom_pme.creer_pme(s, banc.horloge, nom_commerce="Boutique Paul", numero_whatsapp=NUM_B, ville="Douala")
        s.commit()
    a.h, a.hb = a.jeton(NUM_A), a.jeton(NUM_B)
    return a


def pme_de(s, numero: str) -> Pme:
    return dom_pme.pme_par_numero(s, numero)


def ajouter_facture(s, h, pme, client, jours: int, *, statut: str = "envoyee", quantite: int = 2, prix: int = 5000, echeance=None) -> Facture:
    maintenant = h.maintenant()
    conf = Confirmation(pme_id=pme.id, action={"test": True}, mode="simple", demandee_a=maintenant, confirmee_a=maintenant, statut="confirmee")
    s.add(conf)
    s.flush()
    f = dom_factures.creer(s, pme, h, client=client, lignes=[{"produit": "repas", "quantite": quantite, "prix_unitaire": prix}], frais=[], confirmation_id=conf.id, echeance=echeance)
    f.creee_a = maintenant - timedelta(days=jours)
    f.statut = statut
    s.flush()
    return f


def ajouter_vente(s, pme, instant: datetime, *, produit: str = "Poulet DG", total: int = 4000, mode: str = "cash", client: Client | None = None) -> Vente:
    v = Vente(pme_id=pme.id, heure_envoi=instant, heure_reception=instant, lignes=[{"produit": produit, "quantite": 1, "prix_unitaire": total}], total=total,
              parts_paiement=[{"mode": mode, "montant": total}], client_id=client.id if client else None, credit_restant=total if mode == "credit" else 0, statut="active")
    s.add(v)
    s.flush()
    return v


def ajouter_depense(s, pme, instant: datetime, libelle: str, montant: int, type_: str = "charge") -> Depense:
    d = Depense(pme_id=pme.id, libelle=libelle, montant=montant, type=type_, nature="perso" if type_ == "retrait_perso" else "pro", heure_envoi=instant, heure_reception=instant)
    s.add(d)
    s.flush()
    return d


@contextmanager
def compter_requetes(moteur):
    nb = []
    ecouteur = lambda *a, **k: nb.append(1)  # noqa: E731
    event.listen(moteur, "before_cursor_execute", ecouteur)
    try:
        yield nb
    finally:
        event.remove(moteur, "before_cursor_execute", ecouteur)


# ───────────────────────── authentification ─────────────────────────


@pytest.mark.parametrize(("methode", "url", "corps"), ROUTES_PROTEGEES)
def test_toutes_les_routes_refusent_sans_jeton_ou_avec_un_faux_jeton(app_banc, methode, url, corps):
    c = app_banc.c
    assert c.request(methode, url, json=corps).status_code == 401
    assert c.request(methode, url, json=corps, headers={"Authorization": "Bearer 237677000001.faux"}).status_code == 401


def test_compte_non_inscrit_recoit_404_partout_sauf_inscription(app_banc):
    h = app_banc.jeton(NUM_NOUVEAU)
    for url in ["/api/accueil", "/api/alertes", "/api/historique", "/api/factures", "/api/clients", "/api/produits", "/api/chiffres", "/api/documents", "/api/parametres", "/api/connexions", "/api/recherche?q=abc"]:
        assert app_banc.c.get(url, headers=h).status_code == 404, url
    assert app_banc.c.post("/api/alertes/lues", headers=h, json={}).status_code == 404
    assert app_banc.c.put("/api/parametres", headers=h, json={}).status_code == 404


# ───────────────────────── inscription ─────────────────────────


def test_inscription_cree_la_pme_du_numero_du_jeton_puis_409(app_banc):
    c, h = app_banc.c, app_banc.jeton(NUM_NOUVEAU)
    r = c.post("/api/inscription", headers=h, json={"nom_commerce": "  Chez Paul ", "ville": "Douala", "secteur": "Boutique", "numero": NUM_B, "pme_id": 1})
    assert r.status_code == 200 and r.json() == {"pme": {"nom_commerce": "Chez Paul", "ville": "Douala"}}
    with app_banc.fabrique() as s:
        pme = pme_de(s, NUM_NOUVEAU)  # le numéro vient du jeton, jamais du corps
        assert pme.nom_commerce == "Chez Paul" and pme.secteur == "Boutique" and pme.id not in (1, 2)
        assert s.scalar(select(func.count(NumeroAutorise.id)).where(NumeroAutorise.numero == NUM_NOUVEAU)) == 1
        assert pme_de(s, NUM_B).nom_commerce == "Boutique Paul"
    assert c.get("/api/accueil", headers=h).status_code == 200
    again = c.post("/api/inscription", headers=h, json={"nom_commerce": "Autre", "ville": "Douala", "secteur": "Boutique"})
    assert again.status_code == 409 and isinstance(again.json()["detail"], str)
    assert c.post("/api/inscription", headers=app_banc.h, json={"nom_commerce": "A", "ville": "B", "secteur": "C"}).status_code == 409  # compte existant


@pytest.mark.parametrize("corps", [
    {}, None, [], "texte", {"nom_commerce": "X", "ville": "Y"}, {"nom_commerce": "", "ville": "Y", "secteur": "Z"},
    {"nom_commerce": "   ", "ville": "Y", "secteur": "Z"}, {"nom_commerce": 12, "ville": "Y", "secteur": "Z"},
    {"nom_commerce": "X" * 121, "ville": "Y", "secteur": "Z"}, {"nom_commerce": "X", "ville": "Y" * 61, "secteur": "Z"}, {"nom_commerce": "X", "ville": "Y", "secteur": "Z" * 41},
])
def test_inscription_champ_vide_ou_trop_long_donne_422_en_francais(app_banc, corps):
    h = app_banc.jeton(NUM_NOUVEAU)
    r = app_banc.c.post("/api/inscription", headers=h, json=corps)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and r.json()["detail"]
    with app_banc.fabrique() as s:
        assert pme_de(s, NUM_NOUVEAU) is None  # rien n'est créé


# ───────────────────────── accueil ─────────────────────────


def test_accueil_forme_et_chiffres_identiques_au_tableau(app_demo):
    c, h = app_demo.c, app_demo.h
    a, t = c.get("/api/accueil", headers=h).json(), c.get("/api/tableau", headers=h).json()
    assert set(a) == {"gerante", "commerce", "demo", "date_locale", "kpis", "alerte_principale", "a_faire", "serie_7j", "activite_recente", "non_lues"}
    assert (a["gerante"], a["commerce"], a["demo"], a["date_locale"]) == ("Marie", "Chez Marie", True, "jeudi 12 novembre")
    assert set(a["kpis"]) == {"ventes_jour", "nb_ventes_jour", "tresorerie", "benefice_mois", "impayes"}
    assert a["kpis"]["ventes_jour"] == t["jour"]["ventes"] > 0 and a["kpis"]["nb_ventes_jour"] == t["jour"]["nb"]
    assert a["kpis"]["tresorerie"] == t["tresorerie"] and a["kpis"]["benefice_mois"] == t["benefice_mois"] and a["kpis"]["impayes"] == t["impayes"] == 106000
    assert a["serie_7j"] == t["serie_7j"]
    assert len(a["activite_recente"]) == 5 and all(set(e) == CLES_ELEMENT for e in a["activite_recente"])
    assert a["non_lues"] == c.get("/api/alertes", headers=h).json()["non_lues"] == 2
    principale = a["alerte_principale"]
    assert set(principale) == {"id", "niveau", "titre", "texte", "action"} and principale["niveau"] == "urgent"
    assert a["a_faire"] and all(set(x) == {"id", "type", "titre", "texte", "action"} and x["type"] in ("relance", "echeance", "dossier", "info") for x in a["a_faire"])
    assert all(x["action"] is None or set(x["action"]) == {"ecran", "params"} for x in a["a_faire"])


def test_accueil_sans_gerante_ni_donnees(app_banc):
    app_banc.banc.horloge.fixer(datetime(2026, 10, 20, 9, 0))  # loin de toute échéance fiscale
    h = app_banc.jeton(NUM_NOUVEAU)
    app_banc.c.post("/api/inscription", headers=h, json={"nom_commerce": "Neuf", "ville": "Douala", "secteur": "Boutique"})
    a = app_banc.c.get("/api/accueil", headers=h).json()
    assert a["gerante"] is None and a["activite_recente"] == [] and a["kpis"]["ventes_jour"] == 0 and a["alerte_principale"] is None
    assert any(x["type"] == "info" for x in a["a_faire"])  # « aucune vente notée aujourd'hui »


def test_accueil_alerte_principale_disparait_une_fois_les_alertes_lues(app_demo):
    c, h = app_demo.c, app_demo.h
    assert c.post("/api/alertes/lues", headers=h, json={}).json() == {"non_lues": 0}
    a = c.get("/api/accueil", headers=h).json()
    assert a["alerte_principale"] is None and a["non_lues"] == 0


# ───────────────────────── alertes ─────────────────────────


def alertes_de(app, headers, type_: str | None = None) -> list[dict]:
    r = app.c.get("/api/alertes", headers=headers)
    assert r.status_code == 200
    return [a for a in r.json()["alertes"] if type_ is None or a["type"] == type_]


def test_alertes_forme(app_demo):
    r = app_demo.c.get("/api/alertes", headers=app_demo.h).json()
    assert set(r) == {"non_lues", "alertes"} and r["non_lues"] == sum(1 for a in r["alertes"] if not a["lue"])
    for a in r["alertes"]:
        assert set(a) == {"id", "type", "niveau", "titre", "texte", "date", "lue", "action"}
        assert a["type"] in ("retard", "echeance", "resume", "charge", "client", "info") and a["niveau"] in ("urgent", "attention", "info")
        datetime.fromisoformat(a["date"])
        assert a["action"] is None or set(a["action"]) == {"ecran", "params"}
    ordre = [{"urgent": 0, "attention": 1, "info": 2}[a["niveau"]] for a in r["alertes"]]
    assert ordre == sorted(ordre)  # les plus graves d'abord


def test_alerte_facture_en_retard_au_dela_de_7_jours(app_banc):
    with app_banc.fabrique() as s:
        pme = pme_de(s, NUM_A)
        client = dom_clients.ajouter(s, pme, "Mme Fouda")
        recente = ajouter_facture(s, app_banc.banc.horloge, pme, client, 7)  # 7 jours : pas encore en retard
        s.commit()
        id_recente = recente.id
    assert alertes_de(app_banc, app_banc.h, "retard") == []
    with app_banc.fabrique() as s:
        ancienne = ajouter_facture(s, app_banc.banc.horloge, pme_de(s, NUM_A), s.scalar(select(Client)), 8)
        s.commit()
        id_ancienne = ancienne.id
    (a,) = alertes_de(app_banc, app_banc.h, "retard")
    assert a["id"] == f"retard-facture-{id_ancienne}" and a["niveau"] == "urgent" and a["lue"] is False
    assert a["action"] == {"ecran": "facture", "params": {"id": id_ancienne}} and "Mme Fouda" in a["texte"] and fcfa(10000) in a["texte"]
    assert id_recente != id_ancienne
    assert alertes_de(app_banc, app_banc.h, "retard")[0]["id"] == a["id"]  # identifiant stable d'un appel à l'autre


def test_alerte_echeance_fiscale_attention_puis_urgent(app_banc):
    h = app_banc.banc.horloge
    h.fixer(datetime(2026, 10, 20, 9, 0))  # 26 jours avant le 15 novembre
    assert alertes_de(app_banc, app_banc.h, "echeance") == []
    h.fixer(datetime(2026, 11, 5, 9, 0))  # 10 jours
    (a,) = alertes_de(app_banc, app_banc.h, "echeance")
    assert a["id"] == "echeance-2026-11-15" and a["niveau"] == "attention" and a["action"] == {"ecran": "documents", "params": {}}
    h.fixer(datetime(2026, 11, 12, 9, 0))  # 3 jours
    (a,) = alertes_de(app_banc, app_banc.h, "echeance")
    assert a["id"] == "echeance-2026-11-15" and a["niveau"] == "urgent"
    h.fixer(datetime(2027, 3, 5, 9, 0))  # le 15 mars : déclaration mensuelle ET IGS, deux alertes distinctes
    ids = {a["id"] for a in alertes_de(app_banc, app_banc.h, "echeance")}
    assert len(ids) == 2 and "echeance-2027-03-15" in ids


def test_alerte_resume_du_soir_dans_les_24_heures(app_banc):
    h = app_banc.banc.horloge
    h.fixer(datetime(2026, 11, 10, 18, 30))  # 19 h 30 à Douala
    assert resume_du_soir.executer(app_banc.fabrique, app_banc.banc.canal, h, 19) == 2
    (a,) = alertes_de(app_banc, app_banc.h, "resume")
    (b,) = alertes_de(app_banc, app_banc.hb, "resume")
    assert a["niveau"] == "info" and a["id"].startswith("resume-") and a["id"] != b["id"] and a["texte"]
    with app_banc.fabrique() as s:
        message = s.scalar(select(Message).where(Message.pme_id == pme_de(s, NUM_A).id, Message.type == "notification"))
        assert a["id"] == f"resume-{message.id}" and a["date"] == message.heure_reception.isoformat()
    h.avancer(hours=25)
    assert alertes_de(app_banc, app_banc.h, "resume") == []


def alerte_charge_cas(app, *, novembre: int, mois_precedents: tuple[int, ...] = (100_000, 100_000, 100_000), type_: str = "charge", libelle: str = "loyer"):
    app.banc.horloge.fixer(datetime(2026, 11, 20, 9, 0))
    with app.fabrique() as s:
        pme = pme_de(s, NUM_A)
        for mois, montant in zip((10, 9, 8), mois_precedents, strict=False):
            if montant:
                ajouter_depense(s, pme, datetime(2026, mois, 5, 9), libelle, montant, type_)
        ajouter_depense(s, pme, datetime(2026, 11, 5, 9), libelle, novembre, type_)
        s.commit()
    return alertes_de(app, app.h, "charge")


def test_alerte_charge_au_dessus_de_30_pour_cent_de_la_moyenne(app_banc):
    (a,) = alerte_charge_cas(app_banc, novembre=140_000)
    assert a["niveau"] == "attention" and a["id"] == "charge-loyer-2026-11" and a["date"] == "2026-11-05T09:00:00"
    assert "40 %" in a["texte"] and a["action"] == {"ecran": "chiffres", "params": {"periode": "mois"}}


def test_alerte_charge_pas_a_30_pour_cent_pile(app_banc):
    assert alerte_charge_cas(app_banc, novembre=130_000) == []  # « plus de 30 % » : 30 % exactement ne suffit pas


def test_alerte_charge_sans_historique_suffisant_ou_hors_charges(app_banc):
    assert alerte_charge_cas(app_banc, novembre=500_000, mois_precedents=(100_000, 0, 0)) == []  # un seul mois de référence


def test_alerte_charge_ignore_les_retraits_perso_et_les_achats_de_stock(app_banc):
    assert alerte_charge_cas(app_banc, novembre=500_000, type_="retrait_perso") == []


def test_alerte_charge_moyenne_sur_les_mois_avec_depense(app_banc):
    (a,) = alerte_charge_cas(app_banc, novembre=140_000, mois_precedents=(100_000, 0, 100_000))
    assert a["id"] == "charge-loyer-2026-11"  # moyenne = 100 000 sur les 2 mois où le loyer existe


def test_alerte_client_inactif_depuis_plus_de_30_jours(app_banc):
    h = app_banc.banc.horloge
    with app_banc.fabrique() as s:
        pme = pme_de(s, NUM_A)
        actif, ancien = dom_clients.ajouter(s, pme, "Mme Biya"), dom_clients.ajouter(s, pme, "M. Kamto")
        ajouter_vente(s, pme, h.maintenant() - timedelta(days=20), client=actif)
        ajouter_vente(s, pme, h.maintenant() - timedelta(days=31), client=ancien)
        s.commit()
        id_ancien = ancien.id
    (a,) = alertes_de(app_banc, app_banc.h, "client")
    assert a["id"] == f"client-inactif-{id_ancien}" and a["niveau"] == "info" and a["action"] == {"ecran": "client", "params": {"id": id_ancien}}
    fiche = app_banc.c.get(f"/api/clients/{id_ancien}", headers=app_banc.h).json()["client"]
    assert fiche["inactif"] is True


def test_marquer_les_alertes_lues_puis_nouvelle_alerte_non_lue(app_banc):
    h = app_banc.banc.horloge
    h.fixer(datetime(2026, 10, 20, 9, 0))  # loin de toute échéance fiscale
    with app_banc.fabrique() as s:
        pme = pme_de(s, NUM_A)
        client = dom_clients.ajouter(s, pme, "Mme Fouda")
        ancienne = ajouter_facture(s, h, pme, client, 12)  # déjà en retard
        ajouter_facture(s, h, pme, client, 5)  # le sera dans 4 jours
        s.commit()
        id_ancienne = ancienne.id
    r = app_banc.c.get("/api/alertes", headers=app_banc.h).json()
    assert r["non_lues"] >= 1 and all(a["lue"] is False for a in r["alertes"])
    assert app_banc.c.post("/api/alertes/lues", headers=app_banc.h, json={}).json() == {"non_lues": 0}
    r = app_banc.c.get("/api/alertes", headers=app_banc.h).json()
    assert r["non_lues"] == 0 and r["alertes"] and all(a["lue"] is True for a in r["alertes"])
    assert app_banc.c.get("/api/alertes", headers=app_banc.hb).json()["non_lues"] == 0 and app_banc.c.get("/api/accueil", headers=app_banc.h).json()["non_lues"] == 0
    h.avancer(days=4)  # la seconde facture passe à 9 jours de retard : nouvelle alerte, non lue
    r = app_banc.c.get("/api/alertes", headers=app_banc.h).json()
    assert r["non_lues"] == 1
    assert {a["id"]: a["lue"] for a in r["alertes"] if a["type"] == "retard"}[f"retard-facture-{id_ancienne}"] is True
    assert app_banc.c.post("/api/alertes/lues", headers=app_banc.h).json() == {"non_lues": 0}  # le corps est facultatif


def test_marquer_lu_chez_une_pme_n_affecte_pas_l_autre(app_banc):
    h = app_banc.banc.horloge
    h.fixer(datetime(2026, 10, 20, 9, 0))
    with app_banc.fabrique() as s:
        for numero in (NUM_A, NUM_B):
            pme = pme_de(s, numero)
            ajouter_facture(s, h, pme, dom_clients.ajouter(s, pme, "Client"), 12)
        s.commit()
    app_banc.c.post("/api/alertes/lues", headers=app_banc.h, json={})
    assert app_banc.c.get("/api/alertes", headers=app_banc.h).json()["non_lues"] == 0
    assert app_banc.c.get("/api/alertes", headers=app_banc.hb).json()["non_lues"] == 1


def test_alertes_masquees_quand_les_notifications_sont_coupees(app_banc):
    h = app_banc.banc.horloge
    h.fixer(datetime(2026, 11, 12, 18, 30))
    resume_du_soir.executer(app_banc.fabrique, app_banc.banc.canal, h, 19)
    assert alertes_de(app_banc, app_banc.h, "echeance") and alertes_de(app_banc, app_banc.h, "resume")
    r = app_banc.c.put("/api/parametres", headers=app_banc.h, json={"preferences": {"resume_du_soir": False, "rappels_fiscaux": False}})
    assert r.status_code == 200
    assert alertes_de(app_banc, app_banc.h, "echeance") == [] and alertes_de(app_banc, app_banc.h, "resume") == []


# ───────────────────────── historique ─────────────────────────


def test_historique_forme_tri_et_sens(app_demo):
    r = app_demo.c.get("/api/historique?limite=100", headers=app_demo.h).json()
    assert set(r) == {"elements", "suivant"} and len(r["elements"]) == 100 and r["suivant"] == r["elements"][-1]["id"]
    assert all(set(e) == CLES_ELEMENT for e in r["elements"])
    dates = [e["date"] for e in r["elements"]]
    assert dates == sorted(dates, reverse=True)
    sens = {"vente": "entree", "paiement": "entree", "depense": "sortie", "facture": "neutre"}
    tout = app_demo.c.get("/api/historique?limite=100&avant=vente-1", headers=app_demo.h).json()["elements"]
    for e in r["elements"] + tout:
        assert e["id"] == f"{e['type']}-{e['id'].split('-')[1]}" and e["sens"] == sens[e["type"]] and e["statut"] in ("ok", "annule", "en_attente", "retard")
        assert isinstance(e["montant"], int)


def test_historique_filtre_par_type_et_contenu_des_types(app_demo):
    c, h = app_demo.c, app_demo.h
    factures = c.get("/api/historique?type=facture", headers=h).json()["elements"]
    assert len(factures) == 3 and {e["statut"] for e in factures} == {"ok", "en_attente", "retard"} and all(e["sens"] == "neutre" for e in factures)
    paiements = c.get("/api/historique?type=paiement", headers=h).json()["elements"]
    assert len(paiements) == 1 and paiements[0]["client"] == "Bureau Essos" and paiements[0]["montant"] == 40000
    depenses = c.get("/api/historique?type=depense&limite=100", headers=h).json()["elements"]
    assert depenses and all(e["type"] == "depense" and e["sens"] == "sortie" for e in depenses)
    credit = [e for e in c.get("/api/historique?type=vente&q=biya", headers=h).json()["elements"]]
    assert len(credit) == 1 and credit[0]["statut"] == "en_attente" and credit[0]["client"] == "Mme Biya"
    assert c.get("/api/historique?type=autre", headers=h).status_code == 422


def test_historique_recherche_insensible_aux_accents_et_a_la_casse(app_demo):
    c, h = app_demo.c, app_demo.h
    for q in ("Lycee", "lycée", "LYCÉE", "lycee technique"):
        elements = c.get("/api/historique", params={"q": q}, headers=h).json()["elements"]
        assert elements and {e["client"] for e in elements} == {"Lycée Technique"}, q
    assert c.get("/api/historique", params={"q": "inexistant"}, headers=h).json() == {"elements": [], "suivant": None}
    assert {e["type"] for e in c.get("/api/historique", params={"q": "electricite"}, headers=h).json()["elements"]} == {"depense"}  # « électricité et eau »


def test_historique_pagination_complete_sans_doublon_ni_trou(app_demo):
    c, h = app_demo.c, app_demo.h
    reference = c.get("/api/historique?limite=100", headers=h).json()["elements"]
    ids, curseur = [], None
    while len(ids) < 100:
        params = {"limite": 7, **({"avant": curseur} if curseur else {})}
        page = c.get("/api/historique", params=params, headers=h).json()
        assert len(page["elements"]) == 7 and page["suivant"] == page["elements"][-1]["id"]
        ids += [e["id"] for e in page["elements"]]
        curseur = page["suivant"]
    assert ids[:100] == [e["id"] for e in reference]
    assert len(set(ids)) == len(ids)


def test_historique_pagination_a_dates_identiques_et_fin_de_liste(app_banc):
    h = app_banc.banc.horloge
    instant = h.maintenant() - timedelta(hours=1)
    with app_banc.fabrique() as s:
        pme = pme_de(s, NUM_A)
        client = dom_clients.ajouter(s, pme, "Mme Fouda")
        for _ in range(3):
            ajouter_vente(s, pme, instant)
        ajouter_depense(s, pme, instant, "loyer", 1000)
        ajouter_depense(s, pme, instant, "gaz", 2000)
        f = ajouter_facture(s, h, pme, client, 0)
        f.creee_a = instant
        s.add(Paiement(pme_id=pme.id, facture_id=f.id, montant=100, source="declare", recu_a=instant, statut="confirme"))
        s.commit()
    complet = app_banc.c.get("/api/historique", headers=app_banc.h).json()
    assert len(complet["elements"]) == 7 and complet["suivant"] is None
    for taille in (1, 2, 3, 5):
        ids, curseur = [], None
        for _ in range(20):
            page = app_banc.c.get("/api/historique", params={"limite": taille, **({"avant": curseur} if curseur else {})}, headers=app_banc.h).json()
            ids += [e["id"] for e in page["elements"]]
            curseur = page["suivant"]
            if curseur is None:
                break
        assert ids == [e["id"] for e in complet["elements"]], taille


def test_historique_limite_bornee_et_curseur_invalide(app_demo):
    c, h = app_demo.c, app_demo.h
    assert len(c.get("/api/historique?limite=5000", headers=h).json()["elements"]) == 100
    assert len(c.get("/api/historique?limite=0", headers=h).json()["elements"]) == 1
    assert len(c.get("/api/historique", headers=h).json()["elements"]) == 30
    for curseur in ("n-importe-quoi", "vente-999999", "vente-1; DROP TABLE ventes", "paiement-0"):
        r = c.get("/api/historique", params={"avant": curseur}, headers=h)
        assert r.status_code == 422 and isinstance(r.json()["detail"], str), curseur


def test_historique_inclut_les_operations_annulees(app_banc):
    h = app_banc.banc.horloge
    with app_banc.fabrique() as s:
        pme = pme_de(s, NUM_A)
        v = ajouter_vente(s, pme, h.maintenant() - timedelta(hours=1))
        v.statut = "annulee"
        d = ajouter_depense(s, pme, h.maintenant() - timedelta(hours=2), "loyer", 5000)
        d.statut = "annulee"
        f = ajouter_facture(s, h, pme, dom_clients.ajouter(s, pme, "Mme Fouda"), 0, statut="annulee")
        s.add(Paiement(pme_id=pme.id, montant=500, source="declare", recu_a=h.maintenant(), statut="annule"))
        s.commit()
    elements = app_banc.c.get("/api/historique", headers=app_banc.h).json()["elements"]
    assert len(elements) == 4 and {e["statut"] for e in elements} == {"annule"}
    assert app_banc.c.get(f"/api/historique/facture/{f.id}", headers=app_banc.h).json()["annulable"] is False


def test_historique_detail_lignes_notes_et_annulable(app_demo):
    c, h = app_demo.c, app_demo.h
    with app_demo.fabrique() as s:
        vente = s.scalars(select(Vente).where(Vente.client_id.is_not(None))).one()
        depense = s.scalars(select(Depense).where(Depense.type == "retrait_perso")).first()
        paiement = s.scalars(select(Paiement)).one()
    d = c.get(f"/api/historique/vente/{vente.id}", headers=h).json()
    assert set(d) == {"element", "lignes", "notes", "annulable"} and set(d["element"]) == CLES_ELEMENT
    assert d["lignes"] == [{"libelle": "Poulet DG", "quantite": 2, "prix_unitaire": 4000, "montant": 8000}]
    assert any("crédit" in n for n in d["notes"]) and any(fcfa(8000) in n for n in d["notes"]) and d["annulable"] is False
    d = c.get("/api/historique/facture/1", headers=h).json()
    assert sum(x["montant"] for x in d["lignes"]) == d["element"]["montant"] == 80000 and {x["libelle"] for x in d["lignes"]} == {"repas", "livraison"}
    d = c.get(f"/api/historique/depense/{depense.id}", headers=h).json()
    assert d["lignes"][0]["montant"] == depense.montant and any("retrait" in n.lower() for n in d["notes"])
    d = c.get(f"/api/historique/paiement/{paiement.id}", headers=h).json()
    assert d["element"]["id"] == f"paiement-{paiement.id}" and d["element"]["client"] == "Bureau Essos" and d["lignes"][0]["montant"] == 40000
    assert c.get("/api/historique/vente/99999999", headers=h).status_code == 404
    assert c.get("/api/historique/inconnu/1", headers=h).status_code == 404


def test_historique_detail_annulable_dans_la_fenetre_de_10_minutes(app_banc):
    banc, c = app_banc.banc, app_banc.c
    c.post("/api/chat", headers=app_banc.h, json={"texte": "j'ai vendu 3 paires à 10000 cash"})
    vente_id = app_banc.c.get("/api/historique?type=vente", headers=app_banc.h).json()["elements"][0]["id"]
    assert app_banc.c.get(f"/api/historique/{vente_id.replace('-', '/')}", headers=app_banc.h).json()["annulable"] is True
    banc.horloge.avancer(minutes=11)
    assert app_banc.c.get(f"/api/historique/{vente_id.replace('-', '/')}", headers=app_banc.h).json()["annulable"] is False


# ───────────────────────── factures ─────────────────────────


def test_factures_liste_forme_filtres_et_coherence(app_demo):
    c, h = app_demo.c, app_demo.h
    r = c.get("/api/factures", headers=h).json()
    assert set(r) == {"factures"} and [f["numero"] for f in r["factures"]] == [3, 2, 1]
    cles = {"id", "numero", "client", "client_id", "total", "statut", "jours_retard", "date", "echeance"}
    assert all(set(f) == cles for f in r["factures"])
    par_numero = {f["numero"]: f for f in r["factures"]}
    assert par_numero[1]["statut"] == "en_retard" and par_numero[2]["statut"] == "envoyee" and par_numero[3]["statut"] == "payee"
    assert (par_numero[1]["client"], par_numero[1]["total"], par_numero[1]["jours_retard"]) == ("Lycée Technique", 80000, 14)
    tableau = {f["numero"]: f for f in c.get("/api/tableau", headers=h).json()["factures"]}
    assert {n: (f["client"], f["total"], f["statut"], f["jours_retard"]) for n, f in par_numero.items()} == {n: (f["client"], f["total"], f["statut"], f["jours_retard"]) for n, f in tableau.items()}
    for statut, attendu in (("envoyee", [2]), ("payee", [3]), ("en_retard", [1]), ("tout", [3, 2, 1])):
        assert [f["numero"] for f in c.get("/api/factures", params={"statut": statut}, headers=h).json()["factures"]] == attendu
    assert c.get("/api/factures?statut=nimporte", headers=h).status_code == 422
    assert len(c.get("/api/factures?limite=1", headers=h).json()["factures"]) == 1


def test_facture_fiche_message_client_lien_et_champs(app_demo):
    c, h = app_demo.c, app_demo.h
    f = c.get("/api/factures/1", headers=h).json()
    assert set(f) == {"id", "numero", "client", "client_id", "telephone", "date", "echeance", "statut", "jours_retard", "total", "lignes", "frais", "relances", "paiements", "message_client", "lien_paiement", "paiement_simule", "pdf_url"}
    assert f["telephone"] == "237677100001" and f["statut"] == "en_retard" and f["total"] == 80000
    assert f["lignes"] == [{"libelle": "repas", "quantite": 30, "prix_unitaire": 2500, "montant": 75000}] and f["frais"] == [{"libelle": "livraison", "montant": 5000}]
    assert f["lien_paiement"] == "https://pay.moki.cm/f/1-1" and f["paiement_simule"] is True
    assert "facture n° 001" in f["message_client"] and "Lycée Technique" in f["message_client"] and f["lien_paiement"] in f["message_client"]
    assert f["relances"] == [] and f["paiements"] == [] and f["pdf_url"] is None
    payee = c.get("/api/factures/3", headers=h).json()
    assert payee["statut"] == "payee" and payee["jours_retard"] == 0 and len(payee["paiements"]) == 1
    assert set(payee["paiements"][0]) == {"date", "montant", "source"} and payee["paiements"][0]["montant"] == 40000
    assert c.get("/api/factures/9999", headers=h).status_code == 404


def test_facture_creee_par_le_chat_a_un_pdf_telechargeable_et_des_relances(app_banc):
    banc, c, h = app_banc.banc, app_banc.c, app_banc.h
    with app_banc.fabrique() as s:
        dom_clients.ajouter(s, pme_de(s, NUM_A), "Mme Fouda", telephone="6 77 55 44 33")
        s.commit()
    chat = lambda t: c.post("/api/chat", headers=h, json={"texte": t}).json()  # noqa: E731
    chat("facture pour Mme Fouda, 4 plats à 3000")
    chat("oui")
    banc.horloge.avancer(days=2)
    chat("relance Mme Fouda")
    chat("oui")
    (liste,) = c.get("/api/factures", headers=h).json()["factures"]
    f = c.get(f"/api/factures/{liste['id']}", headers=h).json()
    assert f["total"] == 12000 and f["pdf_url"].startswith("/api/fichier?nom=facture-001.pdf&token=")
    pdf = c.get(f["pdf_url"])
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert c.get("/api/fichier?nom=facture-001.pdf", headers=app_banc.hb).status_code == 404  # le PDF reste celui de la PME du jeton
    assert len(f["relances"]) == 1 and set(f["relances"][0]) == {"date", "mode", "texte"} and "facture n° 001" in f["relances"][0]["texte"]
    detail = c.get(f"/api/historique/facture/{f['id']}", headers=h).json()
    assert any("Relance" in n for n in detail["notes"])


# ───────────────────────── clients et produits ─────────────────────────


def test_clients_liste_forme_dette_et_coherence_avec_le_tableau(app_demo):
    c, h = app_demo.c, app_demo.h
    clients = c.get("/api/clients", headers=h).json()["clients"]
    assert len(clients) == 5 and all(set(x) == CLES_CLIENT for x in clients)
    assert sum(x["dette"] for x in clients) == c.get("/api/tableau", headers=h).json()["impayes"] == 106000
    par_nom = {x["nom"]: x for x in clients}
    assert par_nom["Lycée Technique"]["dette"] == 80000 and par_nom["Bureau Essos"]["dette"] == 0 and par_nom["Bureau Essos"]["total_achats"] == 40000
    assert par_nom["M. Kamto"]["nb_achats"] == 0 and par_nom["M. Kamto"]["dernier_achat"] is None and par_nom["M. Kamto"]["inactif"] is False
    assert [x["dette"] for x in clients] == sorted((x["dette"] for x in clients), reverse=True)
    impayes = {i["client"]: i["montant"] for i in c.get("/api/tableau", headers=h).json()["impayes_liste"]}
    assert impayes == {n: x["dette"] for n, x in par_nom.items() if x["dette"]}
    assert len(c.get("/api/clients?limite=2", headers=h).json()["clients"]) == 2


def test_client_fiche(app_demo):
    c, h = app_demo.c, app_demo.h
    r = c.get("/api/clients/1", headers=h).json()
    assert set(r) == {"client", "achats", "factures", "paiements", "dette"} and r["dette"] == r["client"]["dette"] == 80000
    assert r["factures"] == [{"id": 1, "numero": 1, "total": 80000, "statut": "en_retard"}]
    assert [a["id"] for a in r["achats"]] == ["facture-1"] and all(set(a) == CLES_ELEMENT for a in r["achats"]) and r["paiements"] == []
    bureau = c.get("/api/clients/4", headers=h).json()
    assert len(bureau["paiements"]) == 1 and bureau["paiements"][0]["id"].startswith("paiement-") and bureau["factures"][0]["statut"] == "payee"
    assert c.get("/api/clients/9999", headers=h).status_code == 404


def test_client_supprime_n_est_plus_visible(app_banc):
    with app_banc.fabrique() as s:
        client = dom_clients.ajouter(s, pme_de(s, NUM_A), "Mme Fouda")
        client.actif = False
        s.commit()
        cid = client.id
    assert app_banc.c.get(f"/api/clients/{cid}", headers=app_banc.h).status_code == 404
    assert app_banc.c.get("/api/clients", headers=app_banc.h).json() == {"clients": []}


def test_produits_ventes_et_ca_sur_30_jours_coherents_avec_le_top(app_demo):
    c, h = app_demo.c, app_demo.h
    produits = c.get("/api/produits", headers=h).json()["produits"]
    assert len(produits) == 8 and all(set(p) == {"id", "nom", "prix", "ventes_30j", "ca_30j"} for p in produits)
    assert [p["ca_30j"] for p in produits] == sorted((p["ca_30j"] for p in produits), reverse=True)
    top = {t["nom"]: t["total"] for t in c.get("/api/tableau", headers=h).json()["top_produits"]}
    par_nom = {p["nom"]: p for p in produits}
    assert top["Poulet DG"] == par_nom["Poulet DG"]["ca_30j"] and top["Poisson braisé"] == par_nom["Poisson braisé"]["ca_30j"]
    assert par_nom["Poulet DG"]["prix"] == 4000 and par_nom["Poulet DG"]["ventes_30j"] > 0
    assert len(c.get("/api/produits?limite=3", headers=h).json()["produits"]) == 3


def test_produits_rapprochement_pluriel_et_accents(app_banc):
    h = app_banc.banc.horloge
    with app_banc.fabrique() as s:
        pme = pme_de(s, NUM_A)
        s.add(Produit(pme_id=pme.id, nom="Poisson braisé", prix=3500, alias=[]))
        ajouter_vente(s, pme, h.maintenant() - timedelta(days=1), produit="poissons braises", total=3500)
        ajouter_vente(s, pme, h.maintenant() - timedelta(days=45), produit="Poisson braisé", total=3500)  # hors fenêtre
        s.commit()
    (p,) = app_banc.c.get("/api/produits", headers=app_banc.h).json()["produits"]
    assert (p["ventes_30j"], p["ca_30j"]) == (1, 3500)


# ───────────────────────── chiffres ─────────────────────────


@pytest.mark.parametrize("periode", ["jour", "semaine", "mois", "annee"])
def test_chiffres_forme_et_series_coherentes(app_demo, periode):
    r = app_demo.c.get("/api/chiffres", params={"periode": periode}, headers=app_demo.h).json()
    assert set(r) == {"periode", "libelle", "ventes", "charges", "benefice", "stock", "retraits_perso", "tresorerie", "par_mode", "nb_ventes", "panier_moyen", "serie", "top_produits", "depenses_par_poste"}
    assert r["periode"] == periode and r["benefice"] == r["ventes"] - r["charges"] and set(r["par_mode"]) == {"cash", "mobile_money", "credit", "facture"}
    assert sum(r["par_mode"].values()) == r["ventes"] and r["panier_moyen"] == r["ventes"] // r["nb_ventes"]
    assert sum(x["ventes"] for x in r["serie"]) == r["ventes"] and sum(x["charges"] for x in r["serie"]) == r["charges"]
    assert all(set(x) == {"libelle", "ventes", "charges"} for x in r["serie"])
    assert all(set(x) == {"nom", "total"} for x in r["top_produits"]) and all(set(x) == {"libelle", "total"} for x in r["depenses_par_poste"])
    assert [x["total"] for x in r["top_produits"]] == sorted((x["total"] for x in r["top_produits"]), reverse=True) and len(r["top_produits"]) <= 5


def test_chiffres_identiques_au_tableau_et_au_chat(app_demo):
    c, h = app_demo.c, app_demo.h
    t = c.get("/api/tableau", headers=h).json()
    for periode, cle in (("jour", "jour"), ("semaine", "semaine"), ("mois", "mois")):
        r = c.get("/api/chiffres", params={"periode": periode}, headers=h).json()
        assert (r["ventes"], r["nb_ventes"], r["charges"], r["benefice"]) == (t[cle]["ventes"], t[cle]["nb"], t[cle]["charges"], t[cle]["benefice"]), periode
    mois = c.get("/api/chiffres?periode=mois", headers=h).json()
    assert mois["tresorerie"] == t["tresorerie"] and mois["retraits_perso"] == t["retraits_perso_mois"]
    reponse = c.post("/api/chat", headers=h, json={"texte": "j'ai fait combien ce mois ?"}).json()["reponses"][0]
    assert fcfa(mois["ventes"]) in reponse and fcfa(mois["benefice"]) in reponse
    assert c.get("/api/chiffres", headers=h).json()["periode"] == "mois"  # période par défaut


def test_chiffres_le_chat_modifie_les_chiffres_de_l_ecran(app_demo):
    c, h = app_demo.c, app_demo.h
    avant = c.get("/api/chiffres?periode=jour", headers=h).json()
    c.post("/api/chat", headers=h, json={"texte": "j'ai payé 20 000 de loyer"})
    apres = c.get("/api/chiffres?periode=jour", headers=h).json()
    assert apres["charges"] == avant["charges"] + 20000 and apres["tresorerie"] == avant["tresorerie"] - 20000
    assert any(x["libelle"] == "Loyer" and x["total"] == 20000 for x in apres["depenses_par_poste"])


def test_chiffres_periode_invalide_et_pme_vide(app_banc):
    assert app_banc.c.get("/api/chiffres?periode=siecle", headers=app_banc.h).status_code == 422
    r = app_banc.c.get("/api/chiffres?periode=annee", headers=app_banc.h).json()
    assert r["ventes"] == 0 and r["nb_ventes"] == 0 and r["panier_moyen"] == 0 and r["top_produits"] == [] and r["depenses_par_poste"] == []


def test_chiffres_perso_stock_et_charges_separes(app_banc):
    def chat(texte: str) -> None:
        app_banc.c.post("/api/chat", headers=app_banc.h, json={"texte": texte})

    chat("j'ai vendu 3 paires à 10000 cash")
    chat("j'ai payé 20 000 de loyer")
    chat("c'est perso")
    chat("j'ai acheté du stock 4000")
    r = app_banc.c.get("/api/chiffres?periode=jour", headers=app_banc.h).json()
    assert (r["ventes"], r["charges"], r["benefice"], r["stock"], r["retraits_perso"], r["tresorerie"]) == (30000, 0, 30000, 4000, 20000, 6000)


# ───────────────────────── documents, connexions ─────────────────────────


def test_documents_dossier_impot_et_echeances(app_demo, app_banc):
    d = app_demo.c.get("/api/documents", headers=app_demo.h).json()
    assert set(d) == {"dossier", "impot", "echeances"}
    assert d["dossier"] == {"historique_mois": 6, "requis": 6, "manque_mois": 0, "pret": True, "fictives": True}
    t = app_demo.c.get("/api/tableau", headers=app_demo.h).json()
    assert set(d["impot"]) == {"estimation", "ca_annuel", "taux", "note"} and d["impot"]["estimation"] == t["impot"]["estimation"] and "DGI" in d["impot"]["note"]
    assert d["echeances"][0] == {"libelle": "Déclaration mensuelle", "date": "2026-11-15", "jours": 3} and d["echeances"][0] == t["echeance"]
    vide = app_banc.c.get("/api/documents", headers=app_banc.h).json()
    assert vide["dossier"] == {"historique_mois": 0, "requis": 6, "manque_mois": 6, "pret": False, "fictives": False} and vide["impot"]["estimation"] == 0


def test_connexions_forme_et_statuts(app_banc):
    r = app_banc.c.get("/api/connexions", headers=app_banc.h).json()
    assert [x["id"] for x in r["connexions"]] == ["whatsapp", "orange_money", "mtn_momo", "banque", "dgi"]
    assert all(set(x) == {"id", "nom", "statut", "detail"} and x["nom"] and x["detail"] for x in r["connexions"])
    assert {x["id"]: x["statut"] for x in r["connexions"]} == {"whatsapp": "simule", "orange_money": "bientot", "mtn_momo": "bientot", "banque": "bientot", "dgi": "bientot"}


# ───────────────────────── paramètres ─────────────────────────


def test_parametres_lecture_et_ecriture(app_demo):
    c, h = app_demo.c, app_demo.h
    r = c.get("/api/parametres", headers=h).json()
    assert r == {
        "commerce": {"nom_commerce": "Chez Marie", "nom_gerante": "Marie Nkoulou", "ville": "Yaoundé", "quartier": "Essos", "secteur": "Restaurant / snack", "numero": NUM_A},
        "preferences": {"mode_relance": "direct", "seuil_confirmation_renforcee": 50000, "resume_du_soir": True, "rappels_fiscaux": True},
        "demo": True,
    }
    corps = {"commerce": {"nom_commerce": " Chez Marie 2 ", "nom_gerante": "", "quartier": "Bastos"}, "preferences": {"mode_relance": "transfert", "seuil_confirmation_renforcee": 100000, "resume_du_soir": False}}
    ecrit = c.put("/api/parametres", headers=h, json=corps)
    assert ecrit.status_code == 200 and ecrit.json() == c.get("/api/parametres", headers=h).json()
    nouveau = ecrit.json()
    assert nouveau["commerce"]["nom_commerce"] == "Chez Marie 2" and nouveau["commerce"]["nom_gerante"] is None and nouveau["commerce"]["quartier"] == "Bastos"
    assert nouveau["commerce"]["ville"] == "Yaoundé" and nouveau["commerce"]["numero"] == NUM_A  # champs non envoyés inchangés
    assert nouveau["preferences"] == {"mode_relance": "transfert", "seuil_confirmation_renforcee": 100000, "resume_du_soir": False, "rappels_fiscaux": True}
    with app_demo.fabrique() as s:
        pme = pme_de(s, NUM_A)
        assert pme.mode_relance == "transfert" and pme.seuil_confirmation_renforcee == 100000
    assert c.put("/api/parametres", headers=h, json={}).json() == nouveau  # corps vide : rien ne change
    c.put("/api/parametres", headers=h, json={"preferences": {"resume_du_soir": True}})
    assert c.get("/api/parametres", headers=h).json()["preferences"]["resume_du_soir"] is True


@pytest.mark.parametrize("corps", [
    {"preferences": {"mode_relance": "autre"}}, {"preferences": {"mode_relance": None}},
    {"preferences": {"seuil_confirmation_renforcee": 999}}, {"preferences": {"seuil_confirmation_renforcee": 10_000_001}}, {"preferences": {"seuil_confirmation_renforcee": True}},
    {"preferences": {"seuil_confirmation_renforcee": "5000"}}, {"preferences": {"seuil_confirmation_renforcee": 5000.5}}, {"preferences": {"seuil_confirmation_renforcee": -1}},
    {"preferences": {"resume_du_soir": "oui"}}, {"preferences": {"rappels_fiscaux": 1}}, {"preferences": {"inconnue": True}},
    {"commerce": {"nom_commerce": ""}}, {"commerce": {"nom_commerce": "   "}}, {"commerce": {"nom_commerce": "x" * 121}}, {"commerce": {"nom_gerante": "x" * 121}},
    {"commerce": {"ville": "x" * 61}}, {"commerce": {"quartier": "x" * 61}}, {"commerce": {"secteur": "x" * 41}}, {"commerce": {"nom_commerce": 12}}, {"commerce": {"ville": None}},
    {"commerce": {"numero": "237600000000"}}, {"commerce": {"pme_id": 2}}, {"commerce": {"statut": "suspendu"}}, {"commerce": {"donnees_fictives": False}},
    {"numero": "237600000000"}, {"pme_id": 2}, {"statut": "suspendu"}, {"statut_abonnement": "payant"},
    {"commerce": "texte"}, {"preferences": []}, {"commerce": None},
])
def test_parametres_validation_stricte_422_et_rien_n_est_modifie(app_banc, corps):
    avant = app_banc.c.get("/api/parametres", headers=app_banc.h).json()
    r = app_banc.c.put("/api/parametres", headers=app_banc.h, json=corps)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and r.json()["detail"], corps
    assert app_banc.c.get("/api/parametres", headers=app_banc.h).json() == avant
    with app_banc.fabrique() as s:
        assert s.scalar(select(func.count(Pme.id))) == 2 and pme_de(s, NUM_A).statut == "actif"


def test_parametres_modification_partielle_invalide_est_atomique(app_banc):
    avant = app_banc.c.get("/api/parametres", headers=app_banc.h).json()
    r = app_banc.c.put("/api/parametres", headers=app_banc.h, json={"commerce": {"nom_commerce": "Nouveau nom"}, "preferences": {"mode_relance": "nimporte"}})
    assert r.status_code == 422 and app_banc.c.get("/api/parametres", headers=app_banc.h).json() == avant


@pytest.mark.parametrize("seuil", [1000, 10_000_000])
def test_parametres_seuil_aux_bornes(app_banc, seuil):
    r = app_banc.c.put("/api/parametres", headers=app_banc.h, json={"preferences": {"seuil_confirmation_renforcee": seuil}})
    assert r.status_code == 200 and r.json()["preferences"]["seuil_confirmation_renforcee"] == seuil


def test_parametres_textes_de_120_caracteres_acceptes(app_banc):
    r = app_banc.c.put("/api/parametres", headers=app_banc.h, json={"commerce": {"nom_commerce": "x" * 120, "nom_gerante": "y" * 120}})
    assert r.status_code == 200 and len(r.json()["commerce"]["nom_commerce"]) == 120


def test_parametres_preferences_isolees_par_pme_et_respectees_par_les_taches(app_banc):
    h = app_banc.banc.horloge
    app_banc.c.put("/api/parametres", headers=app_banc.h, json={"preferences": {"resume_du_soir": False, "rappels_fiscaux": False}})
    assert app_banc.c.get("/api/parametres", headers=app_banc.hb).json()["preferences"]["resume_du_soir"] is True
    h.fixer(datetime(2026, 11, 12, 18, 30))  # 19 h 30 locale, 3 jours avant l'échéance
    assert resume_du_soir.executer(app_banc.fabrique, app_banc.banc.canal, h, 19) == 1  # seule la PME B reçoit son résumé
    from app.workers import rappels_fiscaux

    assert rappels_fiscaux.executer(app_banc.fabrique, app_banc.banc.canal, h) == 1  # PME B seulement : la déclaration mensuelle est à 3 jours, A a coupé les rappels
    with app_banc.fabrique() as s:
        assert {m.numero for m in s.scalars(select(Message).where(Message.type == "notification"))} == {NUM_B}
        assert s.scalar(select(func.count(Preference.id)).where(Preference.pme_id == pme_de(s, NUM_A).id)) == 2


# ───────────────────────── recherche ─────────────────────────


def test_recherche_accents_casse_et_formes(app_demo):
    c, h = app_demo.c, app_demo.h
    for q in ("Lycee", "lycée tech", "LYCEE"):
        r = c.get("/api/recherche", params={"q": q}, headers=h).json()
        assert set(r) == {"clients", "produits", "factures"}
        assert [x["nom"] for x in r["clients"]] == ["Lycée Technique"] and set(r["clients"][0]) == {"id", "nom", "detail"}
        assert [f["numero"] for f in r["factures"]] == [1] and set(r["factures"][0]) == {"id", "numero", "client", "total", "statut"}
    r = c.get("/api/recherche", params={"q": "poisson braise"}, headers=h).json()
    assert [p["nom"] for p in r["produits"]] == ["Poisson braisé"] and set(r["produits"][0]) == {"id", "nom", "detail"} and r["clients"] == []
    assert [f["numero"] for f in c.get("/api/recherche?q=003", headers=h).json()["factures"]] == [3]
    assert c.get("/api/recherche?q=essos", headers=h).json()["clients"] != []  # le quartier compte aussi


def test_recherche_moins_de_2_caracteres_ou_vide(app_demo):
    for q in ("", "a", " a ", "é", "!!"):
        assert app_demo.c.get("/api/recherche", params={"q": q}, headers=app_demo.h).json() == {"clients": [], "produits": [], "factures": []}, q
    assert app_demo.c.get("/api/recherche", headers=app_demo.h).json() == {"clients": [], "produits": [], "factures": []}


def test_recherche_huit_resultats_maximum_par_categorie(app_banc):
    h = app_banc.banc.horloge
    with app_banc.fabrique() as s:
        pme = pme_de(s, NUM_A)
        for i in range(12):
            client = dom_clients.ajouter(s, pme, f"Client {i:02d}")
            s.add(Produit(pme_id=pme.id, nom=f"Client sac {i:02d}", prix=1000, alias=[]))
            ajouter_facture(s, h, pme, client, 0)
        s.commit()
    r = app_banc.c.get("/api/recherche?q=client", headers=app_banc.h).json()
    assert len(r["clients"]) == len(r["produits"]) == len(r["factures"]) == 8
    assert [x["nom"] for x in r["clients"]] == [f"Client {i:02d}" for i in range(8)]


# ───────────────────────── étanchéité entre PME ─────────────────────────


@pytest.fixture
def deux_pme(app_demo):
    """Démo (A = Chez Marie, NUM_A) + une autre PME (B) avec ses propres données, dans la même base."""
    h = app_demo.banc.horloge
    with app_demo.fabrique() as s:
        pme = dom_pme.creer_pme(s, h, nom_commerce="Atelier Paul", numero_whatsapp=NUM_B, nom_gerante="Paul Atangana", ville="Douala", quartier="Akwa", secteur="Couture")
        client = dom_clients.ajouter(s, pme, "Zacharie Nkodo", telephone="6 70 11 22 33", quartier="Akwa")
        s.add(Produit(pme_id=pme.id, nom="Robe wax", prix=15000, alias=[]))
        vente = ajouter_vente(s, pme, h.maintenant() - timedelta(hours=1), produit="Robe wax", total=15000, client=client)
        depense = ajouter_depense(s, pme, h.maintenant() - timedelta(hours=2), "tissu", 5000)
        facture = ajouter_facture(s, h, pme, client, 12, quantite=3, prix=10000)
        s.add(Paiement(pme_id=pme.id, vente_id=vente.id, montant=1000, source="declare", recu_a=h.maintenant(), statut="confirme"))
        s.commit()
        paiement = s.scalars(select(Paiement).where(Paiement.pme_id == pme.id)).one()
        b = SimpleNamespace(pme=pme.id, client=client.id, vente=vente.id, depense=depense.id, facture=facture.id, paiement=paiement.id)
        a_ids = SimpleNamespace(
            vente=s.scalars(select(Vente.id).where(Vente.pme_id != pme.id).order_by(Vente.id)).first(),
            client=s.scalars(select(Client.id).where(Client.pme_id != pme.id).order_by(Client.id)).first(),
            depense=s.scalars(select(Depense.id).where(Depense.pme_id != pme.id)).first(),
            facture=s.scalars(select(Facture.id).where(Facture.pme_id != pme.id)).first(),
            paiement=s.scalars(select(Paiement.id).where(Paiement.pme_id != pme.id)).first(),
        )
    app_demo.hb, app_demo.b, app_demo.a = app_demo.jeton(NUM_B), b, a_ids
    return app_demo


def test_etancheite_un_id_d_une_autre_pme_donne_404_dans_les_deux_sens(deux_pme):
    c, a, b = deux_pme.c, deux_pme.a, deux_pme.b
    chez_b = [f"/api/factures/{a.facture}", f"/api/clients/{a.client}", f"/api/historique/vente/{a.vente}", f"/api/historique/depense/{a.depense}",
              f"/api/historique/facture/{a.facture}", f"/api/historique/paiement/{a.paiement}"]
    chez_a = [f"/api/factures/{b.facture}", f"/api/clients/{b.client}", f"/api/historique/vente/{b.vente}", f"/api/historique/depense/{b.depense}",
              f"/api/historique/facture/{b.facture}", f"/api/historique/paiement/{b.paiement}"]
    for url in chez_b:
        assert c.get(url, headers=deux_pme.hb).status_code == 404, url
        assert c.get(url, headers=deux_pme.h).status_code == 200, url  # le propriétaire, lui, y accède
    for url in chez_a:
        assert c.get(url, headers=deux_pme.h).status_code == 404, url
        assert c.get(url, headers=deux_pme.hb).status_code == 200, url


def test_etancheite_les_listes_ne_montrent_que_les_donnees_de_la_pme(deux_pme):
    c, hb = deux_pme.c, deux_pme.hb
    reponses = {url: c.get(url, headers=hb) for url in ["/api/accueil", "/api/alertes", "/api/historique?limite=100", "/api/factures", "/api/clients", "/api/produits", "/api/chiffres?periode=annee", "/api/documents", "/api/parametres", "/api/connexions", "/api/recherche?q=lycee", "/api/recherche?q=poulet"]}
    for url, r in reponses.items():
        assert r.status_code == 200, url
        texte = json.dumps(r.json(), ensure_ascii=False)
        for marque in ("Lycée", "Biya", "Fouda", "Poulet", "Chez Marie", "Kamto", "Marie", NUM_A):
            assert marque not in texte, (url, marque)
    assert [f["numero"] for f in reponses["/api/factures"].json()["factures"]] == [1]  # la numérotation repart à 1 pour chaque PME
    assert [x["nom"] for x in reponses["/api/clients"].json()["clients"]] == ["Zacharie Nkodo"]
    assert [x["nom"] for x in reponses["/api/produits"].json()["produits"]] == ["Robe wax"]
    elements = reponses["/api/historique?limite=100"].json()["elements"]
    assert {e["id"] for e in elements} == {f"vente-{deux_pme.b.vente}", f"depense-{deux_pme.b.depense}", f"facture-{deux_pme.b.facture}", f"paiement-{deux_pme.b.paiement}"}
    assert reponses["/api/recherche?q=lycee"].json() == {"clients": [], "produits": [], "factures": []}
    assert [x["id"] for x in reponses["/api/alertes"].json()["alertes"] if x["type"] == "retard"] == [f"retard-facture-{deux_pme.b.facture}"]


def test_etancheite_chiffres_de_b_independants_de_a(deux_pme):
    c = deux_pme.c
    jour = c.get("/api/chiffres?periode=jour", headers=deux_pme.hb).json()
    assert (jour["ventes"], jour["nb_ventes"], jour["charges"], jour["tresorerie"]) == (15000, 1, 5000, 15000 + 1000 - 5000)
    a = c.get("/api/accueil", headers=deux_pme.hb).json()
    assert a["kpis"]["impayes"] == 30000 and a["kpis"]["ventes_jour"] == 15000 and a["commerce"] == "Atelier Paul" and a["demo"] is False and a["gerante"] == "Paul"
    assert c.get("/api/clients", headers=deux_pme.hb).json()["clients"][0]["dette"] == 30000


def test_etancheite_curseur_d_une_autre_pme_refuse_et_parametres_isoles(deux_pme):
    c = deux_pme.c
    r = c.get("/api/historique", params={"avant": f"vente-{deux_pme.a.vente}"}, headers=deux_pme.hb)
    assert r.status_code == 422  # un curseur ne permet pas de deviner les données d'une autre PME
    c.put("/api/parametres", headers=deux_pme.hb, json={"commerce": {"nom_commerce": "Atelier Paul 2"}})
    assert c.get("/api/parametres", headers=deux_pme.h).json()["commerce"]["nom_commerce"] == "Chez Marie"
    assert c.get("/api/parametres", headers=deux_pme.hb).json()["commerce"]["numero"] == NUM_B


def test_aucune_route_n_accepte_un_pme_id_du_client(deux_pme):
    c = deux_pme.c
    pme_a = 1
    assert c.get(f"/api/factures?pme_id={pme_a}", headers=deux_pme.hb).json()["factures"][0]["client"] == "Zacharie Nkodo"
    assert c.get(f"/api/clients?pme_id={pme_a}", headers=deux_pme.hb).json()["clients"][0]["nom"] == "Zacharie Nkodo"
    assert c.get(f"/api/historique?pme_id={pme_a}&type=facture", headers=deux_pme.hb).json()["elements"][0]["client"] == "Zacharie Nkodo"
    assert c.put("/api/parametres", headers=deux_pme.hb, json={"pme_id": pme_a}).status_code == 422
    assert c.get("/api/accueil", headers={**deux_pme.hb, "X-Pme-Id": str(pme_a)}).json()["commerce"] == "Atelier Paul"


# ───────────────────────── performances ─────────────────────────


def test_pas_de_requete_par_ligne_sur_les_listes(app_demo):
    c, h = app_demo.c, app_demo.h
    with compter_requetes(app_demo.moteur) as nb:
        assert c.get("/api/historique?limite=100", headers=h).status_code == 200
    assert len(nb) <= 12, len(nb)
    for url, maximum in (("/api/factures?limite=100", 5), ("/api/clients?limite=100", 12), ("/api/produits?limite=100", 8), ("/api/recherche?q=essos", 15), ("/api/historique?type=paiement", 8), ("/api/clients/1", 25)):
        with compter_requetes(app_demo.moteur) as nb:
            assert c.get(url, headers=h).status_code == 200
        assert len(nb) <= maximum, (url, len(nb))
