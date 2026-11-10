"""Carnet clients : ajout, recherche tolérante aux titres, aux accents et aux alias."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.modeles import Client, Pme
from app.domaine.texte import normaliser, normaliser_telephone, tokens_nom


def ajouter(
    session: Session,
    pme: Pme,
    nom: str,
    telephone: str | None = None,
    quartier: str | None = None,
) -> Client:
    client = Client(
        pme_id=pme.id,
        nom=nom.strip(),
        telephone=normaliser_telephone(telephone) if telephone else None,
        quartier=quartier,
        alias=[],
    )
    session.add(client)
    session.flush()
    return client


def tous(session: Session, pme: Pme) -> list[Client]:
    return list(
        session.scalars(
            select(Client).where(Client.pme_id == pme.id, Client.actif.is_(True)).order_by(Client.nom)
        )
    )


def libelle(client: Client) -> str:
    return f"{client.nom} ({client.quartier})" if client.quartier else client.nom


def rechercher(session: Session, pme: Pme, nom_cite: str) -> list[Client]:
    """Clients dont le nom (ou un alias) contient tous les jetons du nom cité.

    'Mme Ngo' trouve 'Ngo Claire' et 'Ngo Berthe' (ambigu) ; 'Jean' trouve 'Jean Mballa' ;
    'Lycée Technique' trouve 'Lycée Technique'.
    """
    jetons = tokens_nom(nom_cite)
    if not jetons:
        return []
    resultats: list[Client] = []
    cite_norm = normaliser(nom_cite)
    for client in tous(session, pme):
        noms = [client.nom, *(client.alias or [])]
        for nom in noms:
            if normaliser(nom) == cite_norm or jetons <= tokens_nom(nom):
                resultats.append(client)
                break
    # Une correspondance exacte l'emporte sur les correspondances partielles.
    exacts = [c for c in resultats if normaliser(c.nom) == cite_norm]
    return exacts if len(exacts) == 1 else resultats
