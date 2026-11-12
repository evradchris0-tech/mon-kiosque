"""Alertes de l'appli, calculées à la demande (rien n'est stocké sauf « lues jusqu'à » dans les préférences).

Chaque alerte a un identifiant stable et une date d'événement : « lue » = date <= instant où la gérante a tout marqué lu.
- retard    : facture ouverte depuis plus de 7 jours (urgent), date = jour où le retard a dépassé 7 jours ;
- echeance  : échéance fiscale à 15 jours ou moins (attention, urgent à 3 jours ou moins) ;
- resume    : résumé du soir envoyé dans les dernières 24 h (info) ;
- charge    : charge du mois (par libellé) supérieure de plus de 30 % à la moyenne des 3 mois précédents (attention) ;
- client    : client sans achat depuis plus de 30 jours (info, les 5 plus gros clients au plus).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.argent import format_fcfa
from app.core.horloge import Horloge, en_local, en_utc
from app.db.modeles import Client, Depense, Message, Pme
from app.domaine import factures as dom_factures
from app.domaine import fiches, finances, historique, preferences
from app.domaine.texte import normaliser

JOURS_ECHEANCE = 15
JOURS_ECHEANCE_URGENT = 3
HAUSSE_CHARGE_POURCENT = 30
MOIS_REFERENCE = 3
MAX_ALERTES_CLIENTS = 5
FENETRE_RESUME = timedelta(hours=24)
NIVEAUX = {"urgent": 0, "attention": 1, "info": 2}


def jours_txt(n: int) -> str:
    return "aujourd'hui" if n == 0 else "demain" if n == 1 else f"dans {n} jours"


def _alerte(id_: str, type_: str, niveau: str, titre: str, texte: str, instant: datetime, ecran: str | None, params: dict | None = None) -> dict:
    return {
        "id": id_, "type": type_, "niveau": niveau, "titre": titre, "texte": texte, "date": historique.iso(instant),
        "action": {"ecran": ecran, "params": params or {}} if ecran else None,
    }


def _retards(session: Session, pme: Pme, horloge: Horloge) -> list[dict]:
    noms = dict(session.execute(select(Client.id, Client.nom).where(Client.pme_id == pme.id)).all())
    sortie = []
    for f in dom_factures.ouvertes(session, pme):
        retard = dom_factures.jours_de_retard(f, horloge)
        if retard <= dom_factures.SEUIL_RETARD_JOURS:
            continue
        depuis = datetime.combine((f.echeance or f.creee_a.date()) + timedelta(days=dom_factures.SEUIL_RETARD_JOURS + 1), time.min)
        sortie.append(_alerte(
            f"retard-facture-{f.id}", "retard", "urgent", f"Facture n° {f.numero:03d} en retard",
            f"{noms.get(f.client_id, 'Un client')} te doit {format_fcfa(f.total)} depuis {retard} jours.", depuis, "facture", {"id": f.id},
        ))
    return sortie


def _echeances(pme: Pme, horloge: Horloge) -> list[dict]:
    sortie = []
    for e in finances.echeances(horloge, pme.fuseau):
        if e["jours"] > JOURS_ECHEANCE:
            continue
        jour = date.fromisoformat(e["date"])
        urgent = e["jours"] <= JOURS_ECHEANCE_URGENT
        depuis = datetime.combine(jour - timedelta(days=JOURS_ECHEANCE_URGENT if urgent else JOURS_ECHEANCE), time.min)
        id_ = f"echeance-igs-{e['date']}" if "IGS" in e["libelle"] else f"echeance-{e['date']}"
        sortie.append(_alerte(
            id_, "echeance", "urgent" if urgent else "attention", f"{e['libelle']} {jours_txt(e['jours'])}",
            f"Échéance le {jour:%d/%m/%Y}. Dates indicatives : à confirmer avec la DGI.", depuis, "documents",
        ))
    return sortie


def _resume(session: Session, pme: Pme, horloge: Horloge) -> list[dict]:
    message = session.scalar(
        select(Message).where(
            Message.pme_id == pme.id, Message.type == "notification", Message.direction == "sortant",
            Message.texte.startswith("Résumé du soir"), Message.heure_reception >= horloge.maintenant() - FENETRE_RESUME,
        ).order_by(Message.id.desc()).limit(1)
    )
    if message is None:
        return []
    texte = (message.texte or "").removeprefix("Résumé du soir.").strip()
    return [_alerte(f"resume-{message.id}", "resume", "info", "Résumé du soir disponible", texte, message.heure_reception, "chiffres", {"periode": "jour"})]


def _mois_local(instant: datetime, fuseau: str) -> int:
    local = en_local(instant, fuseau)
    return local.year * 12 + local.month


def _depasse(cumul: int, somme_precedents: int, n: int) -> bool:
    """cumul > moyenne × 1,30, en entiers (pas d'arrondi flottant)."""
    return cumul * 100 * n > somme_precedents * (100 + HAUSSE_CHARGE_POURCENT)


def _charges(session: Session, pme: Pme, horloge: Horloge) -> list[dict]:
    """Par libellé de charge : total du mois en cours contre la moyenne des 3 mois précédents (au moins 2 mois avec dépense)."""
    local = en_local(horloge.maintenant(), pme.fuseau)
    courant = local.year * 12 + local.month
    depart = courant - MOIS_REFERENCE
    debut = en_utc(datetime((depart - 1) // 12, (depart - 1) % 12 + 1, 1, tzinfo=ZoneInfo(pme.fuseau)))
    depenses = session.scalars(
        select(Depense).where(Depense.pme_id == pme.id, Depense.statut == "active", Depense.type == "charge", Depense.heure_envoi >= debut)
        .order_by(Depense.heure_envoi, Depense.id)
    )
    par_libelle: dict[str, list[Depense]] = {}
    for d in depenses:
        par_libelle.setdefault(normaliser(d.libelle) or "autre", []).append(d)
    sortie = []
    for cle, lignes in par_libelle.items():
        mensuel: dict[int, int] = {}
        for d in lignes:
            ecart = courant - _mois_local(d.heure_envoi, pme.fuseau)
            if 0 <= ecart <= MOIS_REFERENCE:
                mensuel[ecart] = mensuel.get(ecart, 0) + d.montant
        precedents = [mensuel[i] for i in range(1, MOIS_REFERENCE + 1) if mensuel.get(i, 0) > 0]
        total_mois = mensuel.get(0, 0)
        if len(precedents) < 2:
            continue
        somme, n = sum(precedents), len(precedents)
        if not _depasse(total_mois, somme, n):
            continue
        cumul, instant = 0, lignes[-1].heure_envoi
        for d in lignes:
            if _mois_local(d.heure_envoi, pme.fuseau) != courant:
                continue
            cumul += d.montant
            if _depasse(cumul, somme, n):
                instant = d.heure_envoi
                break
        libelle = lignes[-1].libelle.strip()
        libelle = libelle[:1].upper() + libelle[1:]
        hausse = total_mois * n * 100 // somme - 100
        sortie.append(_alerte(
            f"charge-{cle.replace(' ', '-')}-{local.year}-{local.month:02d}", "charge", "attention", f"{libelle} en hausse",
            f"{libelle} : {format_fcfa(total_mois)} ce mois, soit {hausse} % de plus que ta moyenne des mois précédents ({format_fcfa(somme // n)}).",
            instant, "chiffres", {"periode": "mois"},
        ))
    return sortie


def _clients_inactifs(session: Session, pme: Pme, horloge: Horloge) -> list[dict]:
    inactifs = [(f, d) for f, d in fiches.fiches_clients(session, pme, horloge) if f["inactif"] and d is not None]
    inactifs.sort(key=lambda x: (-x[0]["total_achats"], x[0]["id"]))
    sortie = []
    for fiche, dernier in inactifs[:MAX_ALERTES_CLIENTS]:
        jours = (horloge.maintenant() - dernier).days
        sortie.append(_alerte(
            f"client-inactif-{fiche['id']}", "client", "info", f"{fiche['nom']} n'a rien acheté depuis un moment",
            f"Dernier achat il y a {jours} jours. Un petit mot pour reprendre contact ?", dernier + timedelta(days=fiches.JOURS_INACTIF), "client", {"id": fiche["id"]},
        ))
    return sortie


def calculer(session: Session, pme: Pme, horloge: Horloge) -> list[dict]:
    """Alertes du moment, les plus graves d'abord (puis les plus récentes). `lue` n'est pas encore renseigné."""
    alertes = _retards(session, pme, horloge) + _charges(session, pme, horloge) + _clients_inactifs(session, pme, horloge)
    if preferences.actif(session, pme, "rappels_fiscaux"):
        alertes += _echeances(pme, horloge)
    if preferences.actif(session, pme, "resume_du_soir"):
        alertes += _resume(session, pme, horloge)
    alertes.sort(key=lambda a: (NIVEAUX[a["niveau"]], _inverse(a["date"]), a["id"]))
    return alertes


def _inverse(iso: str) -> float:
    return -datetime.fromisoformat(iso).timestamp()


def avec_lecture(session: Session, pme: Pme, alertes: list[dict]) -> list[dict]:
    """Ajoute `lue` : une alerte est lue si sa date <= instant du dernier « tout marquer comme lu »."""
    limite = preferences.alertes_lues_jusqua(session, pme)
    return [{**a, "lue": limite is not None and datetime.fromisoformat(a["date"]) <= limite} for a in alertes]


def non_lues(alertes: list[dict]) -> int:
    return sum(1 for a in alertes if not a["lue"])
