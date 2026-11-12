"""Schémas du pipeline Moki.

`Interpretation` est la sortie structurée du modèle de langage (annexe A du plan complet).
Elle ne contient aucun total : les montants sont recalculés en code (règle D5).
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Intention(StrEnum):
    VENTE = "VENTE"
    FACTURE = "FACTURE"
    LIEN_PAIEMENT = "LIEN_PAIEMENT"
    RELANCE = "RELANCE"
    RESUME = "RESUME"
    QUI_DOIT = "QUI_DOIT"
    PRODUIT = "PRODUIT"
    CLIENT = "CLIENT"
    PAIEMENT_RECU = "PAIEMENT_RECU"
    ANNULER = "ANNULER"
    AIDE = "AIDE"
    HUMAIN = "HUMAIN"
    CONFIRMATION = "CONFIRMATION"
    AUTRE = "AUTRE"
    DEPENSE = "DEPENSE"
    CHANGER_NATURE = "CHANGER_NATURE"
    BILAN = "BILAN"
    DOSSIER_CREDIT = "DOSSIER_CREDIT"
    IMPOT = "IMPOT"
    ECHEANCES = "ECHEANCES"
    FACTURES = "FACTURES"


class ModePaiement(StrEnum):
    CASH = "cash"
    MOBILE_MONEY = "mobile_money"
    CREDIT = "credit"
    INCONNU = "inconnu"


class TypePeriode(StrEnum):
    AUJOURD_HUI = "aujourd_hui"
    HIER = "hier"
    SEMAINE = "semaine"
    MOIS = "mois"
    PERSONNALISEE = "personnalisee"


class TypeDepense(StrEnum):
    CHARGE = "charge"
    STOCK = "stock"


class Nature(StrEnum):
    PRO = "pro"
    PERSO = "perso"


class Decision(StrEnum):
    EXECUTER = "EXECUTER"
    DEMANDER_PRECISION = "DEMANDER_PRECISION"
    DEMANDER_CONFIRMATION = "DEMANDER_CONFIRMATION"
    CONFIRMATION_RENFORCEE = "CONFIRMATION_RENFORCEE"
    REFUSER = "REFUSER"


class Ligne(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produit: str | None = Field(default=None, description="Produit tel que dit par la PME")
    quantite: int | None = Field(default=None, description="Quantité, entier")
    prix_unitaire: int | None = Field(default=None, description="Prix unitaire en FCFA")
    produit_connu: bool | None = Field(
        default=None, description="Le produit correspond à un produit du catalogue fourni"
    )

    def complete(self) -> bool:
        return (
            self.quantite is not None
            and self.quantite > 0
            and self.prix_unitaire is not None
            and self.prix_unitaire > 0
        )

    def montant(self) -> int:
        if not self.complete():
            raise ValueError("ligne incomplète")
        assert self.quantite is not None and self.prix_unitaire is not None
        return self.quantite * self.prix_unitaire


class Frais(BaseModel):
    model_config = ConfigDict(extra="forbid")

    libelle: str
    montant: int


class ClientCite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom_cite: str | None = Field(default=None, description="Nom du client tel que cité")
    telephone: str | None = Field(default=None, description="Téléphone s'il est cité")


class Periode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TypePeriode = TypePeriode.AUJOURD_HUI
    debut: date | None = None
    fin: date | None = None


class HorsPerimetre(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raison: str | None = None


class DepenseCitee(BaseModel):
    model_config = ConfigDict(extra="forbid")

    libelle: str | None = Field(default=None, description="Pour quoi (loyer, électricité, salaire, transport, stock...)")
    montant: int | None = Field(default=None, description="Montant en FCFA")
    type: TypeDepense = Field(default=TypeDepense.CHARGE, description="charge = frais du commerce ; stock = achat de marchandise à revendre")
    nature: Nature = Field(default=Nature.PRO, description="pro par défaut ; perso si dépense personnelle ou retrait pour soi")


class Interpretation(BaseModel):
    """Ce que le modèle a compris. Jamais de total : il est recalculé en code."""

    model_config = ConfigDict(extra="forbid")

    intention: Intention
    confiance: float = Field(ge=0.0, le=1.0)
    lignes: list[Ligne] = Field(default_factory=list)
    frais: list[Frais] = Field(default_factory=list)
    client: ClientCite | None = None
    paiement: ModePaiement = ModePaiement.INCONNU
    periode: Periode | None = None
    reference_facture: str | None = None
    ambiguites: list[str] = Field(default_factory=list)
    question_a_poser: str | None = None
    hors_perimetre: HorsPerimetre | None = None
    depense: DepenseCitee | None = None
    action_produit: Literal["ajouter", "modifier", "supprimer"] = "ajouter"
    reponse_libre: str | None = Field(
        default=None,
        description="Texte libre, uniquement pour AIDE et AUTRE, jamais de montant",
    )

    def lignes_completes(self) -> bool:
        return bool(self.lignes) and all(ligne.complete() for ligne in self.lignes)

    def total_lignes(self) -> int:
        return sum(ligne.montant() for ligne in self.lignes)

    def total_frais(self) -> int:
        return sum(f.montant for f in self.frais)

    def total(self) -> int:
        """Total recalculé en code : somme des lignes + frais."""
        return self.total_lignes() + self.total_frais()

    def nom_client(self) -> str | None:
        if self.client and self.client.nom_cite:
            return self.client.nom_cite.strip() or None
        return None
