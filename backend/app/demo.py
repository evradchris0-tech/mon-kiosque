"""Données de démonstration FICTIVES : « Chez Marie », snack à Essos, 6 mois d'historique."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import Client, Depense, Facture, Pme, Produit, Vente
from app.domaine import clients as dom_clients
from app.domaine import factures as dom_factures
from app.domaine import pme as dom_pme

NUMERO_DEMO = "237677000001"

PRODUITS = [("Poulet DG", 4000), ("Poisson braisé", 3500), ("Riz sauté", 1500), ("Beignets haricots", 500), ("Boisson", 500), ("Jus naturel", 1000), ("Brochettes", 1000), ("Plantain frit", 800)]
CLIENTS = [("Lycée Technique", "237677100001", "Soa"), ("Mme Biya", "237677100002", "Essos"), ("Mme Fouda", "237677100003", "Mvog-Ada"), ("Bureau Essos", "237677100004", "Essos"), ("M. Kamto", "237677100005", "Bastos")]


def deja_peuple(session: Session) -> bool:
    return (session.scalar(select(func.count(Pme.id))) or 0) > 0


def peupler(session: Session, horloge: Horloge) -> Pme:
    rng = random.Random(42)
    maintenant = horloge.maintenant()
    pme = dom_pme.creer_pme(session, horloge, nom_commerce="Chez Marie", nom_gerante="Marie Nkoulou", numero_whatsapp=NUMERO_DEMO, secteur="Restaurant / snack", ville="Yaoundé", quartier="Essos")
    pme.donnees_fictives = True
    pme.mode_relance = "direct"
    pme.date_inscription = maintenant - timedelta(days=190)
    for nom, prix in PRODUITS:
        session.add(Produit(pme_id=pme.id, nom=nom, prix=prix, alias=[]))
    clients = [dom_clients.ajouter(session, pme, nom, tel, quartier) for nom, tel, quartier in CLIENTS]
    session.flush()

    for jours_avant in range(190, -1, -1):
        jour = (maintenant - timedelta(days=jours_avant)).replace(hour=0, minute=0, second=0, microsecond=0)
        if jour.weekday() == 6 and rng.random() < 0.6:
            continue  # souvent fermé le dimanche
        croissance = 0.75 + 0.25 * (190 - jours_avant) / 190  # activité qui progresse
        for _ in range(max(2, round(rng.randint(14, 24) * croissance))):
            heure = jour + timedelta(hours=rng.randint(6, 16), minutes=rng.randint(0, 59))
            if heure > maintenant:
                continue
            nom, prix = rng.choice(PRODUITS)
            q = rng.randint(1, 4)
            mode = rng.choices(["cash", "mobile_money"], weights=[60, 40])[0]
            total = q * prix
            session.add(Vente(pme_id=pme.id, heure_envoi=heure, heure_reception=heure, lignes=[{"produit": nom, "quantite": q, "prix_unitaire": prix}], total=total, parts_paiement=[{"mode": mode, "montant": total}], statut="active"))
        if jour.day == 5 and jours_avant > 0:
            for libelle, montant, type_ in [("loyer", 100_000, "charge"), ("électricité et eau", 35_000, "charge"), ("salaires", 180_000, "charge"), ("achat de stock", 700_000, "stock"), ("retrait personnel", 80_000, "retrait_perso")]:
                nature = "perso" if type_ == "retrait_perso" else "pro"
                heure = jour + timedelta(hours=9)
                session.add(Depense(pme_id=pme.id, libelle=libelle, montant=montant + rng.randint(-5, 5) * 1000, type=type_, nature=nature, heure_envoi=heure, heure_reception=heure, statut="active"))
        if jour.weekday() == 2:
            heure = jour + timedelta(hours=10)
            session.add(Depense(pme_id=pme.id, libelle="transport et gaz", montant=rng.randint(8, 15) * 1000, type="charge", nature="pro", heure_envoi=heure, heure_reception=heure, statut="active"))
    session.flush()

    # Une facture ancienne impayée (en retard), une récente, une payée, et une vente à crédit
    lycee, biya, fouda = clients[0], clients[1], clients[2]
    anciens = [(lycee, [{"produit": "repas", "quantite": 30, "prix_unitaire": 2500}], [{"libelle": "livraison", "montant": 5000}], 14, "envoyee"),
               (fouda, [{"produit": "plateaux repas", "quantite": 6, "prix_unitaire": 3000}], [], 3, "envoyee"),
               (clients[3], [{"produit": "buffet", "quantite": 20, "prix_unitaire": 2000}], [], 25, "payee")]
    from app.db.modeles import Confirmation

    for client, lignes, frais, il_y_a, statut in anciens:
        conf = Confirmation(pme_id=pme.id, action={"demo": True}, mode="simple", demandee_a=maintenant, confirmee_a=maintenant, statut="confirmee")
        session.add(conf)
        session.flush()
        f = dom_factures.creer(session, pme, horloge, client=client, lignes=lignes, frais=frais, confirmation_id=conf.id)
        f.creee_a = maintenant - timedelta(days=il_y_a)
        f.statut = statut
        if statut == "payee":
            f.payee_a = maintenant - timedelta(days=il_y_a - 2)
            from app.db.modeles import Paiement

            session.add(Paiement(pme_id=pme.id, facture_id=f.id, montant=f.total, source="declare", recu_a=f.payee_a, statut="confirme"))
    session.add(Vente(pme_id=pme.id, heure_envoi=maintenant - timedelta(days=4), heure_reception=maintenant - timedelta(days=4), lignes=[{"produit": "Poulet DG", "quantite": 2, "prix_unitaire": 4000}], total=8000, parts_paiement=[{"mode": "credit", "montant": 8000}], client_id=biya.id, client_nom_cite="Mme Biya", credit_restant=8000, statut="active"))
    session.flush()
    from app.db.modeles import Action

    session.query(Action).filter(Action.pme_id == pme.id).delete()  # pas d'annulation possible sur l'historique de démo
    session.commit()
    return pme


def nb_clients(session: Session, pme: Pme) -> int:
    return session.scalar(select(func.count(Client.id)).where(Client.pme_id == pme.id)) or 0


def verif_dernier(session: Session, pme: Pme) -> datetime | None:
    return session.scalar(select(func.max(Facture.creee_a)).where(Facture.pme_id == pme.id))
