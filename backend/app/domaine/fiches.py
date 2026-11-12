"""Vues de suivi : factures, clients, produits et recherche globale (lecture seule, toujours filtrées par PME)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.argent import format_fcfa
from app.core.horloge import Horloge
from app.db.modeles import Client, Facture, Paiement, Pme, Relance, Vente
from app.domaine import factures as dom_factures
from app.domaine import finances, historique
from app.domaine import produits as dom_produits
from app.domaine.texte import normaliser
from app.moki import reponses

STATUTS_FACTURE = ("tout", "envoyee", "payee", "en_retard")
JOURS_INACTIF = 30
MAX_RECHERCHE = 8
FENETRE_PRODUITS_JOURS = 30


def lien_paiement(pme: Pme, facture: Facture) -> str:
    return f"https://pay.moki.cm/f/{pme.id}-{facture.numero}"


def _date(valeur) -> str | None:
    return valeur.isoformat() if valeur else None


def _jours_retard(facture: Facture, horloge: Horloge) -> int:
    return dom_factures.jours_de_retard(facture, horloge) if facture.statut in dom_factures.STATUTS_OUVERTS else 0


def _element_liste(facture: Facture, client: str, horloge: Horloge) -> dict:
    return {
        "id": facture.id,
        "numero": facture.numero,
        "client": client,
        "client_id": facture.client_id,
        "total": facture.total,
        "statut": dom_factures.statut_affiche(facture, horloge),
        "jours_retard": _jours_retard(facture, horloge),
        "date": historique.iso(facture.creee_a),
        "echeance": _date(facture.echeance),
    }


def liste_factures(session: Session, pme: Pme, horloge: Horloge, statut: str = "tout", limite: int = 30) -> list[dict]:
    """Factures non annulées, la plus récente d'abord. Statut calculé comme dans le tableau (retard = plus de 7 jours)."""
    requete = select(Facture, Client.nom).join(Client, Client.id == Facture.client_id).where(Facture.pme_id == pme.id, Client.pme_id == pme.id)
    if statut == "payee":
        requete = requete.where(Facture.statut == "payee")
    elif statut in ("envoyee", "en_retard"):
        requete = requete.where(Facture.statut.in_(dom_factures.STATUTS_OUVERTS))
    else:
        requete = requete.where(Facture.statut != "annulee")
    resultat: list[dict] = []
    for facture, client in session.execute(requete.order_by(Facture.numero.desc()).execution_options(yield_per=200)):
        element = _element_liste(facture, client, horloge)
        if statut in ("envoyee", "en_retard") and element["statut"] != statut:
            continue
        resultat.append(element)
        if len(resultat) >= limite:
            break
    return resultat


def vue_facture(session: Session, pme: Pme, horloge: Horloge, facture_id: int, dossier_pdf: Path) -> dict | None:
    """Fiche facture ; None si elle n'existe pas dans cette PME (ou si elle est annulée). `pdf_nom` : fichier existant ou None."""
    facture = session.scalar(select(Facture).where(Facture.id == facture_id, Facture.pme_id == pme.id, Facture.statut != "annulee"))
    if facture is None:
        return None
    client = session.scalar(select(Client).where(Client.id == facture.client_id, Client.pme_id == pme.id))
    nom_client = client.nom if client else "?"
    lien = lien_paiement(pme, facture)
    relances = session.scalars(select(Relance).where(Relance.pme_id == pme.id, Relance.facture_id == facture.id).order_by(Relance.envoyee_a))
    paiements = session.scalars(select(Paiement).where(Paiement.pme_id == pme.id, Paiement.facture_id == facture.id, Paiement.statut == "confirme").order_by(Paiement.recu_a))
    pdf_nom = Path(facture.pdf_chemin).name if facture.pdf_chemin else None
    if pdf_nom and not (dossier_pdf / str(pme.id) / pdf_nom).is_file():
        pdf_nom = None
    return {
        "id": facture.id,
        "numero": facture.numero,
        "client": nom_client,
        "client_id": facture.client_id,
        "telephone": client.telephone if client else None,
        "date": historique.iso(facture.creee_a),
        "echeance": _date(facture.echeance),
        "statut": dom_factures.statut_affiche(facture, horloge),
        "jours_retard": _jours_retard(facture, horloge),
        "total": facture.total,
        "lignes": [{"libelle": str(x.get("produit") or "Prestation"), "quantite": int(x["quantite"]), "prix_unitaire": int(x["prix_unitaire"]), "montant": int(x["quantite"]) * int(x["prix_unitaire"])} for x in facture.lignes],
        "frais": [{"libelle": str(f["libelle"]), "montant": int(f["montant"])} for f in facture.frais],
        "relances": [{"date": historique.iso(r.envoyee_a), "mode": r.mode, "texte": r.texte} for r in relances],
        "paiements": [{"date": historique.iso(p.recu_a), "montant": p.montant, "source": p.source} for p in paiements],
        "message_client": reponses.facture_pour_client(pme.nom_commerce, nom_client, facture.numero, facture.total, lien),
        "lien_paiement": lien,
        "paiement_simule": True,
        "pdf_nom": pdf_nom,
    }


