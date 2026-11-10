"""Simulateur en terminal : parle à Moki comme une PME, sans WhatsApp ni clé API.

Usage : python simuler.py            (interprète à règles, base mémoire)
        MOKI_INTERPRETE=claude python simuler.py   (avec ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import sys
import tempfile

from app.core.config import Parametres
from app.core.horloge import HorlogeSysteme
from app.db.base import Base, creer_moteur, fabrique_sessions
from app.domaine import pme as dom_pme
from app.integrations.whatsapp.interface import MessageEntrant
from app.services import construire_dependances, traiter_entrant

NUMERO = "237677000001"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = Parametres(database_url="sqlite+pysqlite:///:memory:", dossier_factures=tempfile.mkdtemp(prefix="factures_"))
    moteur = creer_moteur(p.database_url)
    Base.metadata.create_all(moteur)
    fabrique = fabrique_sessions(moteur)
    horloge = HorlogeSysteme()
    deps = construire_dependances(p, horloge)
    with fabrique() as s:
        dom_pme.creer_pme(s, horloge, nom_commerce="Chez Marie", numero_whatsapp=NUMERO, quartier="Essos", ville="Yaoundé")
        s.commit()
    print("Moki (simulateur). Écris comme sur WhatsApp ; Ctrl+C pour quitter.\n")
    n = 0
    while True:
        try:
            texte = input("PME  > ")
        except (EOFError, KeyboardInterrupt):
            break
        n += 1
        entrant = MessageEntrant(wamid=f"sim.{n}", numero=NUMERO, type="texte", heure_envoi=horloge.maintenant(), texte=texte)
        for rep in traiter_entrant(fabrique, deps, entrant):
            print("Moki > " + rep.replace("\n", "\n       ") + "\n")


if __name__ == "__main__":
    main()
