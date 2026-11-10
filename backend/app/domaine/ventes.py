"""Ventes : enregistrement, annulation, agrégats, détection de doublons."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import Action, Client, Pme, Vente

FENETRE_ANNULATION = timedelta(minutes=10)
FENETRE_DOUBLON = timedelta(minutes=5)


def total_des_lignes(lignes: list[dict]) -> int:
    """Seule source de vérité pour un total de vente : recalcul en code."""
    total = 0
    for ligne in lignes:
        q, pu = int(ligne["quantite"]), int(ligne["prix_unitaire"])
        if q <= 0 or pu <= 0:
            raise ValueError("quantité et prix unitaire doivent être positifs")
        total += q * pu
    return total


def enregistrer(
    session: Session,
    pme: Pme,
    horloge: Horloge,
    *,
    lignes: list[dict],
    mode: str,
    heure_envoi: datetime,
    client: Client | None = None,
    client_nom_cite: str | None = None,
    message_id: int | None = None,
) -> Vente:
    if mode not in ("cash", "mobile_money", "credit"):
        raise ValueError(f"mode de paiement invalide : {mode}")
    total = total_des_lignes(lignes)
    maintenant = horloge.maintenant()
    vente = Vente(
        pme_id=pme.id,
        heure_envoi=heure_envoi,
        heure_reception=maintenant,
        lignes=[
            {
                "produit": ligne.get("produit"),
                "quantite": int(ligne["quantite"]),
                "prix_unitaire": int(ligne["prix_unitaire"]),
            }
            for ligne in lignes
        ],
        total=total,
        parts_paiement=[{"mode": mode, "montant": total}],
        client_id=client.id if client else None,
        client_nom_cite=client_nom_cite,
        credit_restant=total if mode == "credit" else 0,
        statut="active",
        message_id=message_id,
    )
    session.add(vente)
    session.flush()
    if client is not None:
        client.dernier_achat = heure_envoi
    session.add(
        Action(
            pme_id=pme.id,
            type="VENTE",
            cible_id=vente.id,
            resume=f"vente de {total} F",
            creee_a=maintenant,
            annulable_jusqua=maintenant + FENETRE_ANNULATION,
        )
    )
    session.flush()
    return vente


def annuler(session: Session, vente: Vente) -> None:
    vente.statut = "annulee"
    vente.credit_restant = 0
    session.flush()


def actives_entre(session: Session, pme: Pme, debut: datetime, fin: datetime) -> list[Vente]:
    return list(
        session.scalars(
            select(Vente)
            .where(
                Vente.pme_id == pme.id,
                Vente.statut == "active",
                Vente.heure_envoi >= debut,
                Vente.heure_envoi < fin,
            )
            .order_by(Vente.heure_envoi)
        )
    )


def agregats(session: Session, pme: Pme, debut: datetime, fin: datetime) -> tuple[int, int, dict[str, int]]:
    """(nombre, total, total par mode de paiement) sur [debut, fin[."""
    par_mode = {"cash": 0, "mobile_money": 0, "credit": 0}
    nb, total = 0, 0
    for vente in actives_entre(session, pme, debut, fin):
        nb += 1
        total += vente.total
        for part in vente.parts_paiement:
            par_mode[part["mode"]] = par_mode.get(part["mode"], 0) + int(part["montant"])
    return nb, total, par_mode


def panier_moyen(session: Session, pme: Pme, horloge: Horloge, jours: int = 30) -> tuple[int, int]:
    """(nombre de ventes, panier moyen) sur les `jours` derniers jours."""
    depuis = horloge.maintenant() - timedelta(days=jours)
    nb, somme = session.execute(
        select(func.count(Vente.id), func.coalesce(func.sum(Vente.total), 0)).where(
            Vente.pme_id == pme.id, Vente.statut == "active", Vente.heure_envoi >= depuis
        )
    ).one()
    nb = int(nb)
    return nb, (int(somme) // nb if nb else 0)


def doublon_probable(session: Session, pme: Pme, horloge: Horloge, lignes: list[dict], total: int) -> bool:
    depuis = horloge.maintenant() - FENETRE_DOUBLON
    cle = sorted((str(ligne.get("produit") or ""), int(ligne["quantite"]), int(ligne["prix_unitaire"])) for ligne in lignes)
    for vente in session.scalars(
        select(Vente).where(
            Vente.pme_id == pme.id,
            Vente.statut == "active",
            Vente.total == total,
            Vente.heure_reception >= depuis,
        )
    ):
        cle_vente = sorted((str(ligne.get("produit") or ""), int(ligne["quantite"]), int(ligne["prix_unitaire"])) for ligne in vente.lignes)
        if cle_vente == cle:
            return True
    return False


def ventes_a_credit(session: Session, pme: Pme, client: Client | None = None) -> list[Vente]:
    requete = select(Vente).where(
        Vente.pme_id == pme.id, Vente.statut == "active", Vente.credit_restant > 0
    )
    if client is not None:
        requete = requete.where(Vente.client_id == client.id)
    return list(session.scalars(requete.order_by(Vente.heure_envoi)))
