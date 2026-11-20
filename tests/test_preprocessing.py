"""Tests unitaires du module de prétraitement."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.preprocessing import (
    VARIABLES_MODELE,
    ErreurPretraitement,
    construire_variables,
    transformer,
)
from app.validation import valider_demande

from .conftest import DEMANDE_VALIDE


@pytest.mark.exigence("EX21")
def test_variables_derivees_calculees_exactement():
    """TP01 Les 6 variables dérivées ont les valeurs attendues (calcul à la main)."""
    v = construire_variables(DEMANDE_VALIDE)
    assert list(v) == list(VARIABLES_MODELE)
    assert v["age"] == 35
    assert v["log_revenu"] == pytest.approx(math.log(250_000))
    assert v["log_montant"] == pytest.approx(math.log(1_000_000))
    assert v["duree_mois"] == 12
    assert v["anciennete_activite"] == 4
    # mensualité 83 333,33 / revenu 250 000 = 0,3333
    assert v["log_taux_endettement"] == pytest.approx(math.log1p(1_000_000 / 12 / 250_000))


@pytest.mark.exigence("EX21")
def test_objet_valide_et_dictionnaire_donnent_le_meme_resultat():
    """TP02 Un DemandeCredit et le dict équivalent produisent le même vecteur."""
    assert np.array_equal(
        transformer([valider_demande(DEMANDE_VALIDE)]), transformer([DEMANDE_VALIDE])
    )


@pytest.mark.exigence("EX21")
def test_dimensions_de_sortie():
    """TP03 n demandes donnent une matrice (n, 6) de flottants finis."""
    X = transformer([DEMANDE_VALIDE] * 7)
    assert X.shape == (7, len(VARIABLES_MODELE))
    assert X.dtype == float and np.isfinite(X).all()


@pytest.mark.exigence("EX06", "EX21")
def test_variable_absente():
    """TP04 Une variable absente lève ErreurPretraitement (pas KeyError)."""
    d = dict(DEMANDE_VALIDE)
    del d["duree_mois"]
    with pytest.raises(ErreurPretraitement, match="duree_mois"):
        construire_variables(d)


@pytest.mark.exigence("EX21")
@pytest.mark.parametrize("champ", ["revenu_mensuel", "montant_credit", "duree_mois"])
def test_division_ou_log_impossible(champ):
    """TP05 Revenu, montant ou durée nuls (non validés) : erreur contrôlée, pas de crash."""
    with pytest.raises(ErreurPretraitement):
        construire_variables({**DEMANDE_VALIDE, champ: 0})


@pytest.mark.exigence("EX21")
def test_valeur_non_numerique():
    """TP06 Une valeur non convertible lève ErreurPretraitement."""
    with pytest.raises(ErreurPretraitement):
        construire_variables({**DEMANDE_VALIDE, "age": "trente"})


@pytest.mark.exigence("EX10", "EX21")
def test_valeur_non_finie_produite():
    """TP07 Une valeur infinie qui aurait échappé à la validation est bloquée."""
    with pytest.raises(ErreurPretraitement, match="non finie"):
        construire_variables({**DEMANDE_VALIDE, "anciennete_activite": math.inf})


@pytest.mark.exigence("EX21")
@pytest.mark.parametrize("entree", [[], [42], ["texte"]])
def test_entrees_non_prises_en_charge(entree):
    """TP08 Liste vide ou éléments de type inattendu : ErreurPretraitement."""
    with pytest.raises(ErreurPretraitement):
        transformer(entree)
