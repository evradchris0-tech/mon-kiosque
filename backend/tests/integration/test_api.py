"""Webhook, idempotence, signature, console, résumé du soir."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.main import creer_app
from app.core.config import Parametres
from app.db.modeles import Job, Message, Vente
from app.workers import resume_du_soir
from tests.conftest import NUM_A

SECRET = "secret-app"


def charge(wamid: str, texte: str, numero: str = NUM_A) -> dict:
    return {"entry": [{"changes": [{"value": {"messages": [{"id": wamid, "from": numero, "timestamp": "1762765200", "type": "text", "text": {"body": texte}}]}}]}]}


def signer(corps: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), corps, hashlib.sha256).hexdigest()


def client_api(banc):
    p = Parametres(env="staging", whatsapp_secret_app=SECRET, whatsapp_jeton_verification="jeton", console_utilisateur="u", console_mot_de_passe="m")
    return TestClient(creer_app(p, banc.fabrique, banc.deps))


def poster(c, banc, wamid, texte):
    corps = json.dumps(charge(wamid, texte)).encode()
    return c.post("/webhooks/whatsapp", content=corps, headers={"x-hub-signature-256": signer(corps), "content-type": "application/json"})


def test_signature_invalide_refusee(banc):
    c = client_api(banc)
    r = c.post("/webhooks/whatsapp", content=b"{}", headers={"x-hub-signature-256": "sha256=faux"})
    assert r.status_code == 401


def test_verification_abonnement(banc):
    c = client_api(banc)
    assert c.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "jeton", "hub.challenge": "42"}).text == "42"
    assert c.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "42"}).status_code == 403


def test_webhook_rejoue_ne_cree_qu_une_vente(banc):
    c = client_api(banc)
    assert poster(c, banc, "wamid.A", "j'ai vendu 3 paires à 5000 cash").status_code == 200
    assert poster(c, banc, "wamid.A", "j'ai vendu 3 paires à 5000 cash").status_code == 200
    with banc.session() as s:
        assert s.scalar(select(func.count(Vente.id))) == 1
        assert s.scalar(select(func.count(Message.id)).where(Message.wamid == "wamid.A")) == 1
    assert any("C'est noté" in t for t in banc.canal.textes(NUM_A))


def test_console_protegee(banc):
    c = client_api(banc)
    assert c.get("/console").status_code == 401
    r = c.get("/console", auth=("u", "m"))
    assert r.status_code == 200 and "Chez Marie" in r.text


def test_resume_du_soir_une_seule_fois(banc):
    banc.envoyer("j'ai vendu 3 paires à 5000 cash")
    banc.canal.vider()
    banc.horloge.fixer(datetime(2026, 11, 10, 18, 30))  # 19h30 à Douala
    assert resume_du_soir.executer(banc.fabrique, banc.canal, banc.horloge) == 2  # deux PME de test
    assert resume_du_soir.executer(banc.fabrique, banc.canal, banc.horloge) == 0
    assert any("Résumé du soir" in t and "15" in t for t in banc.canal.textes(NUM_A))
    with banc.session() as s:
        assert s.scalar(select(func.count(Job.id))) == 2


def test_resume_pas_avant_19h(banc):
    banc.horloge.fixer(datetime(2026, 11, 10, 15, 0))  # 16h locale
    assert resume_du_soir.executer(banc.fabrique, banc.canal, banc.horloge) == 0
