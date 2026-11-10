"""Canal réel : WhatsApp Cloud API (Meta Graph API)."""

from __future__ import annotations

from pathlib import Path

import httpx

from app.integrations.whatsapp.interface import ErreurCanal, MessageSortant


class CanalCloudApi:
    def __init__(self, jeton: str, id_numero: str, version: str = "v21.0", client: httpx.Client | None = None) -> None:
        if not jeton or not id_numero:
            raise ValueError("jeton et identifiant de numéro WhatsApp requis")
        self.base = f"https://graph.facebook.com/{version}"
        self.id_numero = id_numero
        self.client = client or httpx.Client(timeout=20.0)
        self.entetes = {"Authorization": f"Bearer {jeton}"}

    def envoyer(self, message: MessageSortant) -> str:
        if message.document:
            media_id = self._televerser(Path(message.document))
            charge = {
                "messaging_product": "whatsapp",
                "to": message.numero,
                "type": "document",
                "document": {"id": media_id, "filename": Path(message.document).name, **({"caption": message.texte} if message.texte else {})},
            }
        elif message.modele:
            charge = {
                "messaging_product": "whatsapp",
                "to": message.numero,
                "type": "template",
                "template": {
                    "name": message.modele,
                    "language": {"code": "fr"},
                    "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in message.parametres_modele]}] if message.parametres_modele else [],
                },
            }
        else:
            charge = {"messaging_product": "whatsapp", "to": message.numero, "type": "text", "text": {"body": message.texte or ""}}
        r = self.client.post(f"{self.base}/{self.id_numero}/messages", json=charge, headers=self.entetes)
        if r.status_code >= 400:
            raise ErreurCanal(f"envoi refusé ({r.status_code}) : {r.text[:300]}")
        donnees = r.json()
        return donnees["messages"][0]["id"]

    def telecharger_media(self, media_id: str) -> bytes:
        r = self.client.get(f"{self.base}/{media_id}", headers=self.entetes)
        if r.status_code >= 400:
            raise ErreurCanal(f"média introuvable ({r.status_code})")
        url = r.json()["url"]
        r2 = self.client.get(url, headers=self.entetes)
        if r2.status_code >= 400:
            raise ErreurCanal(f"téléchargement refusé ({r2.status_code})")
        return r2.content

    def _televerser(self, chemin: Path) -> str:
        with chemin.open("rb") as f:
            r = self.client.post(
                f"{self.base}/{self.id_numero}/media",
                headers=self.entetes,
                data={"messaging_product": "whatsapp", "type": "application/pdf"},
                files={"file": (chemin.name, f, "application/pdf")},
            )
        if r.status_code >= 400:
            raise ErreurCanal(f"téléversement refusé ({r.status_code}) : {r.text[:300]}")
        return r.json()["id"]
