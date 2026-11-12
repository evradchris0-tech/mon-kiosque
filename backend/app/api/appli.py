"""API de l'appli mobile (démo) : connexion par numéro, chat, tableau, dossier, fichiers, QR code."""

from __future__ import annotations

import hashlib
import hmac
import io
import secrets
import socket
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from app import services
from app.core.config import Parametres
from app.db.modeles import Facture, Pme
from app.domaine import dossier as dom_dossier
from app.domaine import factures as dom_factures
from app.domaine import finances
from app.domaine import paiements as dom_paiements
from app.domaine import pme as dom_pme
from app.domaine.pme import pme_par_numero
from app.integrations.whatsapp.interface import MessageEntrant
from app.moki import pipeline
from app.moki.schemas import Periode, TypePeriode

STATIC = Path(__file__).resolve().parent.parent / "static"


class Connexion(BaseModel):
    numero: str


class Chat(BaseModel):
    texte: str


def ip_locale() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def url_appli(p: Parametres, request: Request | None = None) -> str:
    if p.url_publique:
        return p.url_publique.rstrip("/") + "/app"
    if request is not None:
        hote = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        if hote and not hote.startswith(("localhost", "127.")):
            proto = request.headers.get("x-forwarded-proto") or ("https" if ".vercel.app" in hote else request.url.scheme)
            return f"{proto}://{hote}/app"
    return f"http://{ip_locale()}:{p.port}/app"


