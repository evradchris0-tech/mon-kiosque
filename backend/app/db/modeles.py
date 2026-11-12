"""Modèle de données (voir docs/02-plan-complet.md §2.6).

Conventions : montants en entiers FCFA ; dates UTC naïves ; chaque table métier porte
`pme_id` et toute requête est filtrée dessus.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Pme(Base):
    __tablename__ = "pme"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom_commerce: Mapped[str] = mapped_column(String(120))
    nom_gerante: Mapped[str | None] = mapped_column(String(120))
    numero_whatsapp: Mapped[str] = mapped_column(String(20), unique=True)
    secteur: Mapped[str | None] = mapped_column(String(40))
    ville: Mapped[str | None] = mapped_column(String(60))
    quartier: Mapped[str | None] = mapped_column(String(60))
    fuseau: Mapped[str] = mapped_column(String(40), default="Africa/Douala")
    seuil_confirmation_renforcee: Mapped[int] = mapped_column(Integer, default=50_000)
    mode_relance: Mapped[str] = mapped_column(String(20), default="transfert")
    statut: Mapped[str] = mapped_column(String(20), default="actif")
    statut_abonnement: Mapped[str] = mapped_column(String(20), default="pilote")
    consentement_corpus: Mapped[bool] = mapped_column(Boolean, default=False)
    consentement_corpus_date: Mapped[datetime | None] = mapped_column(DateTime)
    donnees_fictives: Mapped[bool] = mapped_column(Boolean, default=False)
    date_inscription: Mapped[datetime] = mapped_column(DateTime)

    numeros: Mapped[list[NumeroAutorise]] = relationship(back_populates="pme")


class NumeroAutorise(Base):
    __tablename__ = "numeros_autorises"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True)
    role: Mapped[str] = mapped_column(String(20), default="gerante")
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    pme: Mapped[Pme] = relationship(back_populates="numeros")


class Produit(Base):
    __tablename__ = "produits"
    __table_args__ = (UniqueConstraint("pme_id", "nom", name="uq_produit_pme_nom"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    nom: Mapped[str] = mapped_column(String(120))
    prix: Mapped[int] = mapped_column(Integer)
    unite: Mapped[str | None] = mapped_column(String(30))
    alias: Mapped[list[str]] = mapped_column(JSON, default=list)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    nom: Mapped[str] = mapped_column(String(120))
    telephone: Mapped[str | None] = mapped_column(String(20))
    quartier: Mapped[str | None] = mapped_column(String(60))
    alias: Mapped[list[str]] = mapped_column(JSON, default=list)
    dernier_achat: Mapped[datetime | None] = mapped_column(DateTime)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Vente(Base):
    __tablename__ = "ventes"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    heure_envoi: Mapped[datetime] = mapped_column(DateTime, index=True)
    heure_reception: Mapped[datetime] = mapped_column(DateTime)
    lignes: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    total: Mapped[int] = mapped_column(Integer)
    parts_paiement: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    client_nom_cite: Mapped[str | None] = mapped_column(String(120))
    credit_restant: Mapped[int] = mapped_column(Integer, default=0)
    statut: Mapped[str] = mapped_column(String(20), default="active")
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))


class Facture(Base):
    __tablename__ = "factures"
    __table_args__ = (UniqueConstraint("pme_id", "numero", name="uq_facture_pme_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    lignes: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    frais: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    total: Mapped[int] = mapped_column(Integer)
    echeance: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[str] = mapped_column(String(20), default="envoyee")
    pdf_chemin: Mapped[str | None] = mapped_column(String(255))
    creee_a: Mapped[datetime] = mapped_column(DateTime)
    payee_a: Mapped[datetime | None] = mapped_column(DateTime)
    confirmation_id: Mapped[int | None] = mapped_column(ForeignKey("confirmations.id"))


class Paiement(Base):
    __tablename__ = "paiements"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    facture_id: Mapped[int | None] = mapped_column(ForeignKey("factures.id"))
    vente_id: Mapped[int | None] = mapped_column(ForeignKey("ventes.id"))
    montant: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default="declare")
    operateur: Mapped[str | None] = mapped_column(String(30))
    reference_externe: Mapped[str | None] = mapped_column(String(120), unique=True)
    brut: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    recu_a: Mapped[datetime] = mapped_column(DateTime)
    statut: Mapped[str] = mapped_column(String(20), default="confirme")


class Relance(Base):
    __tablename__ = "relances"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    facture_id: Mapped[int] = mapped_column(ForeignKey("factures.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    mode: Mapped[str] = mapped_column(String(20))
    texte: Mapped[str] = mapped_column(Text)
    confirmation_id: Mapped[int] = mapped_column(ForeignKey("confirmations.id"))
    envoyee_a: Mapped[datetime] = mapped_column(DateTime)
    resultat: Mapped[str | None] = mapped_column(String(40))


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), unique=True)
    etat: Mapped[str] = mapped_column(String(40), default="LIBRE")
    action_en_attente: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    question_en_attente: Mapped[str | None] = mapped_column(Text)
    mot_confirmation: Mapped[str | None] = mapped_column(String(20))
    confirmation_id: Mapped[int | None] = mapped_column(ForeignKey("confirmations.id"))
    expire_a: Mapped[datetime | None] = mapped_column(DateTime)
    mise_a_jour: Mapped[datetime] = mapped_column(DateTime)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int | None] = mapped_column(ForeignKey("pme.id"), index=True)
    numero: Mapped[str] = mapped_column(String(20))
    direction: Mapped[str] = mapped_column(String(10))  # entrant | sortant
    wamid: Mapped[str | None] = mapped_column(String(120), unique=True)
    type: Mapped[str] = mapped_column(String(20), default="texte")
    texte: Mapped[str | None] = mapped_column(Text)
    media_id: Mapped[str | None] = mapped_column(String(120))
    transcription: Mapped[str | None] = mapped_column(Text)
    confiance_stt: Mapped[float | None] = mapped_column(Float)
    heure_envoi: Mapped[datetime] = mapped_column(DateTime)
    heure_reception: Mapped[datetime] = mapped_column(DateTime)


class Confirmation(Base):
    __tablename__ = "confirmations"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    action: Mapped[dict[str, Any]] = mapped_column(JSON)
    mode: Mapped[str] = mapped_column(String(20), default="simple")
    demandee_a: Mapped[datetime] = mapped_column(DateTime)
    confirmee_a: Mapped[datetime | None] = mapped_column(DateTime)
    par_numero: Mapped[str | None] = mapped_column(String(20))
    statut: Mapped[str] = mapped_column(String(20), default="en_attente")


class Journal(Base):
    __tablename__ = "journal"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int | None] = mapped_column(ForeignKey("pme.id"), index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"), index=True)
    etape: Mapped[str] = mapped_column(String(30))
    entree: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    sortie: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    duree_ms: Mapped[int] = mapped_column(Integer, default=0)
    cout_estime: Mapped[float | None] = mapped_column(Float)
    erreur: Mapped[str | None] = mapped_column(Text)
    cree_a: Mapped[datetime] = mapped_column(DateTime)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(40))
    charge: Mapped[dict[str, Any]] = mapped_column(JSON)
    cle_idempotence: Mapped[str] = mapped_column(String(160), unique=True)
    etat: Mapped[str] = mapped_column(String(20), default="en_attente")
    tentatives: Mapped[int] = mapped_column(Integer, default=0)
    cree_a: Mapped[datetime] = mapped_column(DateTime)
    execute_a: Mapped[datetime | None] = mapped_column(DateTime)
    erreur: Mapped[str | None] = mapped_column(Text)


class CasAVerifier(Base):
    __tablename__ = "cas_a_verifier"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int | None] = mapped_column(ForeignKey("pme.id"), index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    motif: Mapped[str] = mapped_column(String(60))
    gravite: Mapped[str] = mapped_column(String(10), default="normale")
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    traite_par: Mapped[str | None] = mapped_column(String(60))
    correction: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    cree_a: Mapped[datetime] = mapped_column(DateTime)
    traite_a: Mapped[datetime | None] = mapped_column(DateTime)


class Action(Base):
    """Trace des actions annulables (fenêtre de 10 minutes)."""

    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    type: Mapped[str] = mapped_column(String(30))
    cible_id: Mapped[int] = mapped_column(Integer)
    resume: Mapped[str] = mapped_column(String(200))
    creee_a: Mapped[datetime] = mapped_column(DateTime)
    annulable_jusqua: Mapped[datetime | None] = mapped_column(DateTime)
    annulee: Mapped[bool] = mapped_column(Boolean, default=False)


class Depense(Base):
    __tablename__ = "depenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    pme_id: Mapped[int] = mapped_column(ForeignKey("pme.id"), index=True)
    libelle: Mapped[str] = mapped_column(String(120))
    montant: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20), default="charge")  # charge | stock | retrait_perso
    nature: Mapped[str] = mapped_column(String(10), default="pro")  # pro | perso
    heure_envoi: Mapped[datetime] = mapped_column(DateTime, index=True)
    heure_reception: Mapped[datetime] = mapped_column(DateTime)
    statut: Mapped[str] = mapped_column(String(20), default="active")
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))


class Inscription(Base):
    __tablename__ = "inscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True)
    etape: Mapped[str] = mapped_column(String(20), default="nom")
    nom_commerce: Mapped[str | None] = mapped_column(String(120))
    ville: Mapped[str | None] = mapped_column(String(60))
    secteur: Mapped[str | None] = mapped_column(String(60))
    cree_a: Mapped[datetime] = mapped_column(DateTime)


Index("ix_journal_pme_cree", Journal.pme_id, Journal.cree_a)
Index("ix_ventes_pme_heure", Vente.pme_id, Vente.heure_envoi)
