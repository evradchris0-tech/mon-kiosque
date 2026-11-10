"""Paiements déclarés (étage A). L'étage B (agrégateur) ajoutera la source 'agregateur'."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.horloge import Horloge
from app.db.modeles import Action, Client, Facture, Paiement, Pme, Vente
from app.domaine import factures as dom_factures
from app.domaine import ventes as dom_ventes


def declarer_sur_facture(session: Session, pme: Pme, horloge: Horloge, facture: Facture) -> Paiement:
    if facture.pme_id != pme.id:
        raise PermissionError("facture d'une autre PME")
    paiement = Paiement(
        pme_id=pme.id,
        facture_id=facture.id,
        montant=facture.total,
        source="declare",
        recu_a=horloge.maintenant(),
        statut="confirme",
    )
    session.add(paiement)
    dom_factures.marquer_payee(session, facture, horloge)
    session.flush()
    session.add(
        Action(
            pme_id=pme.id,
            type="PAIEMENT_RECU",
            cible_id=paiement.id,
            resume=f"paiement de {facture.total} F sur la facture n° {facture.numero:03d}",
            creee_a=horloge.maintenant(),
            annulable_jusqua=horloge.maintenant() + dom_ventes.FENETRE_ANNULATION,
        )
    )
    session.flush()
    return paiement


def declarer_sur_vente(session: Session, pme: Pme, horloge: Horloge, vente: Vente) -> Paiement:
    if vente.pme_id != pme.id:
        raise PermissionError("vente d'une autre PME")
    montant = vente.credit_restant
    paiement = Paiement(
        pme_id=pme.id,
        vente_id=vente.id,
        montant=montant,
        source="declare",
        recu_a=horloge.maintenant(),
        statut="confirme",
    )
    session.add(paiement)
    vente.credit_restant = 0
    session.flush()
    session.add(
        Action(
            pme_id=pme.id,
            type="PAIEMENT_RECU",
            cible_id=paiement.id,
            resume=f"paiement de {montant} F sur une vente à crédit",
            creee_a=horloge.maintenant(),
            annulable_jusqua=horloge.maintenant() + dom_ventes.FENETRE_ANNULATION,
        )
    )
    session.flush()
    return paiement


def annuler(session: Session, paiement: Paiement, horloge: Horloge) -> None:
    paiement.statut = "annule"
    if paiement.facture_id:
        facture = session.get(Facture, paiement.facture_id)
        if facture is not None:
            facture.statut = "envoyee"
            facture.payee_a = None
    if paiement.vente_id:
        vente = session.get(Vente, paiement.vente_id)
        if vente is not None:
            vente.credit_restant = paiement.montant
    session.flush()


def reste_du_client(session: Session, pme: Pme, client: Client) -> int:
    factures = dom_factures.ouvertes(session, pme, client)
    ventes = dom_ventes.ventes_a_credit(session, pme, client)
    return sum(f.total for f in factures) + sum(v.credit_restant for v in ventes)


def total_impayes(session: Session, pme: Pme) -> int:
    factures = dom_factures.ouvertes(session, pme)
    ventes = dom_ventes.ventes_a_credit(session, pme)
    return sum(f.total for f in factures) + sum(v.credit_restant for v in ventes)


def impayes_par_client(session: Session, pme: Pme) -> list[tuple[str, int, str]]:
    """(nom, montant dû, détail) trié par montant décroissant."""
    cumul: dict[int | None, list] = {}
    for f in dom_factures.ouvertes(session, pme):
        cumul.setdefault(f.client_id, [0, []])
        cumul[f.client_id][0] += f.total
        cumul[f.client_id][1].append(f"facture n° {f.numero:03d}")
    for v in dom_ventes.ventes_a_credit(session, pme):
        cle = v.client_id
        cumul.setdefault(cle, [0, []])
        cumul[cle][0] += v.credit_restant
        cumul[cle][1].append("vente à crédit")
    resultat: list[tuple[str, int, str]] = []
    for client_id, (montant, details) in cumul.items():
        nom = "client non identifié"
        if client_id is not None:
            client = session.scalar(select(Client).where(Client.id == client_id, Client.pme_id == pme.id))
            if client is not None:
                nom = client.nom
        resultat.append((nom, montant, ", ".join(details)))
    return sorted(resultat, key=lambda x: -x[1])
