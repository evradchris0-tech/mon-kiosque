"""API des écrans de l'interface v2 (docs/06-interface-pro.md §5) : fines routes au-dessus du domaine.

Règles : la PME est toujours celle du jeton (aucun pme_id venant du client) ; un identifiant d'une autre PME donne 404.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Parametres
from app.db.modeles import Pme
from app.domaine import accueil as dom_accueil
from app.domaine import alertes as dom_alertes
from app.domaine import fiches, finances, historique, preferences
from app.domaine import pme as dom_pme
from app.integrations.whatsapp.interface import CanalFactice
from app.moki import pipeline

LIMITE_DEFAUT, LIMITE_MAX = 30, 100


def _limite(valeur: int) -> int:
    return max(1, min(LIMITE_MAX, valeur))


def _invalide(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=message)


def routeur_ecrans(p: Parametres, fabrique: sessionmaker[Session], deps: pipeline.Dependances, numero_courant, jeton_courant) -> APIRouter:
    r = APIRouter(prefix="/api")

    def _pme(s: Session, numero: str) -> Pme:
        pme = dom_pme.pme_par_numero(s, numero)
        if pme is None:
            raise HTTPException(status_code=404, detail="compte non inscrit : écris d'abord à Moki")
        return pme

    @r.post("/inscription")
    def inscription(corps: Any = Body(default=None), numero: str = Depends(numero_courant)) -> dict:
        try:
            valeurs = dom_pme.valider_inscription(corps)
        except dom_pme.ErreurValidation as e:
            raise _invalide(str(e)) from e
        with fabrique() as s:
            try:
                pme = dom_pme.inscrire(s, deps.horloge, numero, valeurs)
                s.commit()
            except (dom_pme.DejaInscrit, IntegrityError) as e:
                s.rollback()
                raise HTTPException(status_code=409, detail="ce numéro a déjà un compte") from e
            return {"pme": {"nom_commerce": pme.nom_commerce, "ville": pme.ville}}

    @r.get("/accueil")
    def accueil(numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            return dom_accueil.vue_accueil(s, _pme(s, numero), deps.horloge)

    @r.get("/alertes")
    def alertes(numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            pme = _pme(s, numero)
            liste = dom_alertes.avec_lecture(s, pme, dom_alertes.calculer(s, pme, deps.horloge))
            return {"non_lues": dom_alertes.non_lues(liste), "alertes": liste}

    @r.post("/alertes/lues")
    def alertes_lues(numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            preferences.marquer_alertes_lues(s, _pme(s, numero), deps.horloge.maintenant())
            s.commit()
            return {"non_lues": 0}

    @r.get("/historique")
    def liste_historique(
        type: str = "tout", q: str = "", limite: int = LIMITE_DEFAUT, avant: str | None = None, numero: str = Depends(numero_courant)  # noqa: A002 - nom imposé par le contrat
    ) -> dict:
        if type != "tout" and type not in historique.TYPES:
            raise _invalide("Type inconnu : choisis tout, vente, depense, facture ou paiement.")
        with fabrique() as s:
            try:
                elements, suivant = historique.page(
                    s, _pme(s, numero), deps.horloge, types=historique.TYPES if type == "tout" else (type,), q=q[:100], limite=_limite(limite), avant=avant or None
                )
            except historique.ErreurHistorique as e:
                raise _invalide(str(e)) from e
            return {"elements": elements, "suivant": suivant}

    @r.get("/historique/{type}/{element_id}")
    def detail_historique(type: str, element_id: int, numero: str = Depends(numero_courant)) -> dict:  # noqa: A002
        with fabrique() as s:
            vue = historique.detail(s, _pme(s, numero), deps.horloge, type, element_id)
            if vue is None:
                raise HTTPException(status_code=404, detail="opération introuvable")
            return vue

    @r.get("/factures")
    def liste_factures(statut: str = "tout", limite: int = LIMITE_DEFAUT, numero: str = Depends(numero_courant)) -> dict:
        if statut not in fiches.STATUTS_FACTURE:
            raise _invalide("Statut inconnu : choisis tout, envoyee, payee ou en_retard.")
        with fabrique() as s:
            return {"factures": fiches.liste_factures(s, _pme(s, numero), deps.horloge, statut, _limite(limite))}

    @r.get("/factures/{facture_id}")
    def fiche_facture(facture_id: int, numero: str = Depends(numero_courant), jeton: str = Depends(jeton_courant)) -> dict:
        with fabrique() as s:
            vue = fiches.vue_facture(s, _pme(s, numero), deps.horloge, facture_id, Path(p.dossier_factures))
            if vue is None:
                raise HTTPException(status_code=404, detail="facture introuvable")
        nom = vue.pop("pdf_nom")  # même mécanisme que /api/fichier : un fichier du dossier de la PME, jeton en paramètre
        return {**vue, "pdf_url": f"/api/fichier?nom={nom}&token={jeton}" if nom else None}

    @r.get("/clients")
    def liste_clients(limite: int = LIMITE_DEFAUT, numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            return {"clients": fiches.liste_clients(s, _pme(s, numero), deps.horloge, _limite(limite))}

    @r.get("/clients/{client_id}")
    def fiche_client(client_id: int, numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            vue = fiches.vue_client(s, _pme(s, numero), deps.horloge, client_id)
            if vue is None:
                raise HTTPException(status_code=404, detail="client introuvable")
            return vue

    @r.get("/produits")
    def liste_produits(limite: int = LIMITE_DEFAUT, numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            return {"produits": fiches.liste_produits(s, _pme(s, numero), deps.horloge, _limite(limite))}

    @r.get("/chiffres")
    def chiffres(periode: str = "mois", numero: str = Depends(numero_courant)) -> dict:
        if periode not in finances.PERIODES_ECRAN:
            raise _invalide("Période inconnue : choisis jour, semaine, mois ou annee.")
        with fabrique() as s:
            return finances.chiffres_ecran(s, _pme(s, numero), deps.horloge, periode)

    @r.get("/documents")
    def documents(numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            return dom_accueil.vue_documents(s, _pme(s, numero), deps.horloge)

    @r.get("/parametres")
    def lire_parametres(numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            return preferences.vue(s, _pme(s, numero))

    @r.put("/parametres")
    def modifier_parametres(corps: Any = Body(default=None), numero: str = Depends(numero_courant)) -> dict:
        try:
            commerce, prefs = preferences.valider(corps)
        except dom_pme.ErreurValidation as e:
            raise _invalide(str(e)) from e
        with fabrique() as s:
            pme = _pme(s, numero)
            preferences.appliquer(s, pme, commerce, prefs)
            s.commit()
            return preferences.vue(s, pme)

    @r.get("/connexions")
    def connexions(numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            _pme(s, numero)
        return dom_accueil.vue_connexions(isinstance(deps.canal, CanalFactice))

    @r.get("/recherche")
    def recherche(q: str = Query(default=""), numero: str = Depends(numero_courant)) -> dict:
        with fabrique() as s:
            return fiches.rechercher(s, _pme(s, numero), deps.horloge, q[:100])

    return r