def routeur(p: Parametres, fabrique: sessionmaker[Session], deps: pipeline.Dependances) -> APIRouter:
    r = APIRouter()
    secret = (p.secret_jeton or secrets.token_hex(16)).encode()

    def signer(numero: str) -> str:
        """Jeton sans état : valable sur toutes les instances (hébergement serverless)."""
        return f"{numero}." + hmac.new(secret, numero.encode(), hashlib.sha256).hexdigest()[:40]

    def verifier(jeton: str) -> str | None:
        numero, _, mac = jeton.partition(".")
        if not numero.isdigit():
            return None
        attendu = hmac.new(secret, numero.encode(), hashlib.sha256).hexdigest()[:40]
        return numero if hmac.compare_digest(mac, attendu) else None

    def numero_courant(authorization: str | None = Header(default=None), token: str | None = Query(default=None)) -> str:
        jeton = (authorization or "").removeprefix("Bearer ").strip() or (token or "")
        numero = verifier(jeton)
        if numero is None:
            raise HTTPException(status_code=401, detail="session invalide")
        return numero

    def jeton_courant(authorization: str | None = Header(default=None), token: str | None = Query(default=None)) -> str:
        return (authorization or "").removeprefix("Bearer ").strip() or (token or "")

    @r.get("/")
    def accueil() -> RedirectResponse:
        return RedirectResponse("/app")

    @r.get("/manifest.webmanifest")
    def manifeste() -> Response:
        return Response((STATIC / "manifest.webmanifest").read_text(encoding="utf-8"), media_type="application/manifest+json")

    @r.get("/sw.js")
    def service_worker() -> Response:
        return Response((STATIC / "sw.js").read_text(encoding="utf-8"), media_type="text/javascript", headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

    @r.get("/icons/{nom}")
    def icone(nom: str) -> FileResponse:
        if nom != Path(nom).name or not nom.endswith(".png") or not (STATIC / "icons" / nom).is_file():
            raise HTTPException(status_code=404)
        return FileResponse(STATIC / "icons" / nom, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

    @r.get("/app", response_class=HTMLResponse)
    def appli() -> HTMLResponse:
        return HTMLResponse((STATIC / "app.html").read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

    @r.post("/api/connexion")
    def connexion(c: Connexion) -> dict:
        if not p.acces_demo:
            raise HTTPException(status_code=403, detail="accès démo désactivé")
        numero = "".join(ch for ch in c.numero if ch.isdigit())
        if not (8 <= len(numero) <= 15):
            raise HTTPException(status_code=422, detail="numéro invalide")
        jeton = signer(numero)
        with fabrique() as s:
            pme = pme_par_numero(s, numero)
            infos = {"nom_commerce": pme.nom_commerce, "ville": pme.ville} if pme else None
            demo = bool(pme and pme.donnees_fictives)
        return {"token": jeton, "numero": numero, "pme": infos, "demo": demo}

    @r.post("/api/chat")
    def chat(c: Chat, numero: str = Depends(numero_courant), jeton: str = Depends(jeton_courant)) -> dict:
        texte = c.texte.strip()[:2000]
        if not texte:
            raise HTTPException(status_code=422, detail="message vide")
        entrant = MessageEntrant(wamid=f"web.{secrets.token_hex(8)}", numero=numero, type="texte", heure_envoi=deps.horloge.maintenant(), texte=texte)
        textes, documents = services.traiter_entrant_complet(fabrique, deps, entrant, repondre=False)
        with fabrique() as s:
            pme = pme_par_numero(s, numero)
            infos = {"nom_commerce": pme.nom_commerce, "ville": pme.ville} if pme else None
        docs = [{"nom": Path(d).name, "url": f"/api/fichier?nom={Path(d).name}&token={jeton}"} for d in documents]
        return {"reponses": textes, "documents": docs, "pme": infos}

    def _pme(s: Session, numero: str) -> Pme:
        pme = pme_par_numero(s, numero)
        if pme is None:
            raise HTTPException(status_code=404, detail="compte non inscrit : écris d'abord à Moki")
        return pme

    @r.get("/api/tableau")
    def tableau(numero: str = Depends(numero_courant)) -> dict:
        h = deps.horloge
        with fabrique() as s:
            pme = _pme(s, numero)
            from app.domaine import resumes as dom_resumes

            def periode(t: TypePeriode) -> dict:
                c = finances.chiffres_periode(s, pme, Periode(type=t), h)
                return {"ventes": c["ventes"], "nb": c["nb"], "charges": c["charges"], "benefice": c["benefice"]}

            mois = finances.chiffres_periode(s, pme, Periode(type=TypePeriode.MOIS), h)
            factures = []
            for f in dom_factures.ouvertes(s, pme) + [x for x in s.query(Facture).filter(Facture.pme_id == pme.id, Facture.statut == "payee").order_by(Facture.numero.desc()).limit(5)]:
                client = f.client_id
                from app.db.modeles import Client

                nom = s.get(Client, client).nom if client else "?"
                retard = dom_factures.jours_de_retard(f, h) if f.statut in dom_factures.STATUTS_OUVERTS else 0
                statut = "payee" if f.statut == "payee" else ("en_retard" if retard > 7 else "envoyee")
                factures.append({"numero": f.numero, "client": nom, "total": f.total, "statut": statut, "jours_retard": retard})
            factures.sort(key=lambda x: -x["numero"])
            impayes_liste = [{"client": n, "montant": m, "detail": d} for n, m, d in dom_paiements.impayes_par_client(s, pme, h)]
            ech = finances.prochaine_echeance(h, pme.fuseau)
            est = finances.impot_estime(s, pme, h)
            _ = dom_resumes
            return {
                "commerce": pme.nom_commerce,
                "demo": pme.donnees_fictives,
                "jour": periode(TypePeriode.AUJOURD_HUI),
                "semaine": periode(TypePeriode.SEMAINE),
                "mois": periode(TypePeriode.MOIS),
                "tresorerie": finances.tresorerie(s, pme),
                "benefice_mois": mois["benefice"],
                "retraits_perso_mois": mois["retraits"],
                "impayes": dom_paiements.total_impayes(s, pme),
                "serie_7j": finances.serie_7j(s, pme, h),
                "top_produits": finances.top_produits(s, pme, h),
                "impayes_liste": impayes_liste,
                "factures": factures,
                "echeance": ech,
                "impot": {"estimation": est["estimation"], "note": est["note"]},
                "historique_mois": finances.historique_mois(s, pme, h),
            }

    @r.get("/api/notifications")
    def notifications(apres: int | None = None, numero: str = Depends(numero_courant)) -> dict:
        """Messages envoyés par Moki sans demande (résumé de 19 h, rappels fiscaux). Sans `apres`, renvoie seulement le curseur."""
        from sqlalchemy import func, select

        from app.db.modeles import Message

        with fabrique() as s:
            pme = _pme(s, numero)
            dernier = s.scalar(select(func.max(Message.id)).where(Message.pme_id == pme.id)) or 0
            if apres is None:
                return {"notifications": [], "dernier": dernier}
            lignes = s.scalars(select(Message).where(Message.pme_id == pme.id, Message.type == "notification", Message.id > apres).order_by(Message.id)).all()
            return {"notifications": [{"id": m.id, "texte": m.texte} for m in lignes], "dernier": max([dernier, *[m.id for m in lignes]])}

    @r.get("/api/dossier")
    def dossier(numero: str = Depends(numero_courant), jeton: str = Depends(jeton_courant)) -> dict:
        with fabrique() as s:
            pme = _pme(s, numero)
            chemin, _ = dom_dossier.generer(s, pme, deps.horloge, p.dossier_factures)
        nom = Path(chemin).name
        return {"url": f"/api/fichier?nom={nom}&token={jeton}", "nom": nom}

    @r.get("/api/fichier")
    def fichier(nom: str, numero: str = Depends(numero_courant)) -> FileResponse:
        if nom != Path(nom).name or not nom.endswith(".pdf"):
            raise HTTPException(status_code=400)
        with fabrique() as s:
            pme = _pme(s, numero)
            chemin = Path(p.dossier_factures) / str(pme.id) / nom  # le dossier de la PME : jamais celui d'une autre
        if not chemin.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(chemin, media_type="application/pdf", filename=nom)

    @r.get("/qr.png")
    def qr_png(request: Request) -> Response:
        import qrcode

        img = qrcode.make(url_appli(p, request), box_size=12, border=2)
        tampon = io.BytesIO()
        img.save(tampon, format="PNG")
        return Response(tampon.getvalue(), media_type="image/png")

    @r.get("/qr", response_class=HTMLResponse)
    def qr_page(request: Request) -> str:
        url = url_appli(p, request)
        return (
            '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mon Kiosque · QR</title>'
            "<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:linear-gradient(135deg,#FF7900,#E65100);font-family:system-ui,sans-serif;color:#fff;text-align:center}"
            ".c{background:#fff;color:#1a1a1a;border-radius:28px;padding:32px 36px;box-shadow:0 20px 60px rgba(0,0,0,.25)}img{width:min(70vw,360px);display:block;margin:12px auto}"
            "h1{margin:0;font-size:28px}p{margin:6px 0;color:#6b6b6b}code{background:#f1f1f1;padding:4px 10px;border-radius:8px;color:#1a1a1a}</style></head><body><div class='c'>"
            "<h1>Mon Kiosque</h1><p>Le 3-en-1 de la PME camerounaise · Propulsé par Moki</p>"
            f"<img src='/qr.png' alt='QR code'><p>Scanne avec ton téléphone</p><code>{url}</code></div></body></html>"
        )

    _ = dom_pme
    return r
