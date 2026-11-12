"""API : webhook WhatsApp, console interne, santé."""

from __future__ import annotations

import asyncio
import contextlib
import json
import secrets
from datetime import timedelta
from html import escape
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import demo, services
from app.api import appli, ecrans, ui
from app.core.config import Parametres, parametres
from app.core.horloge import en_local
from app.db.base import Base, creer_moteur, fabrique_sessions
from app.db.modeles import CasAVerifier, Journal, Message, Pme, Vente
from app.integrations.whatsapp import webhook as wh
from app.integrations.whatsapp.interface import MessageEntrant
from app.moki import pipeline
from app.workers import rappels_fiscaux, resume_du_soir


class EntreeSimulation(BaseModel):
    pme_id: int
    texte: str


def creer_app(p: Parametres | None = None, fabrique: sessionmaker[Session] | None = None, deps: pipeline.Dependances | None = None) -> FastAPI:
    p = p or parametres()
    if fabrique is None:
        moteur = creer_moteur(p.database_url)
        Base.metadata.create_all(moteur)  # en prod : migrations Alembic
        fabrique = fabrique_sessions(moteur)
    deps = deps or services.construire_dependances(p)
    async def boucle_planifiee() -> None:
        """Toutes les minutes : résumé de 19 h et rappels fiscaux (chacun une seule fois, idempotents)."""
        while True:
            await asyncio.sleep(60)
            with contextlib.suppress(Exception):
                await asyncio.to_thread(resume_du_soir.executer, fabrique, deps.canal, deps.horloge, p.heure_resume)
                await asyncio.to_thread(rappels_fiscaux.executer, fabrique, deps.canal, deps.horloge)

    @contextlib.asynccontextmanager
    async def cycle(_: FastAPI):
        tache = asyncio.create_task(boucle_planifiee()) if p.planificateur else None
        yield
        if tache:
            tache.cancel()

    app = FastAPI(title="Moki", version="0.1.0", lifespan=cycle)
    if p.demo_seed:
        with fabrique() as s_demo:
            if not demo.deja_peuple(s_demo):
                demo.peupler(s_demo, deps.horloge)
    auth = appli.Authentification(p)
    app.include_router(appli.routeur(p, fabrique, deps, auth))
    app.include_router(ecrans.routeur_ecrans(p, fabrique, deps, auth.numero_courant, auth.jeton_courant))
    app.mount("/ui", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static" / "ui", html=True), name="ui")  # nouvelle interface (v2)
    securite = HTTPBasic()

    def console(creds: HTTPBasicCredentials = Depends(securite)) -> str:
        ok_u = secrets.compare_digest(creds.username, p.console_utilisateur)
        ok_p = secrets.compare_digest(creds.password, p.console_mot_de_passe)
        if not (ok_u and ok_p):
            raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
        return creds.username

    @app.get("/sante")
    def sante() -> dict:
        with fabrique() as s:
            s.execute(select(1))
        return {"statut": "ok", "env": p.env}

    @app.get("/webhooks/whatsapp")
    def verification(request: Request) -> Response:
        q = request.query_params
        if q.get("hub.mode") == "subscribe" and secrets.compare_digest(q.get("hub.verify_token", ""), p.whatsapp_jeton_verification):
            return Response(content=q.get("hub.challenge", ""), media_type="text/plain")
        raise HTTPException(status_code=403)

    @app.post("/webhooks/whatsapp")
    async def reception(request: Request, taches: BackgroundTasks) -> dict:
        corps = await request.body()
        if p.env != "dev" or p.whatsapp_secret_app:
            if not wh.verifier_signature(p.whatsapp_secret_app, corps, request.headers.get("x-hub-signature-256")):
                raise HTTPException(status_code=401, detail="signature invalide")
        try:
            charge = json.loads(corps)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail="JSON invalide") from e
        for entrant in wh.extraire_messages(charge):
            taches.add_task(services.traiter_entrant, fabrique, deps, entrant)  # accusé immédiat, traitement ensuite
        return {"recu": True}

    @app.get("/console", response_class=HTMLResponse)
    def tableau(_: str = Depends(console)) -> str:
        with fabrique() as s:
            debut = deps.horloge.maintenant() - timedelta(hours=24)
            nb_pme = s.scalar(select(func.count(Pme.id)))
            ventes_24h = s.scalar(select(func.count(Vente.id)).where(Vente.statut == "active", Vente.heure_reception >= debut))
            msgs_24h = s.scalar(select(func.count(Message.id)).where(Message.direction == "entrant", Message.heure_reception >= debut))
            ouverts = s.scalars(select(CasAVerifier).where(CasAVerifier.traite_a.is_(None)).order_by(CasAVerifier.id.desc()).limit(50)).all()
            lignes = []
            for pme in s.scalars(select(Pme).order_by(Pme.id)).all():
                nb = s.scalar(select(func.count(Vente.id)).where(Vente.pme_id == pme.id, Vente.statut == "active"))
                lignes.append([escape(pme.nom_commerce), escape(pme.numero_whatsapp), escape(pme.quartier or "-"), str(nb), ui.pastille(pme.statut, "vert" if pme.statut == "actif" else "ambre"), f'<a href="/console/pme/{pme.id}">Voir →</a>'])
            cas = [[f"#{c.id}", ui.pastille(c.motif, "rouge" if c.gravite == "grave" else "ambre"), str(c.pme_id or "-"), escape(str((c.details or {}).get("texte", ""))[:90])] for c in ouverts]
        corps = (
            "<h1>Tableau de bord</h1><p class='sous'>Activité des dernières 24 heures</p>"
            + '<div class="grille">'
            + ui.stat(nb_pme, "PME inscrites") + ui.stat(msgs_24h, "messages reçus") + ui.stat(ventes_24h, "ventes notées", "ok")
            + ui.stat(len(ouverts), "cas à vérifier", "alerte" if ouverts else "ok") + "</div>"
            + "<h2>PME</h2>" + ui.tableau(["Commerce", "WhatsApp", "Quartier", "Ventes", "Statut", ""], lignes, "Aucune PME inscrite.")
            + "<h2>À vérifier</h2>" + ui.tableau(["N°", "Motif", "PME", "Message"], cas, "Rien à vérifier. 👍")
        )
        return ui.page("Tableau de bord", corps, "tableau")

    @app.get("/console/pme/{pme_id}", response_class=HTMLResponse)
    def conversations(pme_id: int, _: str = Depends(console)) -> str:
        with fabrique() as s:
            pme = s.get(Pme, pme_id)
            if pme is None:
                raise HTTPException(status_code=404)
            msgs = list(reversed(s.scalars(select(Message).where(Message.pme_id == pme_id).order_by(Message.id.desc()).limit(100)).all()))
            bulles = "".join(ui.bulle(m.texte or m.transcription or "(média)", m.direction == "entrant", f"{en_local(m.heure_reception, pme.fuseau):%d/%m %H:%M}") for m in msgs)
            etapes = s.scalars(select(Journal).where(Journal.pme_id == pme_id).order_by(Journal.id.desc()).limit(40)).all()
            journal = "".join(f"<li>{e.etape} · {e.duree_ms} ms{(' · ERREUR ' + escape(e.erreur)) if e.erreur else ''}</li>" for e in etapes)
        corps = (
            f"<p><a href='/console'>← Retour</a></p><h1>{escape(pme.nom_commerce)}</h1><p class='sous'>{escape(pme.numero_whatsapp)} · {escape(pme.quartier or '')} {escape(pme.ville or '')}</p>"
            f'<div class="deux"><div><div class="chat">{bulles or "<div class=vide>Aucun message.</div>"}</div></div>'
            f'<div class="carte"><b>Journal du pipeline</b><ul class="journal" style="padding-left:16px">{journal or "<li>vide</li>"}</ul></div></div>'
        )
        return ui.page(pme.nom_commerce, corps)

    @app.post("/console/declencher/{quoi}")
    def declencher(quoi: str, _: str = Depends(console)) -> dict:
        """Déclenche à la main, pour la démo : `resume` (ignore l'heure) ou `rappels`."""
        if quoi == "resume":
            return {"envoyes": resume_du_soir.executer(fabrique, deps.canal, deps.horloge, 0)}
        if quoi == "rappels":
            return {"envoyes": rappels_fiscaux.executer(fabrique, deps.canal, deps.horloge)}
        raise HTTPException(status_code=404)

    @app.get("/console/simulateur", response_class=HTMLResponse)
    def simulateur(_: str = Depends(console)) -> str:
        with fabrique() as s:
            options = "".join(f'<option value="{p.id}">{escape(p.nom_commerce)}</option>' for p in s.scalars(select(Pme).order_by(Pme.id)).all())
        if not options:
            return ui.page("Simulateur", "<h1>Simulateur</h1><div class='carte vide'>Crée d'abord une PME.</div>", "simulateur")
        puces = "".join(f'<button type="button" data-t="{escape(t)}">{escape(t)}</button>' for t in ["j'ai vendu 3 paires à 5000", "j'ai fait combien aujourd'hui ?", "qui me doit ?", "tu peux faire quoi ?", "annule"])
        corps = (
            "<h1>Simulateur</h1><p class='sous'>Parle à Moki comme une PME, sans WhatsApp. Les actions sont réelles dans la base.</p>"
            '<div class="chat" id="chat"></div>'
            f'<form class="saisie" id="formulaire"><select id="pme">{options}</select><input id="texte" autocomplete="off" placeholder="Écris à Moki…" autofocus><button id="envoyer">Envoyer</button></form>'
            f'<div class="puces">{puces}</div><script>{ui.SCRIPT_SIMULATEUR}</script>'
        )
        return ui.page("Simulateur", corps, "simulateur")

    @app.post("/console/simuler")
    def simuler(entree: EntreeSimulation, _: str = Depends(console)) -> dict:
        with fabrique() as s:
            pme = s.get(Pme, entree.pme_id)
            if pme is None:
                raise HTTPException(status_code=404, detail="PME inconnue")
            numero = pme.numero_whatsapp
        compteur = f"sim.{secrets.token_hex(6)}"
        entrant = MessageEntrant(wamid=compteur, numero=numero, type="texte", heure_envoi=deps.horloge.maintenant(), texte=entree.texte[:2000])
        return {"reponses": services.traiter_entrant(fabrique, deps, entrant)}

    return app
