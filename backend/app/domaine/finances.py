"""Chiffres de pilotage : ventes, charges, bénéfice, trésorerie, impôt estimé, historique.

Définitions (cahier des fonctionnalités) :
- ventes = ventes enregistrées + factures émises (non annulées) ;
- bénéfice = ventes − charges de la période (les achats de stock et les retraits perso n'y entrent pas) ;
- trésorerie = encaissements − paiements réels (charges, stock, retraits perso).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge, en_local, en_utc
from app.db.modeles import Depense, Facture, Paiement, Pme, Vente
from app.domaine import paiements as dom_paiements
from app.domaine import resumes as dom_resumes
from app.domaine.texte import normaliser, singulier
from app.moki.schemas import Periode, TypePeriode

TAUX_IGS_INDICATIF = 0.02
NOTE_IMPOT = "Estimation indicative à confirmer avec la DGI"
JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def _ventes(session: Session, pme: Pme, debut: datetime, fin: datetime) -> list[Vente]:
    return list(session.scalars(select(Vente).where(Vente.pme_id == pme.id, Vente.statut == "active", Vente.heure_envoi >= debut, Vente.heure_envoi < fin)))


def _factures(session: Session, pme: Pme, debut: datetime, fin: datetime) -> list[Facture]:
    return list(session.scalars(select(Facture).where(Facture.pme_id == pme.id, Facture.statut != "annulee", Facture.creee_a >= debut, Facture.creee_a < fin)))


def _depenses(session: Session, pme: Pme, debut: datetime, fin: datetime) -> list[Depense]:
    return list(session.scalars(select(Depense).where(Depense.pme_id == pme.id, Depense.statut == "active", Depense.heure_envoi >= debut, Depense.heure_envoi < fin)))


def chiffres(session: Session, pme: Pme, debut: datetime, fin: datetime) -> dict:
    ventes, factures, depenses = _ventes(session, pme, debut, fin), _factures(session, pme, debut, fin), _depenses(session, pme, debut, fin)
    par_mode = {"cash": 0, "mobile_money": 0, "credit": 0, "facture": 0}
    for v in ventes:
        for part in v.parts_paiement:
            par_mode[part["mode"]] = par_mode.get(part["mode"], 0) + int(part["montant"])
    par_mode["facture"] = sum(f.total for f in factures)
    ca = sum(v.total for v in ventes) + par_mode["facture"]
    charges = sum(d.montant for d in depenses if d.type == "charge")
    return {
        "ventes": ca,
        "nb": len(ventes) + len(factures),
        "charges": charges,
        "benefice": ca - charges,
        "stock": sum(d.montant for d in depenses if d.type == "stock"),
        "retraits": sum(d.montant for d in depenses if d.type == "retrait_perso"),
        "par_mode": par_mode,
    }


def chiffres_periode(session: Session, pme: Pme, periode: Periode | None, horloge: Horloge) -> dict:
    debut, fin, libelle = dom_resumes.bornes(periode, horloge, pme.fuseau)
    return {**chiffres(session, pme, debut, fin), "libelle": libelle}


def tresorerie(session: Session, pme: Pme) -> int:
    entrees = sum(int(part["montant"]) for v in session.scalars(select(Vente).where(Vente.pme_id == pme.id, Vente.statut == "active")) for part in v.parts_paiement if part["mode"] != "credit")
    entrees += sum(p.montant for p in session.scalars(select(Paiement).where(Paiement.pme_id == pme.id, Paiement.statut == "confirme")))
    sorties = sum(d.montant for d in session.scalars(select(Depense).where(Depense.pme_id == pme.id, Depense.statut == "active")))
    return entrees - sorties


def serie_7j(session: Session, pme: Pme, horloge: Horloge) -> list[dict]:
    local = en_local(horloge.maintenant(), pme.fuseau)
    tz = ZoneInfo(pme.fuseau)
    sortie = []
    for i in range(6, -1, -1):
        jour = (local - timedelta(days=i)).date()
        debut = en_utc(datetime(jour.year, jour.month, jour.day, tzinfo=tz))
        c = chiffres(session, pme, debut, debut + timedelta(days=1))
        sortie.append({"jour": JOURS[jour.weekday()], "ventes": c["ventes"]})
    return sortie


def top_produits(session: Session, pme: Pme, horloge: Horloge, jours: int = 30, n: int = 5) -> list[dict]:
    return top_produits_entre(session, pme, horloge.maintenant() - timedelta(days=jours), horloge.maintenant() + timedelta(days=1), n)


def top_produits_entre(session: Session, pme: Pme, debut: datetime, fin: datetime, n: int = 5) -> list[dict]:
    totaux: dict[str, list] = {}
    for ligne in lignes_vendues(session, pme, debut, fin):
        nom = ligne.get("produit") or "Autre"
        cle = cle_produit(nom)
        entree = totaux.setdefault(cle, [nom, 0])
        entree[1] += int(ligne["quantite"]) * int(ligne["prix_unitaire"])
    classement = sorted(totaux.values(), key=lambda x: -x[1])[:n]
    return [{"nom": nom, "total": total} for nom, total in classement]


def lignes_vendues(session: Session, pme: Pme, debut: datetime, fin: datetime) -> list[dict]:
    """Lignes (produit, quantité, prix) des ventes actives et des factures non annulées de la période."""
    return [ligne for v in _ventes(session, pme, debut, fin) for ligne in v.lignes] + [ligne for f in _factures(session, pme, debut, fin) for ligne in f.lignes]


def cle_produit(nom: str) -> str:
    """Clé de rapprochement d'un nom de produit (sans accents, casse, pluriel)."""
    return " ".join(singulier(m) for m in normaliser(nom).split())


