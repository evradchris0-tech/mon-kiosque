"""Paramètres de l'application, lus dans l'environnement (préfixe MOKI_)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Parametres(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MOKI_", env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "sqlite+pysqlite:///./moki_dev.db"

    # Modèle de langage
    modele: str = "claude-opus-5-5"
    effort: str = "low"
    interprete: str = "factice"  # factice | claude | gemini
    gemini_cle: str = ""
    modele_gemini: str = "gemini-flash-lite-latest"

    # WhatsApp Cloud API
    whatsapp_jeton: str = ""
    whatsapp_id_numero: str = ""
    whatsapp_jeton_verification: str = "a-definir"
    whatsapp_secret_app: str = ""
    canal: str = "factice"  # factice | cloud_api

    # Console interne
    console_utilisateur: str = "admin"
    console_mot_de_passe: str = "changer-ce-mot-de-passe"

    # Métier
    fuseau_defaut: str = "Africa/Douala"
    heure_resume: int = 19
    seuil_confirmation_renforcee: int = 50_000
    dossier_factures: str = "factures"


@lru_cache
def parametres() -> Parametres:
    return Parametres()
