"""Résumés par période, calculés dans le fuseau de la PME."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.horloge import Horloge, en_local, en_utc
from app.db.modeles import Pme
from app.domaine import paiements as dom_paiements
from app.moki.schemas import Periode, TypePeriode


def bornes(periode: Periode | None, horloge: Horloge, fuseau: str) -> tuple[datetime, datetime, str]:
    """(debut_utc, fin_utc, libellé) pour la période demandée."""
    tz = ZoneInfo(fuseau)
    maintenant_local = en_local(horloge.maintenant(), fuseau)
    aujourd_hui = maintenant_local.date()
    genre = periode.type if periode else TypePeriode.AUJOURD_HUI

    def jour(d: date) -> datetime:
        return datetime(d.year, d.month, d.day, tzinfo=tz)

    if genre == TypePeriode.HIER:
        d = aujourd_hui - timedelta(days=1)
        return en_utc(jour(d)), en_utc(jour(aujourd_hui)), "Hier"
    if genre == TypePeriode.SEMAINE:
        lundi = aujourd_hui - timedelta(days=aujourd_hui.weekday())
        return en_utc(jour(lundi)), en_utc(jour(aujourd_hui + timedelta(days=1))), "Cette semaine"
    if genre == TypePeriode.MOIS:
        premier = aujourd_hui.replace(day=1)
        return en_utc(jour(premier)), en_utc(jour(aujourd_hui + timedelta(days=1))), "Ce mois"
    if genre == TypePeriode.PERSONNALISEE and periode and periode.debut:
        fin = (periode.fin or periode.debut) + timedelta(days=1)
        libelle = f"Du {periode.debut.strftime('%d/%m')} au {(fin - timedelta(days=1)).strftime('%d/%m')}"
        return en_utc(jour(periode.debut)), en_utc(jour(fin)), libelle
    return en_utc(jour(aujourd_hui)), en_utc(jour(aujourd_hui + timedelta(days=1))), "Aujourd'hui"


def calculer(session: Session, pme: Pme, periode: Periode | None, horloge: Horloge) -> dict:
    from app.domaine import finances

    c = finances.chiffres_periode(session, pme, periode, horloge)
    return {
        "libelle": c["libelle"],
        "nb": c["nb"],
        "total": c["ventes"],
        "par_mode": c["par_mode"],
        "impayes": dom_paiements.total_impayes(session, pme),
        "charges": c["charges"],
        "benefice": c["benefice"],
    }


def total_du_jour(session: Session, pme: Pme, horloge: Horloge) -> int:
    debut, fin, _ = bornes(None, horloge, pme.fuseau)
    from app.domaine import finances

    return finances.chiffres(session, pme, debut, fin)["ventes"]