def fiches_clients(session: Session, pme: Pme, horloge: Horloge, ids: list[int] | None = None) -> list[tuple[dict, datetime | None]]:
    """(fiche, dernier achat) des clients actifs, en 5 requêtes quel que soit leur nombre.

    achats = ventes actives + factures non annulées ; dette = factures ouvertes + ventes à crédit non soldées
    (même définition que `paiements.reste_du_client`)."""
    requete = select(Client).where(Client.pme_id == pme.id, Client.actif.is_(True))
    if ids is not None:
        requete = requete.where(Client.id.in_(ids))
    clients = list(session.scalars(requete))
    ventes = {c: (n, t, d) for c, n, t, d in session.execute(
        select(Vente.client_id, func.count(Vente.id), func.sum(Vente.total), func.max(Vente.heure_envoi))
        .where(Vente.pme_id == pme.id, Vente.statut == "active", Vente.client_id.is_not(None)).group_by(Vente.client_id))}
    factures = {c: (n, t, d) for c, n, t, d in session.execute(
        select(Facture.client_id, func.count(Facture.id), func.sum(Facture.total), func.max(Facture.creee_a))
        .where(Facture.pme_id == pme.id, Facture.statut != "annulee").group_by(Facture.client_id))}
    dette_f = dict(session.execute(select(Facture.client_id, func.sum(Facture.total)).where(Facture.pme_id == pme.id, Facture.statut.in_(dom_factures.STATUTS_OUVERTS)).group_by(Facture.client_id)).all())
    dette_v = dict(session.execute(select(Vente.client_id, func.sum(Vente.credit_restant)).where(Vente.pme_id == pme.id, Vente.statut == "active", Vente.credit_restant > 0, Vente.client_id.is_not(None)).group_by(Vente.client_id)).all())
    maintenant = horloge.maintenant()
    sortie: list[tuple[dict, datetime | None]] = []
    for c in clients:
        nv, tv, dv = ventes.get(c.id, (0, 0, None))
        nf, tf, df = factures.get(c.id, (0, 0, None))
        dernier = max((d for d in (c.dernier_achat, dv, df) if d is not None), default=None)
        fiche = {
            "id": c.id,
            "nom": c.nom,
            "telephone": c.telephone,
            "quartier": c.quartier,
            "dette": int(dette_f.get(c.id, 0) or 0) + int(dette_v.get(c.id, 0) or 0),
            "nb_achats": nv + nf,
            "total_achats": int(tv or 0) + int(tf or 0),
            "dernier_achat": historique.iso(dernier) if dernier else None,
            "inactif": dernier is not None and (maintenant - dernier).days > JOURS_INACTIF,
        }
        sortie.append((fiche, dernier))
    return sortie


def liste_clients(session: Session, pme: Pme, horloge: Horloge, limite: int = 30) -> list[dict]:
    fiches = [f for f, _ in fiches_clients(session, pme, horloge)]
    fiches.sort(key=lambda f: (-f["dette"], normaliser(f["nom"])))
    return fiches[:limite]


