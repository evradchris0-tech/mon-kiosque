"""Dossier de crédit en PDF : calculé uniquement à partir des saisies (aucun chiffre inventé)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.argent import format_fcfa
from app.core.horloge import Horloge, en_local
from app.db.modeles import Pme
from app.domaine import finances
from app.domaine import paiements as dom_paiements
from app.domaine.factures import _ascii

MOIS_REQUIS = 6


def donnees(session: Session, pme: Pme, horloge: Horloge) -> dict:
    mensuel = finances.mensuel(session, pme, horloge, MOIS_REQUIS)
    hist = finances.historique_mois(session, pme, horloge)
    return {
        "mensuel": mensuel,
        "ventes": sum(m["ventes"] for m in mensuel),
        "charges": sum(m["charges"] for m in mensuel),
        "benefice": sum(m["benefice"] for m in mensuel),
        "tresorerie": finances.tresorerie(session, pme),
        "impayes": dom_paiements.total_impayes(session, pme),
        "historique_mois": hist,
        "manque_mois": max(0, MOIS_REQUIS - hist),
    }


def generer(session: Session, pme: Pme, horloge: Horloge, dossier: str) -> tuple[str, dict]:
    from fpdf import FPDF

    d = donnees(session, pme, horloge)
    local = en_local(horloge.maintenant(), pme.fuseau)
    dossier_pme = Path(dossier) / str(pme.id)
    dossier_pme.mkdir(parents=True, exist_ok=True)
    chemin = dossier_pme / f"dossier-credit-{local:%Y%m%d-%H%M%S}.pdf"

    def f(m: int) -> str:
        return _ascii(format_fcfa(m))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(255, 121, 0)
    pdf.rect(0, 0, 210, 34, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(12, 9)
    pdf.cell(0, 10, "DOSSIER DE CREDIT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_xy(12, 21)
    pdf.cell(0, 6, _ascii(f"{pme.nom_commerce} - {', '.join(x for x in (pme.quartier, pme.ville) if x)}"))
    pdf.set_text_color(20, 20, 20)
    pdf.set_xy(12, 40)
    debut_txt = d["mensuel"][0]["mois"] if d["mensuel"] else "-"
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Periode : {debut_txt} a {local:%m/%Y}   |   Edite le {local:%d/%m/%Y}", new_x="LMARGIN", new_y="NEXT")
    if pme.donnees_fictives:
        pdf.set_text_color(211, 47, 47)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "DONNEES FICTIVES - DOCUMENT DE DEMONSTRATION", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(20, 20, 20)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Synthese", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    synthese = [("Ventes (6 mois)", d["ventes"]), ("Charges du commerce", d["charges"]), ("Benefice", d["benefice"]), ("Tresorerie (argent disponible)", d["tresorerie"]), ("Impayes clients", d["impayes"])]
    for libelle, valeur in synthese:
        pdf.cell(110, 8, libelle, border="B")
        pdf.cell(60, 8, f(valeur), border="B", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Ventes mensuelles", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 10)
    for titre, largeur in [("Mois", 30), ("Ventes", 48), ("Charges", 48), ("Benefice", 48)]:
        pdf.cell(largeur, 8, titre, border=1, align="C" if titre == "Mois" else "R")
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    for m in d["mensuel"]:
        pdf.cell(30, 8, m["mois"], border=1, align="C")
        pdf.cell(48, 8, f(m["ventes"]), border=1, align="R")
        pdf.cell(48, 8, f(m["charges"]), border=1, align="R")
        pdf.cell(48, 8, f(m["benefice"]), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    haut_max, base_y, x0 = 40, pdf.get_y() + 46, 20
    maxi = max([m["ventes"] for m in d["mensuel"]] + [1])
    pdf.set_fill_color(255, 121, 0)
    for i, m in enumerate(d["mensuel"]):
        h = haut_max * max(m["ventes"], 0) / maxi
        pdf.rect(x0 + i * 28, base_y - h, 18, h, "F")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(x0 + i * 28 - 3, base_y + 1)
        pdf.cell(24, 5, m["mois"], align="C")
    pdf.set_y(base_y + 12)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(90, 90, 90)
    note = f"Historique disponible : {d['historique_mois']} mois."
    if d["manque_mois"]:
        note += f" Il manque {d['manque_mois']} mois pour atteindre {MOIS_REQUIS} mois de donnees."
    pdf.multi_cell(0, 5, _ascii(note), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5, _ascii("Document calcule uniquement a partir des saisies enregistrees dans Moki (Mon Kiosque). Aucun chiffre n'est invente."), new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(chemin))
    return str(chemin), d
