"""Inscription par WhatsApp (A1, A2) : un numéro = un compte, 3 questions (nom, ville, secteur)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.modeles import Inscription, NumeroAutorise, Pme
from app.domaine import pme as dom_pme
from app.moki import reponses


def traiter(session: Session, deps, message) -> tuple[list[str], str]:
    """Renvoie (textes à envoyer, motif)."""
    numero = message.numero
    horloge = deps.horloge
    deja = session.scalar(select(Pme.id).where(Pme.numero_whatsapp == numero)) or session.scalar(select(NumeroAutorise.id).where(NumeroAutorise.numero == numero))
    if deja is not None:
        return [reponses.compte_indisponible()], "compte_indisponible"

    ins = session.scalar(select(Inscription).where(Inscription.numero == numero))
    if ins is None:
        session.add(Inscription(numero=numero, etape="nom", cree_a=horloge.maintenant()))
        session.flush()
        return [reponses.bienvenue_nom()], "inscription_debut"

    texte = (message.texte or "").strip()
    if not texte:
        return [reponses.inscription_ecrire()], "inscription_attente"
    if ins.etape == "nom":
        ins.nom_commerce = texte[:120]
        ins.etape = "ville"
        session.flush()
        return [reponses.inscription_ville(ins.nom_commerce)], "inscription_ville"
    if ins.etape == "ville":
        ins.ville = texte[:60]
        ins.etape = "secteur"
        session.flush()
        return [reponses.inscription_secteur()], "inscription_secteur"
    # secteur : dernière question, on crée le compte
    ins.secteur = texte[:60]
    pme = dom_pme.creer_pme(session, horloge, nom_commerce=ins.nom_commerce or "Mon commerce", numero_whatsapp=numero, ville=ins.ville, secteur=ins.secteur)
    nom = pme.nom_commerce
    session.delete(ins)
    session.flush()
    return [reponses.inscription_ok(nom)], "inscription_ok"