def premiere_date(session: Session, pme: Pme) -> datetime | None:
    dates = [
        session.scalar(select(Vente.heure_envoi).where(Vente.pme_id == pme.id, Vente.statut == "active").order_by(Vente.heure_envoi).limit(1)),
        session.scalar(select(Facture.creee_a).where(Facture.pme_id == pme.id, Facture.statut != "annulee").order_by(Facture.creee_a).limit(1)),
        session.scalar(select(Depense.heure_envoi).where(Depense.pme_id == pme.id, Depense.statut == "active").order_by(Depense.heure_envoi).limit(1)),
    ]
    dates = [d for d in dates if d is not None]
    return min(dates) if dates else None


def historique_mois(session: Session, pme: Pme, horloge: Horloge) -> int:
    debut = premiere_date(session, pme)
    return 0 if debut is None else max(0, (horloge.maintenant() - debut).days // 30)


def mensuel(session: Session, pme: Pme, horloge: Horloge, nb: int = 6) -> list[dict]:
    local = en_local(horloge.maintenant(), pme.fuseau)
    tz = ZoneInfo(pme.fuseau)
    mois_liste = []
    annee, mois = local.year, local.month
    for _ in range(nb):
        mois_liste.append((annee, mois))
        mois -= 1
        if mois == 0:
            annee, mois = annee - 1, 12
    sortie = []
    for annee, mois in reversed(mois_liste):
        suivant = (annee + (mois // 12), mois % 12 + 1)
        debut = en_utc(datetime(annee, mois, 1, tzinfo=tz))
        fin = en_utc(datetime(suivant[0], suivant[1], 1, tzinfo=tz))
        c = chiffres(session, pme, debut, fin)
        sortie.append({"mois": f"{mois:02d}/{annee}", "ventes": c["ventes"], "charges": c["charges"], "benefice": c["benefice"]})
    return sortie


def impot_estime(session: Session, pme: Pme, horloge: Horloge) -> dict:
    """Estimation INDICATIVE : taux fixe sur le chiffre d'affaires annualisé. À confirmer avec la DGI."""
    fin = horloge.maintenant() + timedelta(days=1)
    debut = fin - timedelta(days=365)
    premiere = premiere_date(session, pme)
    if premiere is None:
        return {"estimation": 0, "ca_annuel": 0, "taux": TAUX_IGS_INDICATIF, "note": NOTE_IMPOT}
    jours = min(365, max(30, (horloge.maintenant() - premiere).days))
    ca = chiffres(session, pme, debut, fin)["ventes"]
    ca_annuel = round(ca * 365 / jours)
    return {"estimation": round(ca_annuel * TAUX_IGS_INDICATIF), "ca_annuel": ca_annuel, "taux": TAUX_IGS_INDICATIF, "note": NOTE_IMPOT}


def echeances(horloge: Horloge, fuseau: str) -> list[dict]:
    """Échéances fiscales INDICATIVES (à valider) : déclaration mensuelle le 15, IGS le 15 mars."""
    aujourd_hui = en_local(horloge.maintenant(), fuseau).date()
    sortie = []
    mensuelle = aujourd_hui.replace(day=15)
    if mensuelle < aujourd_hui:
        mensuelle = (aujourd_hui.replace(day=1) + timedelta(days=32)).replace(day=15)
    sortie.append({"libelle": "Déclaration mensuelle", "date": mensuelle.isoformat(), "jours": (mensuelle - aujourd_hui).days})
    mars = aujourd_hui.replace(month=3, day=15)
    if mars < aujourd_hui:
        mars = mars.replace(year=mars.year + 1)
    sortie.append({"libelle": "Paiement de l'IGS", "date": mars.isoformat(), "jours": (mars - aujourd_hui).days})
    return sorted(sortie, key=lambda e: e["jours"])


def prochaine_echeance(horloge: Horloge, fuseau: str) -> dict:
    return echeances(horloge, fuseau)[0]


MOIS = ["jan.", "fév.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
PERIODES_ECRAN = ("jour", "semaine", "mois", "annee")


def bornes_ecran(periode: str, horloge: Horloge, fuseau: str) -> tuple[datetime, datetime, str]:
    """(début UTC, fin UTC, libellé) des périodes de l'écran Chiffres ; mêmes bornes que le tableau pour jour/semaine/mois."""
    if periode == "annee":
        tz = ZoneInfo(fuseau)
        aujourd_hui = en_local(horloge.maintenant(), fuseau).date()
        debut = en_utc(datetime(aujourd_hui.year, 1, 1, tzinfo=tz))
        fin = en_utc(datetime(aujourd_hui.year, aujourd_hui.month, aujourd_hui.day, tzinfo=tz) + timedelta(days=1))
        return debut, fin, "Cette année"
    genre = {"jour": TypePeriode.AUJOURD_HUI, "semaine": TypePeriode.SEMAINE, "mois": TypePeriode.MOIS}[periode]
    return dom_resumes.bornes(Periode(type=genre), horloge, fuseau)


def _tranches(periode: str, debut_local: datetime, fin_local: datetime) -> list[tuple[str, datetime, datetime]]:
    """Découpe la période en tranches contiguës (heure locale) : (libellé, début, fin)."""
    tranches: list[tuple[str, datetime, datetime]] = []
    if periode == "jour":
        for h in range(0, 24, 3):
            tranches.append((f"{h} h", debut_local + timedelta(hours=h), debut_local + timedelta(hours=h + 3)))
    elif periode == "semaine":
        for i in range(7):
            jour = debut_local + timedelta(days=i)
            tranches.append((JOURS[jour.weekday()], jour, jour + timedelta(days=1)))
    elif periode == "mois":
        jour = debut_local
        while jour < fin_local:
            tranches.append((str(jour.day), jour, jour + timedelta(days=1)))
            jour += timedelta(days=1)
    else:
        for m in range(1, (fin_local - timedelta(seconds=1)).month + 1):
            debut = debut_local.replace(month=m)
            fin = debut_local.replace(year=debut.year + 1, month=1) if m == 12 else debut_local.replace(month=m + 1)
            tranches.append((MOIS[m - 1].capitalize(), debut, fin))
    return tranches


def serie_periode(session: Session, pme: Pme, horloge: Horloge, periode: str) -> list[dict]:
    """Ventes et charges par tranche de la période (jour : 3 h ; semaine/mois : jour ; année : mois). Une seule lecture en base."""
    debut, fin, _ = bornes_ecran(periode, horloge, pme.fuseau)
    debut_local = en_local(debut, pme.fuseau)
    tranches = _tranches(periode, debut_local, en_local(fin, pme.fuseau))
    ventes = [(en_local(v.heure_envoi, pme.fuseau), v.total) for v in _ventes(session, pme, debut, fin)]
    ventes += [(en_local(f.creee_a, pme.fuseau), f.total) for f in _factures(session, pme, debut, fin)]
    charges = [(en_local(d.heure_envoi, pme.fuseau), d.montant) for d in _depenses(session, pme, debut, fin) if d.type == "charge"]
    sortie = []
    for libelle, a, b in tranches:
        sortie.append({"libelle": libelle, "ventes": sum(m for t, m in ventes if a <= t < b), "charges": sum(m for t, m in charges if a <= t < b)})
    return sortie


def depenses_par_poste(session: Session, pme: Pme, debut: datetime, fin: datetime, n: int = 10) -> list[dict]:
    """Dépenses actives de la période regroupées par libellé (sans accents ni casse), les plus fortes d'abord."""
    totaux: dict[str, list] = {}
    for d in _depenses(session, pme, debut, fin):
        entree = totaux.setdefault(normaliser(d.libelle) or "autre", [d.libelle.strip().capitalize() or "Autre", 0])
        entree[1] += d.montant
    classement = sorted(totaux.values(), key=lambda x: (-x[1], x[0]))[:n]
    return [{"libelle": libelle, "total": total} for libelle, total in classement]


def chiffres_ecran(session: Session, pme: Pme, horloge: Horloge, periode: str) -> dict:
    """Écran Chiffres : mêmes fonctions que le tableau et le chat (chiffres, trésorerie), seule la période change."""
    debut, fin, libelle = bornes_ecran(periode, horloge, pme.fuseau)
    c = chiffres(session, pme, debut, fin)
    return {
        "periode": periode,
        "libelle": libelle,
        "ventes": c["ventes"],
        "charges": c["charges"],
        "benefice": c["benefice"],
        "stock": c["stock"],
        "retraits_perso": c["retraits"],
        "tresorerie": tresorerie(session, pme),
        "par_mode": c["par_mode"],
        "nb_ventes": c["nb"],
        "panier_moyen": c["ventes"] // c["nb"] if c["nb"] else 0,
        "serie": serie_periode(session, pme, horloge, periode),
        "top_produits": top_produits_entre(session, pme, debut, fin),
        "depenses_par_poste": depenses_par_poste(session, pme, debut, fin),
    }


def impayes(session: Session, pme: Pme) -> int:
    return dom_paiements.total_impayes(session, pme)


def jour_periode() -> Periode:
    return Periode(type=TypePeriode.AUJOURD_HUI)
