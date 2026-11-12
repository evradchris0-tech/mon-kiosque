"""Interprètes sans réseau.

- `InterpreteScripte` : réponses fixées par les tests (message exact -> Interpretation).
- `InterpreteRegles` : petit analyseur à base de règles, suffisant pour le développement
  local et les démonstrations sans clé API. Il ne prétend pas couvrir le franglais.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from app.core.argent import lire_montant
from app.domaine.texte import normaliser
from app.integrations.llm.interface import (
    ContexteInterpretation,
    ErreurInterprete,
    ResultatInterpretation,
)
from app.moki.schemas import (
    ClientCite,
    DepenseCitee,
    Frais,
    Intention,
    Interpretation,
    Ligne,
    ModePaiement,
    Nature,
    Periode,
    TypeDepense,
    TypePeriode,
)


class InterpreteScripte:
    def __init__(
        self,
        reponses: dict[str, Interpretation] | None = None,
        par_defaut: Callable[[ContexteInterpretation, str], Interpretation] | None = None,
    ) -> None:
        self.reponses = dict(reponses or {})
        self.par_defaut = par_defaut
        self.appels: list[tuple[ContexteInterpretation, str]] = []
        self.panne = False

    def programmer(self, texte: str, interpretation: Interpretation) -> None:
        self.reponses[texte] = interpretation

    def interpreter(self, contexte: ContexteInterpretation, texte: str) -> ResultatInterpretation:
        self.appels.append((contexte, texte))
        if self.panne:
            raise ErreurInterprete("panne simulée du modèle")
        if texte in self.reponses:
            interp = self.reponses[texte]
        elif self.par_defaut is not None:
            interp = self.par_defaut(contexte, texte)
        else:
            interp = InterpreteRegles().interpreter(contexte, texte).interpretation
        return ResultatInterpretation(interpretation=interp, modele="scripte", cout_estime=0.0)


_MOTS_NOMBRE = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7,
    "huit": 8, "neuf": 9, "dix": 10, "douze": 12, "quinze": 15, "vingt": 20, "trente": 30,
    "cinquante": 50, "cent": 100, "mille": 1000,
}

_LIGNE = re.compile(
    r"(?P<q>\d+)\s+(?P<produit>[a-zà-ÿ' -]+?)\s+(?:à|a|de|x|\*)?\s*(?P<pu>\d[\d . ]*k?)\b",
    re.IGNORECASE,
)
_FRAIS = re.compile(r"(livraison|transport|emballage)\s+(\d[\d . ]*k?)", re.IGNORECASE)
_TEL = re.compile(r"((?:\+?237)?\s*6(?:\s*\d){8})")


def _nombres_en_chiffres(texte: str) -> str:
    """'trois paires à cinq mille francs' -> '3 paires à 5000 francs' (cas simples)."""
    mots = texte.split()
    sortie: list[str] = []
    i = 0
    while i < len(mots):
        m = normaliser(mots[i])
        if m in _MOTS_NOMBRE:
            valeur = _MOTS_NOMBRE[m]
            if i + 1 < len(mots) and normaliser(mots[i + 1]) == "mille":
                valeur *= 1000
                i += 1
            sortie.append(str(valeur))
        else:
            sortie.append(mots[i])
        i += 1
    return " ".join(sortie)


class InterpreteRegles:
    """Analyseur déterministe de secours. Couvre les formulations simples et courantes."""

    def interpreter(self, contexte: ContexteInterpretation, texte: str) -> ResultatInterpretation:
        return ResultatInterpretation(
            interpretation=self._analyser(contexte, texte), modele="regles", cout_estime=0.0
        )

    def _analyser(self, contexte: ContexteInterpretation, brut: str) -> Interpretation:
        texte = _nombres_en_chiffres(brut.strip())
        t = normaliser(texte)

        if contexte.etat_conversation == "ATTEND_PRECISION" and contexte.action_en_attente:
            fusion = self._fusionner(contexte, t)
            if fusion is not None:
                return fusion

        if re.search(r"\b(ignore|oublie) (tes|les) (regles|consignes|instructions)\b", t) or (
            "tous mes clients" in t or "tout le monde" in t
        ):
            return Interpretation(
                intention=Intention.AUTRE, confiance=0.95,
                hors_perimetre={"raison": "envoi de masse ou contournement des règles"},
            )
        if re.match(r"^(annule|annuler|je me suis trompe|je me suis trompee)\b", t):
            return Interpretation(intention=Intention.ANNULER, confiance=0.95)
        if re.match(r"^(oui|ok|non|d accord|vas y)\b", t):
            return Interpretation(intention=Intention.CONFIRMATION, confiance=0.9)
        if re.search(r"\b(humain|quelqu un|une personne|l equipe)\b", t) and re.search(r"\b(parler|contacter|appeler|veux|voudrais)\b", t):
            return Interpretation(intention=Intention.HUMAIN, confiance=0.9)
        if re.search(r"\b(aide|tu peux faire quoi|tu sais faire quoi|comment ca marche)\b", t):
            return Interpretation(intention=Intention.AIDE, confiance=0.9)
        if re.search(r"\b(mes factures|mes dernieres factures|etat (de mes |des )?factures|liste (de mes |des )?factures|factures? (?:sont )?(?:en retard|impayees))\b", t):
            return Interpretation(intention=Intention.FACTURES, confiance=0.95)
        if re.search(r"dossier (de |du )?credit|dossier bancaire|\bmon dossier\b", t):
            return Interpretation(intention=Intention.DOSSIER_CREDIT, confiance=0.95)
        if re.search(r"\b(echeances?|prochaine declaration|date limite)\b", t):
            return Interpretation(intention=Intention.ECHEANCES, confiance=0.9)
        if (re.search(r"\bigs\b", t) or re.search(r"\b(mon|mes|estimation|estime|combien)\b.{0,25}\bimpots?\b", t)) and not re.search(r"\b(comment|declarer|declaration|frauder|eviter|moins)\b", t):
            return Interpretation(intention=Intention.IMPOT, confiance=0.9)
        if re.search(r"\b(tresorerie|benefices?|argent disponible|en caisse|j ai gagne)\b", t):
            return Interpretation(intention=Intention.BILAN, confiance=0.9)
        m_nature = re.search(r"\bc est (perso|personnel|personnelle|pro|professionnel|professionnelle)\b", t)
        if m_nature:
            perso = m_nature.group(1).startswith("perso")
            return Interpretation(intention=Intention.CHANGER_NATURE, confiance=0.9, depense=DepenseCitee(nature=Nature.PERSO if perso else Nature.PRO))
        if re.search(r"\bj ?ai (paye|depense|verse|achete|retire)\b|\b(depense|retrait) (de|d)\b|\bj ai pris \d.*pour moi\b|\bje (retire|prends) \d", t):
            return self._depense(texte, t)
        m_sup = re.match(r"^\s*(?:supprime|supprimer|efface|enleve|enl\u00e8ve|retire)\s+(?:le produit\s+|la |le |les |l')?(.+?)(?:\s+du catalogue)?\s*$", texte, re.IGNORECASE)
        if m_sup:
            return Interpretation(intention=Intention.PRODUIT, confiance=0.9, action_produit="supprimer", lignes=[Ligne(produit=m_sup.group(1).strip(), quantite=None, prix_unitaire=None)])
        if re.match(r"^\s*(change|modifie|mets|met)\b.*\bprix\b", texte, re.IGNORECASE):
            m_mod = re.search(r"prix (?:de |des |du |d')?(.+?) (?:\u00e0|a|en) (\d[\d .\u202f]*k?)", texte, re.IGNORECASE)
            if m_mod and lire_montant(m_mod.group(2)):
                return Interpretation(intention=Intention.PRODUIT, confiance=0.9, action_produit="modifier", lignes=[Ligne(produit=m_mod.group(1).strip(), quantite=None, prix_unitaire=lire_montant(m_mod.group(2)))])
        if re.search(r"\b(impots?|fiscal|avocat|tribunal|medecin|maladie|sante)\b", t):
            return Interpretation(
                intention=Intention.AUTRE, confiance=0.9, hors_perimetre={"raison": "conseil hors périmètre"}
            )
        if re.search(r"\bqui (me )?doit\b", t) or "impayes" in t or "les dettes" in t:
            return Interpretation(intention=Intention.QUI_DOIT, confiance=0.9)
        if re.search(r"\b(combien|le total|les ventes|le bilan|le point|resume|chiffre)\b", t) and not re.search(r"\b(vendu|facture|relance|ajoute)\b", t):
            periode = TypePeriode.AUJOURD_HUI
            if "hier" in t:
                periode = TypePeriode.HIER
            elif "semaine" in t:
                periode = TypePeriode.SEMAINE
            elif "mois" in t:
                periode = TypePeriode.MOIS
            return Interpretation(intention=Intention.RESUME, confiance=0.9, periode=Periode(type=periode))
        if re.search(r"\brelance", t) or re.search(r"\bde venir payer\b", t) or re.search(r"\b(rappelle|rappeler) .*(payer|facture)", t):
            return self._relance(contexte, texte, t)
        if re.search(r"\b(a paye|a regle|m a paye|m a regle|ont paye|m a donne)\b", t):
            return self._paiement_recu(texte, t)
        if re.search(r"\b(lien|le lien) ", t) and re.search(r"\d", t):
            return self._lien(texte, t)
        if t.startswith("ajoute") or t.startswith("ajouter") or t.startswith("nouveau client") or t.startswith("nouveau produit"):
            return self._ajout(texte, t)
        if t.startswith("facture") or " facture " in f" {t} ":
            return self._facture(texte, t)
        if re.search(r"\b(vendu|a pris|ont pris|a achete|j ai fait une vente|vente de)\b", t):
            return self._vente(texte, t)
        return Interpretation(intention=Intention.AUTRE, confiance=0.3, question_a_poser=None)

    # ---- intentions ----

    def _depense(self, texte: str, t: str) -> Interpretation:
        m = re.search(r"(\d[\d .\u202f]*k?)", texte)
        montant = lire_montant(m.group(1)) if m else None
        perso = bool(re.search(r"\b(pour moi|perso|personnel|personnelle|maison|enfants?|ecole|famille|retire|retrait|prends)\b", t))
        stock = bool(re.search(r"\b(stock|marchandises?|approvisionnement|fournisseur|achete)\b", t)) and not perso
        reste = texte.replace(m.group(1), " ", 1) if m else texte
        reste = re.sub(r"(?i)\b(?:j'ai|jai|d'|l')\s*", " ", reste)
        reste = re.sub(r"(?i)\b(?:j|ai|je|paye|pay\u00e9|d\u00e9pens\u00e9|depense|d\u00e9pense|verse|vers\u00e9|achet\u00e9|achete|retir\u00e9|retire|retrait|prends|pris|de|du|des|pour|le|la|les|moi|francs?|fcfa|f|en|un|une)\b", " ", reste)
        libelle = re.sub(r"\s+", " ", re.sub(r"[^\w\u00c0-\u00ff' -]", " ", reste)).strip() or None
        return Interpretation(
            intention=Intention.DEPENSE,
            confiance=0.85 if montant else 0.5,
            depense=DepenseCitee(libelle=libelle, montant=montant, type=TypeDepense.STOCK if stock else TypeDepense.CHARGE, nature=Nature.PERSO if perso else Nature.PRO),
            question_a_poser=None if montant else "C'\u00e9tait pour quoi, et combien ?",
        )

    def _lignes(self, texte: str) -> tuple[list[Ligne], list[str]]:
        lignes: list[Ligne] = []
        ambiguites: list[str] = []
        texte_sans_frais = _FRAIS.sub(" ", texte)
        for m in _LIGNE.finditer(texte_sans_frais):
            q = int(m.group("q"))
            produit = m.group("produit").strip(" ,")
            produit = re.sub(r"^(de|des|du|d')\s+", "", produit).strip()
            pu = lire_montant(m.group("pu"))
            if pu is None:
                continue
            if produit.lower() in ("pr", "pour") or m.group("pu").lower().endswith("k") and q > 1 and "chacun" not in texte.lower() and "chaque" not in texte.lower() and " a " not in f" {normaliser(m.group(0))} ":
                ambiguites.append(f"{m.group('pu')} : unitaire ou total ?")
                lignes.append(Ligne(produit=None if produit.lower() in ("pr", "pour") else produit, quantite=q, prix_unitaire=None))
                continue
            lignes.append(Ligne(produit=produit, quantite=q, prix_unitaire=pu))
        return lignes, ambiguites

    def _client(self, texte: str) -> ClientCite | None:
        m = re.search(
            r"\b(Mme|Madame|M\.|Monsieur|Mr)\s+([A-ZÀ-Ý][\wà-ÿ-]*)", texte
        )
        if m:
            return ClientCite(nom_cite=f"{m.group(1)} {m.group(2)}")
        m = re.search(r"\b(?:pour|à|a|de)\s+((?:le |la |l')?[A-ZÀ-Ý][\wà-ÿ-]+(?:\s+[A-ZÀ-Ý][\wà-ÿ-]+)*)", texte)
        if m:
            return ClientCite(nom_cite=m.group(1))
        m = re.match(r"^\s*([A-ZÀ-Ý][\wà-ÿ-]+(?:\s+[A-ZÀ-Ý][\wà-ÿ-]+)*)\s+(?:a|m'a|ont)\b", texte)
        if m and m.group(1).lower() not in ("facture", "relance", "ajoute"):
            return ClientCite(nom_cite=m.group(1))
        return None

    def _vente(self, texte: str, t: str) -> Interpretation:
        lignes, ambiguites = self._lignes(texte)
        paiement = ModePaiement.INCONNU
        if re.search(r"\b(cash|liquide|especes)\b", t):
            paiement = ModePaiement.CASH
        elif re.search(r"\b(om|orange money|momo|mobile money|mtn)\b", t):
            paiement = ModePaiement.MOBILE_MONEY
        elif re.search(r"\b(credit|paie demain|paiera|doit encore|pas encore paye|a credit)\b", t):
            paiement = ModePaiement.CREDIT
        question = None
        if ambiguites:
            question = "C'est le prix de chacune ou le total ?"
        elif not lignes:
            question = "Qu'est-ce que tu as vendu, combien, et à quel prix ?"
        return Interpretation(
            intention=Intention.VENTE,
            confiance=0.85 if lignes else 0.5,
            lignes=lignes,
            client=self._client(texte),
            paiement=paiement,
            ambiguites=ambiguites,
            question_a_poser=question,
        )

    def _facture(self, texte: str, t: str) -> Interpretation:
        lignes, ambiguites = self._lignes(texte)
        frais = [Frais(libelle=m.group(1).lower(), montant=lire_montant(m.group(2)) or 0) for m in _FRAIS.finditer(texte)]
        if not lignes:
            m = re.search(r"facture\s+(?:de\s+)?(\d[\d . ]*k?)", texte, re.IGNORECASE)
            montant = lire_montant(m.group(1)) if m else None
            if montant:
                lignes = [Ligne(produit=None, quantite=1, prix_unitaire=montant)]
        return Interpretation(
            intention=Intention.FACTURE,
            confiance=0.85 if lignes else 0.5,
            lignes=lignes,
            frais=frais,
            client=self._client(texte),
            ambiguites=ambiguites,
            question_a_poser="Pour quel client, et quelles lignes ?" if not lignes else None,
        )

    def _relance(self, contexte: ContexteInterpretation, texte: str, t: str) -> Interpretation:
        client = self._client(texte)
        if client is None:
            m = re.search(r"relance\s+(.+?)(?:\s+pour\b|$)", texte, re.IGNORECASE)
            if m:
                client = ClientCite(nom_cite=m.group(1).strip(" ,."))
        ref = re.search(r"facture\s*(?:n[°o]?\s*)?(\d{1,4})", t)
        return Interpretation(
            intention=Intention.RELANCE,
            confiance=0.85 if client else 0.5,
            client=client,
            reference_facture=ref.group(1) if ref else None,
            question_a_poser=None if client else "Qui veux-tu relancer ?",
        )

    def _paiement_recu(self, texte: str, t: str) -> Interpretation:
        client = self._client(texte)
        montant = None
        m = re.search(r"(\d[\d . ]*k?)\s*(?:f|fcfa|francs)?\b", texte)
        if m:
            montant = lire_montant(m.group(1))
        ref = re.search(r"facture\s*(?:n[°o]?\s*)?(\d{1,4})", t)
        return Interpretation(
            intention=Intention.PAIEMENT_RECU,
            confiance=0.85 if client else 0.5,
            client=client,
            lignes=[Ligne(produit=None, quantite=1, prix_unitaire=montant)] if montant else [],
            reference_facture=ref.group(1) if ref else None,
        )

    def _lien(self, texte: str, t: str) -> Interpretation:
        m = re.search(r"(\d[\d . ]*k?)", texte)
        montant = lire_montant(m.group(1)) if m else None
        return Interpretation(
            intention=Intention.LIEN_PAIEMENT,
            confiance=0.85 if montant else 0.5,
            lignes=[Ligne(produit=None, quantite=1, prix_unitaire=montant)] if montant else [],
            client=self._client(texte),
        )

    def _ajout(self, texte: str, t: str) -> Interpretation:
        tel = _TEL.search(texte)
        reste = re.sub(r"^(ajoute[rz]?|nouveau client|nouveau produit)\s+", "", texte, flags=re.IGNORECASE).strip()
        if tel:
            nom = reste.replace(tel.group(1), "").strip(" ,:")
            return Interpretation(
                intention=Intention.CLIENT, confiance=0.9,
                client=ClientCite(nom_cite=nom, telephone=tel.group(1)),
            )
        m = re.match(r"^(.*?)[\s:]+(?:à|a)?\s*(\d[\d . ]*k?)\s*(?:f|fcfa)?$", reste, re.IGNORECASE)
        if m and lire_montant(m.group(2)):
            return Interpretation(
                intention=Intention.PRODUIT, confiance=0.9,
                lignes=[Ligne(produit=m.group(1).strip(), quantite=None, prix_unitaire=lire_montant(m.group(2)))],
            )
        if re.match(r"^(Mme|Madame|M\.|Monsieur)\b", reste):
            return Interpretation(intention=Intention.CLIENT, confiance=0.8, client=ClientCite(nom_cite=reste))
        return Interpretation(intention=Intention.PRODUIT, confiance=0.4, question_a_poser="C'est un produit (avec son prix) ou un client (avec son numéro) ?")

    def _fusionner(self, contexte: ContexteInterpretation, t: str) -> Interpretation | None:
        """Complète l'interprétation en attente avec une réponse courte (mode de paiement, choix)."""
        attente = contexte.action_en_attente or {}
        base = attente.get("interpretation")
        if not base:
            return None
        interp = Interpretation.model_validate(base)
        if re.search(r"\b(cash|liquide|especes)\b", t):
            interp.paiement = ModePaiement.CASH
            return interp
        if re.search(r"\b(om|orange money|momo|mobile money|mtn)\b", t):
            interp.paiement = ModePaiement.MOBILE_MONEY
            return interp
        if re.search(r"\b(credit|plus tard|demain|pas encore)\b", t):
            interp.paiement = ModePaiement.CREDIT
            return interp
        if interp.ambiguites and interp.lignes:
            montant = lire_montant(t) if lire_montant(t) is not None else None
            if "chacun" in t or "chaque" in t or "unitaire" in t:
                for ligne in interp.lignes:
                    if ligne.prix_unitaire is None and montant is None:
                        m = re.search(r"(\d[\d . ]*k?)", attente.get("texte_initial", ""))
                        montant = lire_montant(m.group(1)) if m else None
                    if ligne.prix_unitaire is None and montant is not None:
                        ligne.prix_unitaire = montant
                interp.ambiguites = []
                interp.question_a_poser = None
                return interp
            if "total" in t or "en tout" in t:
                for ligne in interp.lignes:
                    if ligne.prix_unitaire is None:
                        m = re.search(r"(\d[\d . ]*k?)", attente.get("texte_initial", ""))
                        total = lire_montant(m.group(1)) if m else None
                        if total is not None and ligne.quantite:
                            ligne.prix_unitaire = total // ligne.quantite
                interp.ambiguites = []
                interp.question_a_poser = None
                return interp
        for nom in contexte.clients:
            if normaliser(nom.split(" (")[0]) in t or t in normaliser(nom):
                interp.client = ClientCite(nom_cite=nom.split(" (")[0])
                interp.ambiguites = []
                return interp
        return None
