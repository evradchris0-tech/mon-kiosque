"""API : webhook WhatsApp, console interne, santé."""

from __future__ import annotations

import json
import secrets
from html import escape

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import services
from app.core.config import Parametres, parametres
from app.db.base import Base, creer_moteur, fabrique_sessions
from app.db.modeles import CasAVerifier, Journal, Message, Pme, Vente
from app.integrations.whatsapp import webhook as wh
from app.moki import pipeline


def creer_app(p: Parametres | None = None, fabrique: sessionmaker[Session] | None = None, deps: pipeline.Dependances | None = None) -> FastAPI:
    p = p or parametres()
    if fabrique is None:
        moteur = creer_moteur(p.database_url)
        Base.metadata.create_all(moteur)  # en prod : migrations Alembic
        fabrique = fabrique_sessions(moteur)
    deps = deps or services.construire_dependances(p)
    app = FastAPI(title="Moki", version="0.1.0")
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
            pmes = s.scalars(select(Pme).order_by(Pme.id)).all()
            lignes = ""
            for pme in pmes:
                nb = s.scalar(select(func.count(Vente.id)).where(Vente.pme_id == pme.id, Vente.statut == "active"))
                lignes += f"<tr><td>{pme.id}</td><td>{escape(pme.nom_commerce)}</td><td>{escape(pme.numero_whatsapp)}</td><td>{nb}</td><td><a href='/console/pme/{pme.id}'>conversations</a></td></tr>"
            cas = s.scalars(select(CasAVerifier).where(CasAVerifier.traite_a.is_(None)).order_by(CasAVerifier.id.desc()).limit(50)).all()
            liste = "".join(f"<li>#{c.id} {escape(c.motif)} (pme {c.pme_id}) : {escape(str((c.details or {}).get('texte', '')))}</li>" for c in cas)
        return f"<h1>Moki · console</h1><h2>PME</h2><table border=1 cellpadding=6><tr><th>id</th><th>commerce</th><th>numéro</th><th>ventes</th><th></th></tr>{lignes}</table><h2>À vérifier</h2><ul>{liste or '<li>rien</li>'}</ul>"

    @app.get("/console/pme/{pme_id}", response_class=HTMLResponse)
    def conversations(pme_id: int, _: str = Depends(console)) -> str:
        with fabrique() as s:
            pme = s.get(Pme, pme_id)
            if pme is None:
                raise HTTPException(status_code=404)
            msgs = s.scalars(select(Message).where(Message.pme_id == pme_id).order_by(Message.id.desc()).limit(100)).all()
            lignes = "".join(f"<tr><td>{m.heure_reception:%d/%m %H:%M}</td><td>{m.direction}</td><td>{escape(m.texte or m.transcription or '')}</td></tr>" for m in msgs)
            etapes = s.scalars(select(Journal).where(Journal.pme_id == pme_id).order_by(Journal.id.desc()).limit(30)).all()
            j = "".join(f"<li>{e.etape} {e.duree_ms} ms {escape(e.erreur or '')}</li>" for e in etapes)
        return f"<h1>{escape(pme.nom_commerce)}</h1><table border=1 cellpadding=4>{lignes}</table><h3>Journal</h3><ul>{j}</ul>"

    return app
