"""Résumé de fin de journée (19 h locale), idempotent par PME et par jour."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.horloge import Horloge, en_local
from app.db.modeles import Job, Pme
from app.domaine import resumes as dom_resumes
from app.integrations.whatsapp.interface import CanalMessages, MessageSortant
from app.moki import reponses


def executer(fabrique: sessionmaker[Session], canal: CanalMessages, horloge: Horloge, heure: int = 19) -> int:
    """Envoie le résumé aux PME dont l'heure locale a dépassé `heure` et qui n'ont pas encore le leur. Renvoie le nombre envoyé."""
    envoyes = 0
    with fabrique() as s:
        for pme in s.scalars(select(Pme).where(Pme.statut == "actif")).all():
            local = en_local(horloge.maintenant(), pme.fuseau)
            if local.hour < heure:
                continue
            cle = f"resume:{pme.id}:{local.date().isoformat()}"
            if s.scalar(select(Job.id).where(Job.cle_idempotence == cle)) is not None:
                continue
            r = dom_resumes.calculer(s, pme, None, horloge)
            texte = "Résumé du soir. " + reponses.resume(r["libelle"], r["nb"], r["total"], r["par_mode"], r["impayes"], r["charges"], r["benefice"])
            s.add(Job(type="resume_du_soir", charge={"pme_id": pme.id}, cle_idempotence=cle, etat="fait", cree_a=horloge.maintenant(), execute_a=horloge.maintenant()))
            s.commit()  # la clé est posée avant l'envoi : pas de doublon en cas de relance du worker
            try:
                canal.envoyer(MessageSortant(numero=pme.numero_whatsapp, texte=texte))  # hors fenêtre 24 h : message à modèle en réel
                envoyes += 1
            except Exception:  # noqa: BLE001
                pass
    return envoyes