def vue_client(session: Session, pme: Pme, horloge: Horloge, client_id: int) -> dict | None:
    trouvees = fiches_clients(session, pme, horloge, [client_id])
    if not trouvees:
        return None
    fiche = trouvees[0][0]
    achats, _ = historique.page(session, pme, horloge, types=("vente", "facture"), client_id=client_id, actifs=True, limite=30)
    paiements, _ = historique.page(session, pme, horloge, types=("paiement",), client_id=client_id, actifs=True, limite=30)
    factures = session.scalars(select(Facture).where(Facture.pme_id == pme.id, Facture.client_id == client_id, Facture.statut != "annulee").order_by(Facture.numero.desc()).limit(30))
    return {
        "client": fiche,
        "achats": achats,
        "factures": [{"id": f.id, "numero": f.numero, "total": f.total, "statut": dom_factures.statut_affiche(f, horloge)} for f in factures],
        "paiements": paiements,
        "dette": fiche["dette"],
    }


def liste_produits(session: Session, pme: Pme, horloge: Horloge, limite: int = 30) -> list[dict]:
    """Catalogue avec quantités vendues et chiffre d'affaires des 30 derniers jours (même fenêtre que `top_produits`)."""
    catalogue = dom_produits.tous(session, pme)
    index: dict[str, int] = {}
    for p in catalogue:
        for nom in [p.nom, *(p.alias or [])]:
            index.setdefault(finances.cle_produit(nom), p.id)
    maintenant = horloge.maintenant()
    quantites: dict[int, int] = {}
    chiffres: dict[int, int] = {}
    for ligne in finances.lignes_vendues(session, pme, maintenant - timedelta(days=FENETRE_PRODUITS_JOURS), maintenant + timedelta(days=1)):
        pid = index.get(finances.cle_produit(ligne.get("produit") or ""))
        if pid is None:
            continue
        quantites[pid] = quantites.get(pid, 0) + int(ligne["quantite"])
        chiffres[pid] = chiffres.get(pid, 0) + int(ligne["quantite"]) * int(ligne["prix_unitaire"])
    produits = [{"id": p.id, "nom": p.nom, "prix": p.prix, "ventes_30j": quantites.get(p.id, 0), "ca_30j": chiffres.get(p.id, 0)} for p in catalogue]
    produits.sort(key=lambda x: (-x["ca_30j"], normaliser(x["nom"])))
    return produits[:limite]


def rechercher(session: Session, pme: Pme, horloge: Horloge, q: str) -> dict:
    """Recherche globale (clients, produits, factures), insensible à la casse et aux accents. q : au moins 2 caractères."""
    vide: dict = {"clients": [], "produits": [], "factures": []}
    q = q.strip()
    cible = normaliser(q)
    if len(q) < 2 or not cible:
        return vide
    jetons = cible.split()

    def contient(*textes: str | None) -> bool:
        meule = normaliser(" ".join(t for t in textes if t))
        return all(j in meule for j in jetons)

    alias = {c.id: c.alias or [] for c in session.scalars(select(Client).where(Client.pme_id == pme.id, Client.actif.is_(True)))}
    clients = []
    for fiche, _ in fiches_clients(session, pme, horloge):
        if contient(fiche["nom"], fiche["quartier"], fiche["telephone"], *alias.get(fiche["id"], [])):
            detail = " · ".join(x for x in (fiche["quartier"], f"doit {format_fcfa(fiche['dette'])}" if fiche["dette"] else None) if x)
            clients.append({"id": fiche["id"], "nom": fiche["nom"], "detail": detail})
    clients.sort(key=lambda c: normaliser(c["nom"]))

    produits = [
        {"id": p.id, "nom": p.nom, "detail": format_fcfa(p.prix) + (f" / {p.unite}" if p.unite else "")}
        for p in dom_produits.tous(session, pme)
        if contient(p.nom, *(p.alias or []))
    ]

    factures = []
    noms = dict(session.execute(select(Client.id, Client.nom).where(Client.pme_id == pme.id)).all())
    for f in session.scalars(select(Facture).where(Facture.pme_id == pme.id, Facture.statut != "annulee").order_by(Facture.numero.desc())):
        client = noms.get(f.client_id, "?")
        if contient(client, f"facture {f.numero:03d}", str(f.numero)):
            factures.append({"id": f.id, "numero": f.numero, "client": client, "total": f.total, "statut": dom_factures.statut_affiche(f, horloge)})
    return {"clients": clients[:MAX_RECHERCHE], "produits": produits[:MAX_RECHERCHE], "factures": factures[:MAX_RECHERCHE]}
