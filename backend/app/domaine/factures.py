"""Factures : numérotation par PME, création, PDF, suivi du statut."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.argent import format_fcfa
from app.core.horloge import Horloge, en_local
from app.db.modeles import Action, Client, Facture, Pme

STATUTS_OUVERTS = ("envoyee", "en_retard")
FENETRE_ANNULATION = timedelta(minutes=10)


def total_facture(lignes: list[dict], frais: list[dict]) -> int:
    """Seule source de vérité pour le total d'une facture."""
    total = 0
    for ligne in lignes:
        q, pu = int(ligne["quantite"]), int(ligne["prix_unitaire"])
        if q <= 0 or pu <= 0:
            raise ValueError("quantité et prix unitaire doivent être positifs")
        total += q * pu
    for f in frais:
        if int(f["montant"]) < 0:
            raise ValueError("un frais ne peut pas être négatif")
        total += int(f["montant"])
    return total


def prochain_numero(session: Session, pme: Pme) -> int:
    dernier = session.scalar(select(func.max(Facture.numero)).where(Facture.pme_id == pme.id))
    return (dernier or 0) + 1


def creer(
    session: Session,
    pme: Pme,
    horloge: Horloge,
    *,
    client: Client,
    lignes: list[dict],
    frais: list[dict],
    confirmation_id: int,
    echeance: date | None = None,
    dossier_pdf: str | None = None,
) -> Facture:
    """Crée une facture « envoyée » (à la PME, pour transfert). Confirmation obligatoire."""
    if confirmation_id is None:
        raise ValueError("une facture ne se crée pas sans confirmation enregistrée")
    maintenant = horloge.maintenant()
    facture = Facture(
        pme_id=pme.id,
        numero=prochain_numero(session, pme),
        client_id=client.id,
        lignes=[
            {
                "produit": ligne.get("produit") or "Prestation",
                "quantite": int(ligne["quantite"]),
                "prix_unitaire": int(ligne["prix_unitaire"]),
            }
            for ligne in lignes
        ],
        frais=[{"libelle": f["libelle"], "montant": int(f["montant"])} for f in frais],
        total=total_facture(lignes, frais),
        echeance=echeance,
        statut="envoyee",
        creee_a=maintenant,
        confirmation_id=confirmation_id,
    )
    session.add(facture)
    session.flush()
    if dossier_pdf:
        facture.pdf_chemin = rendre_pdf(facture, pme, client, Path(dossier_pdf))
    session.add(
        Action(
            pme_id=pme.id,
            type="FACTURE",
            cible_id=facture.id,
            resume=f"facture n° {facture.numero:03d} de {facture.total} F",
            creee_a=maintenant,
            annulable_jusqua=maintenant + FENETRE_ANNULATION,
        )
    )
    session.flush()
    return facture


def ouvertes(session: Session, pme: Pme, client: Client | None = None) -> list[Facture]:
    requete = select(Facture).where(Facture.pme_id == pme.id, Facture.statut.in_(STATUTS_OUVERTS))
    if client is not None:
        requete = requete.where(Facture.client_id == client.id)
    return list(session.scalars(requete.order_by(Facture.numero)))


def par_numero(session: Session, pme: Pme, numero: int) -> Facture | None:
    return session.scalar(select(Facture).where(Facture.pme_id == pme.id, Facture.numero == numero))


def marquer_payee(session: Session, facture: Facture, horloge: Horloge) -> None:
    facture.statut = "payee"
    facture.payee_a = horloge.maintenant()
    session.flush()


def annuler(session: Session, facture: Facture) -> None:
    facture.statut = "annulee"
    session.flush()


def jours_de_retard(facture: Facture, horloge: Horloge) -> int:
    reference = facture.echeance or facture.creee_a.date()
    return max(0, (horloge.maintenant().date() - reference).days)


def rendre_pdf(facture: Facture, pme: Pme, client: Client, dossier: Path) -> str:
    """PDF simple et lisible (fpdf2, aucune dépendance système)."""
    from fpdf import FPDF  # import local : la génération reste optionnelle

    dossier_pme = dossier / str(pme.id)
    dossier_pme.mkdir(parents=True, exist_ok=True)
    chemin = dossier_pme / f"facture-{facture.numero:03d}.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, _ascii(pme.nom_commerce), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    if pme.quartier or pme.ville:
        pdf.cell(0, 7, _ascii(", ".join(p for p in (pme.quartier, pme.ville) if p)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"FACTURE N {facture.numero:03d}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    date_locale = en_local(facture.creee_a, pme.fuseau).strftime("%d/%m/%Y")
    pdf.cell(0, 7, f"Date : {date_locale}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _ascii(f"Client : {client.nom}"), new_x="LMARGIN", new_y="NEXT")
    if facture.echeance:
        pdf.cell(0, 7, f"Echeance : {facture.echeance.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 8, "Designation", border=1)
    pdf.cell(25, 8, "Qte", border=1, align="R")
    pdf.cell(35, 8, "Prix unit.", border=1, align="R")
    pdf.cell(40, 8, "Montant", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for ligne in facture.lignes:
        montant = int(ligne["quantite"]) * int(ligne["prix_unitaire"])
        pdf.cell(90, 8, _ascii(str(ligne["produit"])), border=1)
        pdf.cell(25, 8, str(ligne["quantite"]), border=1, align="R")
        pdf.cell(35, 8, _ascii(format_fcfa(int(ligne["prix_unitaire"]))), border=1, align="R")
        pdf.cell(40, 8, _ascii(format_fcfa(montant)), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    for f in facture.frais:
        pdf.cell(150, 8, _ascii(str(f["libelle"])), border=1)
        pdf.cell(40, 8, _ascii(format_fcfa(int(f["montant"]))), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(150, 9, "TOTAL", border=1)
    pdf.cell(40, 9, _ascii(format_fcfa(facture.total)), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Facture preparee avec Moki - Mon Kiosque", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(chemin))
    return str(chemin)


def _ascii(texte: str) -> str:
    """Les polices de base de fpdf2 sont latin-1 : on remplace l'espace fine et les caractères hors plage."""
    return texte.replace(" ", " ").encode("latin-1", "replace").decode("latin-1")


def libelle_echeance(facture: Facture) -> str:
    if facture.echeance:
        return facture.echeance.strftime("%d/%m/%Y")
    return "-"


def date_du_jour_locale(horloge: Horloge, fuseau: str) -> datetime:
    return en_local(horloge.maintenant(), fuseau)


SEUIL_RETARD_JOURS = 7


def etat(session: Session, pme: Pme, horloge: Horloge, limite: int = 12) -> list[tuple[int, str, int, str]]:
    """(numéro, client, total, état lisible) des factures, la plus récente d'abord."""
    lignes = []
    factures = session.scalars(select(Facture).where(Facture.pme_id == pme.id, Facture.statut != "annulee").order_by(Facture.numero.desc()).limit(limite))
    for f in factures:
        client = session.get(Client, f.client_id)
        if f.statut == "payee":
            libelle = "payée ✅"
        else:
            retard = jours_de_retard(f, horloge)
            libelle = f"en retard ({retard} j) ⚠️" if retard > SEUIL_RETARD_JOURS else "envoyée"
        lignes.append((f.numero, client.nom if client else "?", f.total, libelle))
    return lignes
