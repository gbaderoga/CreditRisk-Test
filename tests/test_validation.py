"""Tests unitaires du module de validation (sans API ni modèle)."""

from __future__ import annotations

import math

import pytest

from app import config
from app.validation import DemandeCredit, ErreurValidation, valider_demande

from .conftest import DEMANDE_VALIDE


def avec(**modifs):
    d = dict(DEMANDE_VALIDE)
    d.update(modifs)
    return d


def champs_en_erreur(donnees) -> set[str]:
    with pytest.raises(ErreurValidation) as exc:
        valider_demande(donnees)
    return {d["champ"] for d in exc.value.details}


@pytest.mark.exigence("EX01", "EX02", "EX03", "EX08")
def test_demande_valide_acceptee():
    """TV01 Une demande conforme est acceptée et convertie sans perte."""
    d = valider_demande(DEMANDE_VALIDE)
    assert isinstance(d, DemandeCredit)
    assert d.model_dump() == {k: v for k, v in DEMANDE_VALIDE.items()}


# --------------------------------------------------------------------------- EX01 âge
@pytest.mark.exigence("EX01")
@pytest.mark.parametrize("age", [config.AGE_MIN, 40, config.AGE_MAX])
def test_age_aux_bornes_accepte(age):
    """TV02 Les âges situés aux bornes incluses (18 et 75) sont acceptés."""
    anciennete = min(DEMANDE_VALIDE["anciennete_activite"], age - 12)
    assert valider_demande(avec(age=age, anciennete_activite=anciennete)).age == age


@pytest.mark.exigence("EX01")
@pytest.mark.parametrize("age", [-1, 0, config.AGE_MIN - 1, config.AGE_MAX + 1, 150])
def test_age_hors_limites_rejete(age):
    """TV03 Un âge hors de [18, 75] est rejeté sur le champ age."""
    assert "age" in champs_en_erreur(avec(age=age, anciennete_activite=0))


@pytest.mark.exigence("EX01")
@pytest.mark.parametrize("age", [35.5, 35.0, "35", True, None])
def test_age_non_entier_rejete(age):
    """TV04 Un âge décimal, textuel, booléen ou nul est rejeté (typage strict)."""
    assert "age" in champs_en_erreur(avec(age=age))


# --------------------------------------------------------------------------- EX02 revenu
@pytest.mark.exigence("EX02")
@pytest.mark.parametrize("revenu", [0, -1, -250000, "250000", "abc", None, True, [250000]])
def test_revenu_invalide_rejete(revenu):
    """TV05 Un revenu nul, négatif ou non numérique provoque une erreur contrôlée."""
    assert "revenu_mensuel" in champs_en_erreur(avec(revenu_mensuel=revenu))


@pytest.mark.exigence("EX02")
@pytest.mark.parametrize("revenu", [1, 250000, 250000.75, config.REVENU_MAX])
def test_revenu_positif_accepte(revenu):
    """TV06 Un revenu entier ou décimal strictement positif et <= max est accepté."""
    assert valider_demande(avec(revenu_mensuel=revenu)).revenu_mensuel == revenu


@pytest.mark.exigence("EX02")
def test_revenu_au_dessus_du_maximum_rejete():
    """TV07 Un revenu supérieur au plafond documenté est rejeté."""
    assert "revenu_mensuel" in champs_en_erreur(avec(revenu_mensuel=config.REVENU_MAX + 1))


# --------------------------------------------------------------------------- EX03 durée
@pytest.mark.exigence("EX03")
@pytest.mark.parametrize("duree", [config.DUREE_MIN, 12, config.DUREE_MAX])
def test_duree_valide_acceptee(duree):
    """TV08 Les durées entières de 1 à 120 mois sont acceptées."""
    assert valider_demande(avec(duree_mois=duree)).duree_mois == duree


@pytest.mark.exigence("EX03")
@pytest.mark.parametrize("duree", [0, -12, 121, 12.5, 12.0, "12", None])
def test_duree_invalide_rejetee(duree):
    """TV09 Une durée nulle, négative, > 120, décimale ou textuelle est rejetée."""
    assert "duree_mois" in champs_en_erreur(avec(duree_mois=duree))


