"""Historique unifié : ventes, dépenses, factures et paiements (actifs ou annulés), du plus récent au plus ancien.

Identifiant d'élément : « type-id » (ex. « vente-12 »). L'ordre est total et stable : (date, rang du type, id) décroissants,
ce qui permet une pagination par curseur (`avant` = identifiant du dernier élément reçu) sans doublon ni trou.
"""

from __future__ import annotations

import heapq
import re
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.argent import format_fcfa
from app.core.horloge import Horloge, en_local
from app.db.modeles import Action, Client, Depense, Facture, Paiement, Pme, Relance, Vente
from app.domaine import factures as dom_factures
from app.domaine.texte import normaliser

TYPES = ("vente", "depense", "facture", "paiement")
RANG = {"vente": 0, "depense": 1, "facture": 2, "paiement": 3}  # départage deux éléments de même date
LOT = 100
ID_MAX = 2_147_483_647
MODES = {"cash": "Espèces", "mobile_money": "Mobile Money", "credit": "À crédit"}
TYPES_DEPENSE = {"charge": "Charge du commerce", "stock": "Achat de stock", "retrait_perso": "Retrait personnel"}
SOURCES_PAIEMENT = {"declare": "déclaré par toi", "agregateur": "reçu par l'opérateur"}
ACTIONS = {"vente": "VENTE", "depense": "DEPENSE", "facture": "FACTURE", "paiement": "PAIEMENT_RECU"}
MODELES: dict[str, tuple[Any, str]] = {"vente": (Vente, "heure_envoi"), "depense": (Depense, "heure_envoi"), "facture": (Facture, "creee_a"), "paiement": (Paiement, "recu_a")}
_CURSEUR = re.compile(r"^(vente|depense|facture|paiement)-(\d{1,10})$")


class ErreurHistorique(ValueError):
    """Paramètre invalide (curseur inconnu…) : message en français."""


def iso(instant: datetime) -> str:
    return instant.replace(microsecond=0).isoformat()


class Contexte:
    """Noms de clients et rattachements des paiements, chargés une fois (pas de requête par élément)."""

    def __init__(self, session: Session, pme: Pme, horloge: Horloge) -> None:
        self.session, self.pme, self.horloge = session, pme, horloge
        self.clients: dict[int, str] = dict(session.execute(select(Client.id, Client.nom).where(Client.pme_id == pme.id)).all())
        self.factures: dict[int, tuple[int, int]] = {}  # id -> (numéro, client_id)
        self.ventes: dict[int, int | None] = {}  # id -> client_id

    def precharger_paiements(self, paiements: list[Paiement]) -> None:
        ids_f = {p.facture_id for p in paiements if p.facture_id and p.facture_id not in self.factures}
        ids_v = {p.vente_id for p in paiements if p.vente_id and p.vente_id not in self.ventes}
        if ids_f:
            for fid, numero, cid in self.session.execute(select(Facture.id, Facture.numero, Facture.client_id).where(Facture.pme_id == self.pme.id, Facture.id.in_(ids_f))):
                self.factures[fid] = (numero, cid)
        if ids_v:
            for vid, cid in self.session.execute(select(Vente.id, Vente.client_id).where(Vente.pme_id == self.pme.id, Vente.id.in_(ids_v))):
                self.ventes[vid] = cid


def _description(lignes: list[dict]) -> str:
    if not lignes:
        return "Article"
    premiere = f"{int(lignes[0]['quantite'])} × {lignes[0].get('produit') or 'Article'}"
    reste = len(lignes) - 1
    return premiere if reste == 0 else f"{premiere} + {reste} autre{'s' if reste > 1 else ''}"


def _element(type_: str, ligne_id: int, date: datetime, titre: str, detail: str, montant: int, sens: str, statut: str, client: str | None) -> dict:
    return {"id": f"{type_}-{ligne_id}", "type": type_, "date": iso(date), "titre": titre, "detail": detail, "montant": montant, "sens": sens, "statut": statut, "client": client}


