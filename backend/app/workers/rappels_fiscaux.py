"""Rappels fiscaux (H2) : message 15 jours puis 3 jours avant chaque échéance, une seule fois."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.horloge import Horloge
from app.db.modeles import Job, Message, Pme
from app.domaine import finances, preferences
from app.integrations.whatsapp.interface import CanalMessages, MessageSortant
from app.moki import reponses

JOURS_RAPPEL = (15, 3)


def executer(fabrique: sessionmaker[Session], canal: CanalMessages, horloge: Horloge) -> int:
    envoyes = 0
    with fabrique() as s:
        for pme in s.scalars(select(Pme).where(Pme.statut == "actif")).all():
            if not preferences.actif(s, pme, "rappels_fiscaux"):
                continue
            for e in finances.echeances(horloge, pme.fuseau):
                if e["jours"] not in JOURS_RAPPEL:
                    continue
                cle = f"rappel_fiscal:{pme.id}:{e['date']}:{e['jours']}"
                if s.scalar(select(Job.id).where(Job.cle_idempotence == cle)) is not None:
                    continue
                s.add(Job(type="rappel_fiscal", charge={"pme_id": pme.id}, cle_idempotence=cle, etat="fait", cree_a=horloge.maintenant(), execute_a=horloge.maintenant()))
                s.commit()  # clé posée avant l'envoi : jamais de doublon
                try:
                    contenu = reponses.rappel_fiscal(e["libelle"], e["jours"], e["date"])
                    canal.envoyer(MessageSortant(numero=pme.numero_whatsapp, texte=contenu))  # hors fenêtre 24 h : message à modèle en réel
                    s.add(Message(pme_id=pme.id, numero=pme.numero_whatsapp, direction="sortant", type="notification", texte=contenu, heure_envoi=horloge.maintenant(), heure_reception=horloge.maintenant()))
                    s.commit()
                    envoyes += 1
                except Exception:  # noqa: BLE001
                    pass
    return envoyes
