"""Gabarits de réponse de Moki.

Tout message qui contient un montant vient d'ici, jamais du modèle de langage.
Ton : court, direct, tutoiement, français simple.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.argent import format_fcfa

LIBELLES_MODE = {
    "facture": "en factures",
    "cash": "en cash",
    "mobile_money": "par mobile money",
    "credit": "à crédit",
}


def recap_lignes(lignes: Sequence[dict], frais: Sequence[dict] = ()) -> str:
    parts: list[str] = []
    for ligne in lignes:
        produit = ligne.get("produit") or "article"
        q = int(ligne["quantite"])
        pu = int(ligne["prix_unitaire"])
        parts.append(f"{q} {produit} × {format_fcfa(pu)} = {format_fcfa(q * pu)}")
    for f in frais:
        parts.append(f"{f['libelle']} = {format_fcfa(int(f['montant']))}")
    return "\n".join(parts)


def total_ligne(total: int) -> str:
    return f"Total : {format_fcfa(total)}"


def demande_mode_paiement(recap: str, total: int) -> str:
    return f"Compris :\n{recap}\n{total_ligne(total)}\nC'est payé en cash ou par mobile money ?"


def vente_notee(total: int, mode: str, total_jour: int) -> str:
    return (
        f"C'est noté : {format_fcfa(total)} {LIBELLES_MODE.get(mode, '')}.".replace("  ", " ")
        + f" Total d'aujourd'hui : {format_fcfa(total_jour)}."
        + " Dis « annuler » si tu t'es trompée."
    )


def vente_credit_notee(total: int, client: str, reste_client: int) -> str:
    return (
        f"C'est noté : {format_fcfa(total)} à crédit pour {client}. "
        f"{client} te doit maintenant {format_fcfa(reste_client)} en tout. "
        "Dis « annuler » si tu t'es trompée."
    )


def client_inconnu_propose(nom: str) -> str:
    return (
        f"Je ne connais pas encore {nom}. Pour l'ajouter à ton carnet, dis par exemple "
        f"« ajoute {nom} 6XX XX XX XX »."
    )


def client_ambigu(nom: str, candidats: Sequence[str]) -> str:
    n = len(candidats)
    liste = " et ".join([", ".join(candidats[:-1]), candidats[-1]]) if n > 1 else candidats[0]
    return f"J'ai {n} {nom} : {liste}. C'est laquelle ?"


def doublon_possible(recap: str, total: int) -> str:
    return (
        "Tu viens déjà de noter une vente identique il y a quelques minutes :\n"
        f"{recap}\n{total_ligne(total)}\nJe l'enregistre quand même ?"
    )


def montant_inhabituel(total: int, moyenne: int) -> str:
    return (
        f"{format_fcfa(total)}, c'est bien plus que d'habitude "
        f"(en moyenne {format_fcfa(moyenne)} par vente). Je confirme ce montant ?"
    )


def montant_eleve(total: int) -> str:
    return f"{format_fcfa(total)} est un montant élevé. Je confirme ?"


def resume(libelle: str, nb: int, total: int, par_mode: dict[str, int], impayes: int, charges: int = 0, benefice: int | None = None) -> str:
    if nb == 0 and charges == 0:
        return f"{libelle} : aucune vente enregistrée pour l'instant."
    details = ", ".join(f"{format_fcfa(m)} {LIBELLES_MODE[mode]}" for mode, m in par_mode.items() if m > 0 and mode in LIBELLES_MODE)
    if nb == 0:
        texte = f"{libelle} : aucune vente"
    else:
        texte = f"{libelle} : {nb} vente{'s' if nb > 1 else ''}, {format_fcfa(total)}"
        if details:
            texte += f" ({details})"
    texte += "."
    texte += f" Charges : {format_fcfa(charges)}."
    if benefice is not None:
        texte += f" Bénéfice estimé : {format_fcfa(benefice)}."
    if impayes > 0:
        texte += f" Impayés en cours : {format_fcfa(impayes)}."
    return texte


def qui_doit(lignes: Sequence[tuple[str, int, str]]) -> str:
    """lignes : (nom du client, montant dû, détail)."""
    if not lignes:
        return "Personne ne te doit d'argent. 👍"
    total = sum(m for _, m, _ in lignes)
    corps = "\n".join(f"• {nom} : {format_fcfa(m)} ({detail})" for nom, m, detail in lignes)
    return f"On te doit {format_fcfa(total)} :\n{corps}"


def facture_recap(client: str, recap: str, total: int, client_nouveau: bool) -> str:
    texte = f"Voici la facture pour {client} :\n{recap}\n{total_ligne(total)}"
    if client_nouveau:
        texte += f"\n(J'ajouterai {client} à ton carnet.)"
    texte += "\nJe la prépare et je te l'envoie pour que tu la transfères ?"
    return texte


def facture_prete(numero: int, client: str, total: int, lien: str | None = None) -> str:
    texte = (
        f"Facture n° {numero:03d} pour {client} : {format_fcfa(total)}. "
        "Elle est jointe ci-dessus : transfère-la à ton client. "
        f"Dis-moi « {client} a payé » quand c'est réglé."
    )
    if lien:
        texte += f"\nLien de paiement : {lien} (Paiement simulé)"
    return texte


def facture_prete_direct(numero: int, client: str, total: int, lien: str | None = None) -> str:
    texte = f"Facture n° {numero:03d} pour {client} : {format_fcfa(total)}. Je l'envoie à {client} sur WhatsApp. Dis-moi « {client} a payé » quand c'est réglé."
    if lien:
        texte += f"\nLien de paiement : {lien} (Paiement simulé)"
    return texte


def facture_pour_client(commerce: str, client: str, numero: int, total: int, lien: str | None = None) -> str:
    texte = f"Bonjour {client}, voici votre facture n° {numero:03d} de {format_fcfa(total)} de la part de {commerce}. Merci !"
    if lien:
        texte += f"\nPaiement : {lien}"
    return texte


def relance_envoi_direct(client: str) -> str:
    return f"D'accord, j'envoie la relance à {client} sur WhatsApp."


def envoi_ok(client: str, simule: bool) -> str:
    return f"✅ Envoyé à {client} sur WhatsApp." + (" (démo : envoi simulé)" if simule else "")


def envoi_echec(client: str) -> str:
    return f"⚠️ Je n'ai pas pu envoyer le message à {client}. Transfère-le toi-même, je ne l'ai pas envoyé."


def confirmation_renforcee(mot: str) -> str:
    return f"Montant élevé. Pour confirmer, tape exactement le mot : {mot}"


def demande_oui_non(question: str) -> str:
    return f"{question} OUI / NON"


def rappel_question(question: str) -> str:
    return f"Je n'ai pas compris ta réponse. {question}"


def action_abandonnee() -> str:
    return "D'accord, j'abandonne. On fait quoi ?"


def action_expiree() -> str:
    return "L'action en attente a expiré, je ne l'ai pas enregistrée. Redis-moi si besoin."


def rien_a_confirmer() -> str:
    return "Il n'y a rien à confirmer pour l'instant."


def annule(resume_action: str) -> str:
    return f"Annulé : {resume_action}."


def rien_a_annuler() -> str:
    return "Je n'ai rien à annuler : la dernière action date de plus de 10 minutes ou n'existe pas."


def relance_texte(nom_commerce: str, client: str, numero: int, total: int, jours: int) -> str:
    retard = f" depuis {jours} jours" if jours > 0 else ""
    return (
        f"Bonjour {client}, c'est {nom_commerce}. Petit rappel : la facture n° {numero:03d} "
        f"de {format_fcfa(total)} est en attente de paiement{retard}. "
        "Merci de me dire quand je peux l'encaisser. Bonne journée !"
    )


def relance_proposee(client: str, texte: str) -> str:
    return f"Voici la relance pour {client} :\n« {texte} »\nJe te l'envoie pour que tu la transfères ?"


def relance_prete(client: str, texte: str) -> str:
    return f"Copie ce message et envoie-le à {client} :\n\n{texte}"


def relance_plafond(client: str) -> str:
    return f"J'ai déjà relancé {client} cette semaine. On attend un peu avant de relancer encore."


def rien_d_ouvert(client: str | None) -> str:
    if client:
        return f"{client} ne te doit rien d'après mes notes."
    return "Aucune facture ni vente à crédit en attente."


def paiement_recu_recap(client: str, detail: str, montant: int) -> str:
    return f"Je marque {detail} de {client} ({format_fcfa(montant)}) comme payée ?"


def paiement_recu_note(client: str, montant: int, reste_client: int) -> str:
    texte = f"C'est noté : {format_fcfa(montant)} reçus de {client}."
    if reste_client > 0:
        texte += f" {client} te doit encore {format_fcfa(reste_client)}."
    else:
        texte += f" {client} est à jour. 👍"
    return texte


def lien_indisponible_credit(montant: int, client: str) -> str:
    return (
        "Le lien de paiement n'est pas encore disponible. "
        f"Je note {format_fcfa(montant)} à crédit pour {client}, et tu me diras quand c'est payé ?"
    )


def produit_ajoute(nom: str, prix: int) -> str:
    return f"C'est noté : {nom} à {format_fcfa(prix)}."


def produit_mis_a_jour(nom: str, prix: int) -> str:
    return f"Prix mis à jour : {nom} à {format_fcfa(prix)}."


def client_ajoute(nom: str, telephone: str | None) -> str:
    tel = f" ({telephone})" if telephone else ""
    return f"C'est noté : {nom}{tel} est dans ton carnet."


def aide() -> str:
    return (
        "Voilà ce que je sais faire :\n"
        "• noter une vente : « j'ai vendu 3 paires à 5000 »\n"
        "• faire une facture : « facture pour Lycée Technique, 30 repas à 2500 »\n"
        "• dire qui te doit : « qui me doit ? »\n"
        "• préparer une relance : « relance Mme Fouda »\n"
        "• noter un paiement : « Jean a payé »\n"
        "• faire le point : « j'ai fait combien aujourd'hui ? »\n"
        "• ajouter un produit ou un client : « ajoute sandales rouges 7500 »\n"
        "• noter une dépense : « j'ai payé 20 000 de loyer » (dis « c'est perso » pour un retrait personnel)\n"
        "• voir trésorerie et bénéfice : « mon bénéfice »\n"
        "• ton dossier de crédit : « prépare mon dossier de crédit »\n"
        "• ton impôt estimé : « mon impôt »\n"
        "Dis « annuler » pour annuler la dernière action, « humain » pour parler à quelqu'un."
    )


def hors_perimetre() -> str:
    return (
        "Je ne suis pas formé pour ça et je préfère ne pas te donner une mauvaise information. "
        "Je peux par contre t'aider pour tes ventes, tes factures et tes relances."
    )


def refus_piege() -> str:
    return (
        "Je ne peux pas faire ça : je n'envoie jamais de message ni de demande d'argent "
        "sans que tu confirmes chaque client et chaque montant."
    )


def incompris() -> str:
    return (
        "Je n'ai pas compris. Tu peux me dire par exemple « j'ai vendu 2 poulets à 4000 » "
        "ou « j'ai fait combien aujourd'hui ? »."
    )


def vocal_incompris() -> str:
    return "Je n'ai pas bien entendu ton vocal. Tu peux répéter ou l'écrire ?"


def panne() -> str:
    return "Désolé, j'ai un souci technique et je n'ai rien enregistré. Réessaie dans un instant."


def humain() -> str:
    return "D'accord, quelqu'un de l'équipe te contacte rapidement. En attendant, je reste là."


def numero_inconnu() -> str:
    return (
        "Bonjour ! Je suis Moki. Ce numéro n'est pas encore inscrit. "
        "Contacte l'équipe Mon Kiosque pour ouvrir ton espace."
    )


def precision_vente() -> str:
    return "Qu'est-ce que tu as vendu, combien, et à quel prix ?"


def precision_client_facture() -> str:
    return "Pour quel client ?"


def precision_relance() -> str:
    return "Qui veux-tu relancer ?"


def precision_credit_client() -> str:
    return "À qui tu as vendu à crédit ?"


def precision_choix_facture(choix: Sequence[str]) -> str:
    return "Laquelle ? " + " ou ".join(choix)


def depense_notee(libelle: str, montant: int, nature: str, type_: str) -> str:
    if nature == "perso":
        return f"C'est noté : retrait personnel de {format_fcfa(montant)} ({libelle}). Il n'est pas compté dans les charges du commerce. Dis « annuler » si tu t'es trompée."
    if type_ == "stock":
        return (
            f"C'est noté : achat de stock de {format_fcfa(montant)} ({libelle}). "
            "Ça sort de ta trésorerie mais pas de ton bénéfice tant que ce n'est pas vendu. Dis « annuler » si tu t'es trompée."
        )
    return f"C'est noté : dépense de {format_fcfa(montant)} ({libelle}), classée en professionnelle. Dis « c'est perso » pour la changer, ou « annuler »."


def nature_changee(libelle: str, montant: int, nature: str) -> str:
    if nature == "perso":
        return f"D'accord : {libelle} ({format_fcfa(montant)}) est maintenant un retrait personnel, hors des charges du commerce."
    return f"D'accord : {libelle} ({format_fcfa(montant)}) est maintenant une dépense professionnelle."


def precision_depense() -> str:
    return "C'était pour quoi, et combien ?"


def rien_a_changer() -> str:
    return "Je n'ai pas de dépense récente à modifier."


def bilan(tresorerie: int, benefice: int, retraits: int, ventes: int, charges: int) -> str:
    return (
        f"💰 Trésorerie (argent disponible) : {format_fcfa(tresorerie)}.\n"
        f"📈 Bénéfice du mois : {format_fcfa(benefice)} (ventes {format_fcfa(ventes)} − charges {format_fcfa(charges)}).\n"
        f"👤 Retraits personnels du mois : {format_fcfa(retraits)} (pas comptés dans les charges)."
    )


def dossier_pret(historique: int, manque: int, fictives: bool) -> str:
    texte = "Ton dossier de crédit est prêt (PDF ci-joint). Il est calculé uniquement à partir de tes saisies."
    if fictives:
        texte += " ⚠️ Démo : ce sont des données fictives."
    if manque > 0:
        texte += f" Ton historique est de {historique} mois : il manque {manque} mois pour atteindre 6 mois de données."
    else:
        texte += f" Ton historique couvre {historique} mois : c'est suffisant pour un dossier."
    return texte


def impot(estimation: int, ca_annuel: int, echeance_libelle: str, jours: int) -> str:
    return (
        f"Estimation de ton impôt (IGS) : environ {format_fcfa(estimation)} par an, sur un chiffre d'affaires annuel estimé à {format_fcfa(ca_annuel)}.\n"
        "⚠️ Estimation à confirmer avec la DGI : c'est indicatif, pas un conseil fiscal.\n"
        f"Prochaine échéance : {echeance_libelle}, dans {jours} jour{'s' if jours > 1 else ''}."
    )


def echeances(liste: Sequence[dict]) -> str:
    corps = "\n".join(f"• {e['libelle']} : le {e['date'][8:10]}/{e['date'][5:7]}, dans {e['jours']} jour{'s' if e['jours'] > 1 else ''}" for e in liste)
    return f"Tes prochaines échéances (indicatives, à confirmer avec la DGI) :\n{corps}\nJe te préviens 15 jours puis 3 jours avant."


def rappel_fiscal(libelle: str, jours: int, date_iso: str) -> str:
    return f"⏰ Rappel : {libelle} le {date_iso[8:10]}/{date_iso[5:7]}, dans {jours} jours. Estimation à confirmer avec la DGI."


def produit_supprime(nom: str) -> str:
    return f"C'est fait : {nom} est retiré de ton catalogue."


def produit_introuvable(nom: str) -> str:
    return f"Je ne trouve pas « {nom} » dans ton catalogue."


def compte_indisponible() -> str:
    return "Ce numéro est déjà lié à un compte qui n'est pas actif. Contacte l'équipe Mon Kiosque."


def bienvenue_nom() -> str:
    return "Bienvenue sur Mon Kiosque ! 👋 Moi c'est Moki, ton assistant pour tenir ta caisse, tes factures et tes relances. Pour ouvrir ton compte, 3 petites questions. D'abord : comment s'appelle ton commerce ?"


def inscription_ville(nom: str) -> str:
    return f"Super, « {nom} » ! Dans quelle ville ?"


def inscription_secteur() -> str:
    return "Et ton secteur ? (boutique, restaurant/snack, services…)"


def inscription_ecrire() -> str:
    return "Écris-moi ta réponse par message, s'il te plaît."


def inscription_ok(nom: str) -> str:
    return f"C'est bon, ton compte « {nom} » est ouvert ! 🎉 Commence par m'ajouter un produit, par exemple « ajoute sandales rouges 7500 », ou dis-moi « j'ai vendu 3 paires à 5000 ». Dis « aide » pour voir tout ce que je sais faire."