def element(ctx: Contexte, type_: str, ligne: Any) -> dict:
    if type_ == "vente":
        client = ctx.clients.get(ligne.client_id) if ligne.client_id else ligne.client_nom_cite
        mode = MODES.get(ligne.parts_paiement[0]["mode"], "Paiement") if ligne.parts_paiement else "Paiement"
        if ligne.statut != "active":
            statut = "annule"
        elif ligne.credit_restant > 0:
            statut = "retard" if (ctx.horloge.maintenant() - ligne.heure_envoi).days > dom_factures.SEUIL_RETARD_JOURS else "en_attente"
        else:
            statut = "ok"
        return _element("vente", ligne.id, ligne.heure_envoi, _description(ligne.lignes), mode, ligne.total, "entree", statut, client)
    if type_ == "depense":
        libelle = ligne.libelle.strip()
        return _element("depense", ligne.id, ligne.heure_envoi, libelle[:1].upper() + libelle[1:], TYPES_DEPENSE.get(ligne.type, "Dépense"), ligne.montant, "sortie", "ok" if ligne.statut == "active" else "annule", None)
    if type_ == "facture":
        statut = dom_factures.statut_affiche(ligne, ctx.horloge)
        statut = {"payee": "ok", "annulee": "annule", "envoyee": "en_attente", "en_retard": "retard"}[statut]
        return _element("facture", ligne.id, ligne.creee_a, f"Facture n° {ligne.numero:03d}", _description(ligne.lignes), ligne.total, "neutre", statut, ctx.clients.get(ligne.client_id))
    numero_client = ctx.factures.get(ligne.facture_id) if ligne.facture_id else None
    client_id = numero_client[1] if numero_client else ctx.ventes.get(ligne.vente_id)
    detail = f"Facture n° {numero_client[0]:03d}" if numero_client else "Vente à crédit"
    if ligne.operateur:
        detail += f" · {ligne.operateur}"
    return _element("paiement", ligne.id, ligne.recu_a, "Paiement reçu", detail, ligne.montant, "entree", "ok" if ligne.statut == "confirme" else "annule", ctx.clients.get(client_id) if client_id else None)


def _filtres(type_: str, pme: Pme, client_id: int | None, actifs: bool) -> list:
    modele = MODELES[type_][0]
    filtres: list = [modele.pme_id == pme.id]
    if actifs:
        filtres.append({"vente": Vente.statut == "active", "depense": Depense.statut == "active", "facture": Facture.statut != "annulee", "paiement": Paiement.statut == "confirme"}[type_])
    if client_id is not None:
        if type_ in ("vente", "facture"):
            filtres.append(modele.client_id == client_id)
        elif type_ == "paiement":
            filtres.append(or_(
                Paiement.facture_id.in_(select(Facture.id).where(Facture.pme_id == pme.id, Facture.client_id == client_id)),
                Paiement.vente_id.in_(select(Vente.id).where(Vente.pme_id == pme.id, Vente.client_id == client_id)),
            ))
        else:
            filtres.append(Depense.id < 0)  # une dépense n'appartient à aucun client
    return filtres


def _lire(ctx: Contexte, type_: str, filtres: list, borne: tuple[datetime, int] | None) -> Iterator[Any]:
    """Lignes d'une source, de la plus récente à la plus ancienne, par lots (pagination par clé : aucun OFFSET)."""
    modele, nom_date = MODELES[type_]
    col = getattr(modele, nom_date)
    while True:
        requete = select(modele).where(*filtres)
        if borne is not None:
            requete = requete.where(or_(col < borne[0], and_(col == borne[0], modele.id < borne[1])))
        lot = list(ctx.session.scalars(requete.order_by(col.desc(), modele.id.desc()).limit(LOT)))
        if not lot:
            return
        if type_ == "paiement":
            ctx.precharger_paiements(lot)
        yield from lot
        if len(lot) < LOT:
            return
        borne = (getattr(lot[-1], nom_date), lot[-1].id)


def _ligne(ctx: Contexte, type_: str, ligne_id: int) -> Any:
    modele = MODELES[type_][0]
    return ctx.session.scalar(select(modele).where(modele.id == ligne_id, modele.pme_id == ctx.pme.id))


def _etiqueter(type_: str, lignes: Iterator[Any]) -> Iterator[tuple[tuple[datetime, int, int], str, Any]]:
    nom_date = MODELES[type_][1]
    for ligne in lignes:
        yield (getattr(ligne, nom_date), RANG[type_], ligne.id), type_, ligne


def _correspond(jetons: list[str], elt: dict) -> bool:
    meule = normaliser(f"{elt['titre']} {elt['detail']} {elt['client'] or ''}")
    return all(j in meule for j in jetons)


def page(
    session: Session,
    pme: Pme,
    horloge: Horloge,
    *,
    types: tuple[str, ...] = TYPES,
    q: str = "",
    limite: int = 30,
    avant: str | None = None,
    client_id: int | None = None,
    actifs: bool = False,
) -> tuple[list[dict], str | None]:
    """(éléments, curseur suivant | None). `avant` : identifiant du dernier élément déjà reçu."""
    ctx = Contexte(session, pme, horloge)
    bornes: dict[str, tuple[datetime, int] | None] = dict.fromkeys(types)
    if avant:
        m = _CURSEUR.match(avant)
        repere = _ligne(ctx, m.group(1), int(m.group(2))) if m else None
        if m is None or repere is None:
            raise ErreurHistorique("Curseur de pagination invalide.")
        rang_c, date_c = RANG[m.group(1)], getattr(repere, MODELES[m.group(1)][1])
        for t in types:  # un élément est « après » le curseur si sa clé (date, rang, id) est plus petite
            bornes[t] = (date_c, ID_MAX) if RANG[t] < rang_c else (date_c, repere.id) if RANG[t] == rang_c else (date_c, -1)
    flux = [_etiqueter(t, _lire(ctx, t, _filtres(t, pme, client_id, actifs), bornes[t])) for t in types]
    jetons = normaliser(q).split()
    elements: list[dict] = []
    for _, t, ligne in heapq.merge(*flux, key=lambda x: x[0], reverse=True):
        elt = element(ctx, t, ligne)
        if jetons and not _correspond(jetons, elt):
            continue
        elements.append(elt)
        if len(elements) > limite:
            break
    suivant = elements[limite - 1]["id"] if len(elements) > limite else None
    return elements[:limite], suivant


