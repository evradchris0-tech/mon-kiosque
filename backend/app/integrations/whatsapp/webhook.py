"""Lecture des webhooks WhatsApp Cloud API : signature, extraction des messages."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

from app.integrations.whatsapp.interface import MessageEntrant


def verifier_signature(secret_app: str, corps: bytes, entete: str | None) -> bool:
    """X-Hub-Signature-256: sha256=<hmac>. Sans secret configuré, on refuse (sauf dev)."""
    if not secret_app:
        return False
    if not entete or not entete.startswith("sha256="):
        return False
    attendu = hmac.new(secret_app.encode(), corps, hashlib.sha256).hexdigest()
    return hmac.compare_digest(attendu, entete[len("sha256="):])


def extraire_messages(charge: dict[str, Any]) -> list[MessageEntrant]:
    """Transforme la charge utile Meta en messages normalisés. Ignore les statuts."""
    messages: list[MessageEntrant] = []
    for entree in charge.get("entry", []):
        for changement in entree.get("changes", []):
            valeur = changement.get("value", {})
            for m in valeur.get("messages", []):
                genre = m.get("type")
                heure = datetime.fromtimestamp(int(m.get("timestamp", "0")), tz=UTC).replace(tzinfo=None)
                base = {"wamid": m["id"], "numero": m["from"], "heure_envoi": heure}
                if genre == "text":
                    messages.append(MessageEntrant(type="texte", texte=m["text"]["body"], **base))
                elif genre == "audio":
                    messages.append(MessageEntrant(type="audio", media_id=m["audio"]["id"], **base))
                elif genre == "button":
                    messages.append(MessageEntrant(type="texte", texte=m["button"]["text"], **base))
                elif genre == "interactive":
                    rep = m["interactive"].get("button_reply") or m["interactive"].get("list_reply") or {}
                    messages.append(MessageEntrant(type="texte", texte=rep.get("title", ""), **base))
                else:
                    messages.append(MessageEntrant(type="autre", **base))
    return messages
