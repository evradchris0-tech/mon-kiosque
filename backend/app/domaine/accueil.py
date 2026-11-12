"""Écrans de synthèse : accueil, documents (dossier de crédit, impôt, échéances) et connexions."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.argent import format_fcfa
from app.core.horloge import Horloge, en_local
from app.db.modeles import Pme
from app.domaine import alertes as dom_alertes
from app.domaine import dossier, finances, historique, preferences
from app.domaine import factures as dom_factures
from app.domaine import paiements as dom_paiements
from app.moki.schemas import Periode, TypePeriode

JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
MAX_A_FAIRE = 5


def date_locale(horloge: Horloge, fuseau: str) -> str:
    local = en_local(horloge.maintenant(), fuseau)
    return f"{JOURS_FR[local.weekday()]} {local.day} {MOIS_FR[local.month - 1]}"


def prenom(nom_gerante: str | None) -> str | None:
    mots = (nom_gerante or "").split()
    return mots[0] if mots else None


def _action(ecran: str | None, params: dict | None = None) -> dict | None:
    return {"ecran": ecran, "params": params or {}} if ecran else None


def _a_faire(session: Session, pme: Pme, horloge: Horloge, nb_ventes_jour: int) -> list[dict]:
    taches: list[dict] = []
    ouvertes = sorted(dom_factures.ouvertes(session, pme), key=lambda f: (-dom_factures.jours_de_retard(f, horloge), f.numero))
    for f in ouvertes[:3]:
        retard = dom_factures.jours_de_retard(f, horloge)
        texte = f"{format_fcfa(f.total)} à encaisser" + (f", en retard de {retard} jours." if retard > 0 else ".")
        taches.append({"id": f"relance-facture-{f.id}", "type": "relance", "titre": f"Relancer pour la facture n° {f.numero:03d}", "texte": texte, "action": _action("facture", {"id": f.id})})
    if preferences.actif(session, pme, "rappels_fiscaux"):
        e = finances.prochaine_echeance(horloge, pme.fuseau)
        if e["jours"] <= dom_alertes.JOURS_ECHEANCE:
            taches.append({"id": f"echeance-{e['date']}", "type": "echeance", "titre": e["libelle"], "texte": f"Échéance {dom_alertes.jours_txt(e['jours'])}, le {e['date'][8:]}/{e['date'][5:7]}.", "action": _action("documents")})
    d = dossier.etat(session, pme, horloge)
    if d["manque_mois"] > 0:
        taches.append({"id": "dossier-historique", "type": "dossier", "titre": "Dossier de crédit", "texte": f"Il te manque {d['manque_mois']} mois d'historique pour un dossier complet.", "action": _action("documents")})
    else:
        taches.append({"id": "dossier-pret", "type": "dossier", "titre": "Dossier de crédit prêt", "texte": "Tu as assez d'historique : génère ton dossier en PDF.", "action": _action("documents")})
    if nb_ventes_jour == 0:
        taches.append({"id": "info-aucune-vente", "type": "info", "titre": "Aucune vente notée aujourd'hui", "texte": "Dis à Moki ce que tu as vendu, il note tout.", "action": _action("assistant")})
    return taches[:MAX_A_FAIRE]


def vue_accueil(session: Session, pme: Pme, horloge: Horloge) -> dict:
    jour = finances.chiffres_periode(session, pme, Periode(type=TypePeriode.AUJOURD_HUI), horloge)
    mois = finances.chiffres_periode(session, pme, Periode(type=TypePeriode.MOIS), horloge)
    alertes = dom_alertes.avec_lecture(session, pme, dom_alertes.calculer(session, pme, horloge))
    non_lues = [a for a in alertes if not a["lue"]]
    principale = None
    if non_lues:
        a = non_lues[0]
        principale = {"id": a["id"], "niveau": a["niveau"], "titre": a["titre"], "texte": a["texte"], "action": a["action"]}
    recentes, _ = historique.page(session, pme, horloge, limite=5)
    return {
        "gerante": prenom(pme.nom_gerante),
        "commerce": pme.nom_commerce,
        "demo": pme.donnees_fictives,
        "date_locale": date_locale(horloge, pme.fuseau),
        "kpis": {
            "ventes_jour": jour["ventes"],
            "nb_ventes_jour": jour["nb"],
            "tresorerie": finances.tresorerie(session, pme),
            "benefice_mois": mois["benefice"],
            "impayes": dom_paiements.total_impayes(session, pme),
        },
        "alerte_principale": principale,
        "a_faire": _a_faire(session, pme, horloge, jour["nb"]),
        "serie_7j": finances.serie_7j(session, pme, horloge),
        "activite_recente": recentes,
        "non_lues": len(non_lues),
    }


def vue_documents(session: Session, pme: Pme, horloge: Horloge) -> dict:
    est = finances.impot_estime(session, pme, horloge)
    return {
        "dossier": dossier.etat(session, pme, horloge),
        "impot": {"estimation": est["estimation"], "ca_annuel": est["ca_annuel"], "taux": est["taux"], "note": est["note"]},
        "echeances": finances.echeances(horloge, pme.fuseau),
    }


def vue_connexions(canal_simule: bool) -> dict:
    """État des canaux : WhatsApp (simulé tant que le canal est factice), le reste est à venir."""
    return {"connexions": [
        {"id": "whatsapp", "nom": "WhatsApp", "statut": "simule" if canal_simule else "connecte",
         "detail": "Démo : les messages sont simulés, rien n'est envoyé aux clients." if canal_simule else "Moki répond sur ton WhatsApp."},
        {"id": "orange_money", "nom": "Orange Money", "statut": "bientot", "detail": "Bientôt : les paiements reçus seront notés tout seuls."},
        {"id": "mtn_momo", "nom": "MTN MoMo", "statut": "bientot", "detail": "Bientôt : les paiements reçus seront notés tout seuls."},
        {"id": "banque", "nom": "Banque", "statut": "bientot", "detail": "Prévu : relevé bancaire pour compléter ton dossier de crédit."},
        {"id": "dgi", "nom": "DGI (impôts)", "statut": "bientot", "detail": "Prévu : déclarations et échéances officielles."},
    ]}