def _date_locale(instant: datetime, fuseau: str) -> str:
    return en_local(instant, fuseau).strftime("%d/%m/%Y")


def _ligne_detail(libelle: str, quantite: int, prix: int) -> dict:
    return {"libelle": libelle, "quantite": quantite, "prix_unitaire": prix, "montant": quantite * prix}


def detail(session: Session, pme: Pme, horloge: Horloge, type_: str, ligne_id: int) -> dict | None:
    """Détail d'un élément (lignes, notes, annulable) ; None si l'élément n'existe pas dans CETTE PME."""
    if type_ not in TYPES:
        return None
    ctx = Contexte(session, pme, horloge)
    ligne = _ligne(ctx, type_, ligne_id)
    if ligne is None:
        return None
    if type_ == "paiement":
        ctx.precharger_paiements([ligne])
    elt = element(ctx, type_, ligne)
    lignes: list[dict] = []
    notes: list[str] = []
    if type_ == "vente":
        lignes = [_ligne_detail(str(x.get("produit") or "Article"), int(x["quantite"]), int(x["prix_unitaire"])) for x in ligne.lignes]
        for part in ligne.parts_paiement:
            notes.append(f"Paiement : {MODES.get(part['mode'], part['mode']).lower()}.")
        if ligne.credit_restant > 0:
            notes.append(f"Reste à payer : {format_fcfa(ligne.credit_restant)}.")
        if ligne.statut != "active":
            notes.append("Vente annulée : elle ne compte plus dans tes chiffres.")
    elif type_ == "depense":
        lignes = [_ligne_detail(ligne.libelle, 1, ligne.montant)]
        notes.append(f"{TYPES_DEPENSE.get(ligne.type, 'Dépense')} ({'personnelle' if ligne.nature == 'perso' else 'professionnelle'}).")
        if ligne.type == "retrait_perso":
            notes.append("Un retrait personnel n'entre pas dans les charges ni dans le bénéfice.")
        if ligne.statut != "active":
            notes.append("Dépense annulée : elle ne compte plus dans tes chiffres.")
    elif type_ == "facture":
        lignes = [_ligne_detail(str(x.get("produit") or "Prestation"), int(x["quantite"]), int(x["prix_unitaire"])) for x in ligne.lignes]
        lignes += [_ligne_detail(str(f["libelle"]), 1, int(f["montant"])) for f in ligne.frais]
        if ligne.echeance:
            notes.append(f"Échéance : {ligne.echeance.strftime('%d/%m/%Y')}.")
        if ligne.statut == "payee" and ligne.payee_a:
            notes.append(f"Payée le {_date_locale(ligne.payee_a, pme.fuseau)}.")
        for r in session.scalars(select(Relance).where(Relance.pme_id == pme.id, Relance.facture_id == ligne.id).order_by(Relance.envoyee_a)):
            notes.append(f"Relance du {_date_locale(r.envoyee_a, pme.fuseau)} ({'envoyée sur WhatsApp' if r.mode == 'direct' else 'à transférer'}).")
        if ligne.statut == "annulee":
            notes.append("Facture annulée : elle ne compte plus dans tes chiffres.")
    else:
        lignes = [_ligne_detail(elt["detail"], 1, ligne.montant)]
        notes.append(f"Paiement {SOURCES_PAIEMENT.get(ligne.source, ligne.source)}.")
        if ligne.statut != "confirme":
            notes.append("Paiement annulé : le montant est de nouveau dû.")
    annulable = elt["statut"] != "annule" and session.scalar(
        select(Action.id).where(
            Action.pme_id == pme.id, Action.type == ACTIONS[type_], Action.cible_id == ligne.id,
            Action.annulee.is_(False), Action.annulable_jusqua.is_not(None), Action.annulable_jusqua >= horloge.maintenant(),
        ).limit(1)
    ) is not None
    return {"element": elt, "lignes": lignes, "notes": notes, "annulable": annulable}