# --------------------------------------------------------------------------- EX08 montant
@pytest.mark.exigence("EX08")
@pytest.mark.parametrize("montant", [0, -1, -1000000, "1000000", config.MONTANT_MAX + 1])
def test_montant_invalide_rejete(montant):
    """TV10 Un montant nul, négatif, textuel ou au-delà du plafond est rejeté."""
    assert "montant_credit" in champs_en_erreur(avec(montant_credit=montant))


# --------------------------------------------------------------------------- EX06 complétude
@pytest.mark.exigence("EX06")
@pytest.mark.parametrize("champ", config.VARIABLES_ENTREE)
def test_champ_obligatoire_absent(champ):
    """TV11 L'absence de chacun des 5 champs obligatoires est signalée sur ce champ."""
    d = dict(DEMANDE_VALIDE)
    del d[champ]
    assert champ in champs_en_erreur(d)


@pytest.mark.exigence("EX06")
def test_demande_vide_signale_tous_les_champs():
    """TV12 Un objet vide produit une erreur par champ obligatoire."""
    assert champs_en_erreur({}) == set(config.VARIABLES_ENTREE)


@pytest.mark.exigence("EX06")
@pytest.mark.parametrize("donnees", [None, [], [DEMANDE_VALIDE], "texte", 42])
def test_entree_qui_n_est_pas_un_objet(donnees):
    """TV13 Une entrée qui n'est pas un objet est rejetée par une erreur contrôlée."""
    with pytest.raises(ErreurValidation):
        valider_demande(donnees)


# --------------------------------------------------------------------------- EX09 extra
@pytest.mark.exigence("EX09")
def test_champ_supplementaire_rejete():
    """TV14 Un champ non prévu au contrat est refusé (pas ignoré silencieusement)."""
    assert "sexe" in champs_en_erreur(avec(sexe="F"))


# --------------------------------------------------------------------------- EX10 finitude
@pytest.mark.exigence("EX10")
@pytest.mark.parametrize("champ", ["revenu_mensuel", "montant_credit", "anciennete_activite"])
@pytest.mark.parametrize("valeur", [math.nan, math.inf, -math.inf])
def test_valeurs_non_finies_rejetees(champ, valeur):
    """TV15 NaN, +inf et -inf sont rejetés sur les champs décimaux."""
    assert champ in champs_en_erreur(avec(**{champ: valeur}))


# --------------------------------------------------------------------------- EX13 cohérence
@pytest.mark.exigence("EX13")
def test_anciennete_incompatible_avec_age():
    """TV16 Une ancienneté supérieure à (âge - 12) ans est rejetée sur ce champ."""
    assert champs_en_erreur(avec(age=20, anciennete_activite=9)) == {"anciennete_activite"}


@pytest.mark.exigence("EX13")
def test_anciennete_a_la_limite_de_coherence_acceptee():
    """TV17 Une ancienneté exactement égale à (âge - 12) est acceptée."""
    assert valider_demande(avec(age=20, anciennete_activite=8)).anciennete_activite == 8


@pytest.mark.exigence("EX13")
def test_anciennete_negative_rejetee():
    """TV18 Une ancienneté négative est rejetée."""
    assert "anciennete_activite" in champs_en_erreur(avec(anciennete_activite=-1))


@pytest.mark.exigence("EX12")
def test_message_d_erreur_ne_reflete_pas_la_valeur():
    """TV19 Le détail d'erreur ne recopie pas la valeur reçue (donnée personnelle)."""
    with pytest.raises(ErreurValidation) as exc:
        valider_demande(avec(revenu_mensuel=-987654))
    assert "987654" not in str(exc.value.details)


@pytest.mark.exigence("EX12")
def test_formatage_erreur_sans_contexte():
    """TV20 Une erreur pydantic sans contexte ou de type inconnu reste formatée proprement."""
    from app.validation import formater_erreurs

    (a, b) = formater_erreurs(
        [
            {"loc": ("body", "age"), "type": "greater_than_equal", "msg": "x"},
            {"loc": (), "type": "autre", "msg": "Value error, message"},
        ]
    )
    assert a == {
        "champ": "age",
        "type": "greater_than_equal",
        "message": "valeur trop petite (doit être >= {ge})",
    }
    assert b["champ"] == "(requête)" and b["message"] == "message"
