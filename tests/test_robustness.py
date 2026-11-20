"""Tests de robustesse : entrées limites, non finies, hors distribution, schéma incorrect, fuzzing.

Distinction appliquée :
* entrée INVALIDE      → rejet 4xx, jamais de 500, jamais de probabilité renvoyée ;
* entrée INHABITUELLE  → 200, probabilité valide, alertes + analyse complémentaire requise.
"""

from __future__ import annotations

import json
import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app import config

from .conftest import DEMANDE_VALIDE


def poster_brut(client, texte: str):
    return client.post("/predict", content=texte, headers={"content-type": "application/json"})


def assert_probabilite_valide(res: dict):
    p = res["probabilite_defaut"]
    assert isinstance(p, float)
    assert math.isfinite(p)
    assert 0.0 <= p <= 1.0


# ===================================================================== valeurs manquantes
@pytest.mark.exigence("EX06")
@pytest.mark.parametrize("champ", config.VARIABLES_ENTREE)
def test_valeur_null(client, demande, champ):
    """TR01 Valeur JSON null sur un champ : 422, le champ est identifié."""
    demande[champ] = None
    r = client.post("/predict", json=demande)
    assert r.status_code == 422
    assert champ in {d["champ"] for d in r.json()["erreur"]["details"]}


@pytest.mark.exigence("EX06")
def test_plusieurs_champs_manquants_tous_signales(client):
    """TR02 Plusieurs champs absents : toutes les erreurs sont listées en une réponse."""
    r = client.post("/predict", json={"age": 35})
    champs = {d["champ"] for d in r.json()["erreur"]["details"]}
    assert champs == set(config.VARIABLES_ENTREE) - {"age"}


# ===================================================================== non numériques
@pytest.mark.exigence("EX02", "EX03", "EX08")
@pytest.mark.parametrize(
    "valeur", ["", " ", "abc", "1e5", "250 000", "250,000", [1], {"v": 1}, True, False]
)
@pytest.mark.parametrize("champ", config.VARIABLES_ENTREE)
def test_valeurs_non_numeriques(client, demande, champ, valeur):
    """TR03 Texte, liste, objet ou booléen dans un champ numérique : 422 (10 × 5 cas)."""
    demande[champ] = valeur
    r = client.post("/predict", json=demande)
    assert r.status_code == 422
    assert "probabilite_defaut" not in r.text


# ===================================================================== non finies
@pytest.mark.exigence("EX10")
@pytest.mark.parametrize("litteral", ["NaN", "Infinity", "-Infinity", "1e400", "-1e400"])
@pytest.mark.parametrize("champ", config.VARIABLES_ENTREE)
def test_valeurs_non_finies_dans_le_json_brut(client, champ, litteral):
    """TR04 NaN / Infinity / 1e400 (débordement) envoyés tels quels : 422 (5 × 5 cas).

    Le parseur JSON de Python accepte ces littéraux non standard ; seule la validation
    les arrête. Ce test vérifie qu'aucun n'atteint le modèle.
    """
    corps = json.dumps(DEMANDE_VALIDE).replace(
        f'"{champ}": {json.dumps(DEMANDE_VALIDE[champ])}', f'"{champ}": {litteral}'
    )
    assert litteral in corps
    r = poster_brut(client, corps)
    assert r.status_code == 422, r.text


# ===================================================================== bornes
BORNES_VALIDES = [
    {"age": 18, "anciennete_activite": 0},
    {"age": 75, "anciennete_activite": 60},
    {"duree_mois": 1},
    {"duree_mois": 120},
    {"revenu_mensuel": 1},
    {"revenu_mensuel": config.REVENU_MAX},
    {"montant_credit": 1},
    {"montant_credit": config.MONTANT_MAX},
    {"anciennete_activite": 0},
    {"revenu_mensuel": 1e-9},
]


@pytest.mark.exigence("EX01", "EX02", "EX03", "EX04", "EX08")
@pytest.mark.parametrize("modifs", BORNES_VALIDES, ids=json.dumps)
def test_valeurs_aux_bornes_acceptees(client, demande, modifs):
    """TR05 Chaque borne autorisée est acceptée et donne une probabilité valide."""
    demande.update(modifs)
    r = client.post("/predict", json=demande)
    assert r.status_code == 200, r.text
    assert_probabilite_valide(r.json())


BORNES_INVALIDES = [
    ("age", 17),
    ("age", 76),
    ("duree_mois", 0),
    ("duree_mois", 121),
    ("revenu_mensuel", 0),
    ("revenu_mensuel", config.REVENU_MAX * 1.000001),
    ("montant_credit", 0),
    ("montant_credit", config.MONTANT_MAX + 0.01),
    ("anciennete_activite", -0.01),
    ("anciennete_activite", 60.01),
]


@pytest.mark.exigence("EX01", "EX02", "EX03", "EX08", "EX13")
@pytest.mark.parametrize("champ,valeur", BORNES_INVALIDES)
def test_valeurs_juste_hors_bornes_rejetees(client, demande, champ, valeur):
    """TR06 La première valeur au-delà de chaque borne est rejetée."""
    demande[champ] = valeur
    if champ == "anciennete_activite":
        demande["age"] = 75
    assert client.post("/predict", json=demande).status_code == 422


# ===================================================================== hors distribution
HORS_DISTRIBUTION = [
    ("revenu tres faible", {"revenu_mensuel": 1000}, "hors_domaine:revenu_mensuel"),
    ("revenu tres eleve", {"revenu_mensuel": 50_000_000}, "hors_domaine:revenu_mensuel"),
    ("montant tres eleve", {"montant_credit": 300_000_000}, "hors_domaine:montant_credit"),
    ("duree longue", {"duree_mois": 120}, "hors_domaine:duree_mois"),
    ("age maximal", {"age": 75}, "hors_domaine:age"),
    (
        "anciennete elevee",
        {"age": 70, "anciennete_activite": 50},
        "hors_domaine:anciennete_activite",
    ),
    (
        "mensualite > revenu",
        {"montant_credit": 5_000_000, "duree_mois": 3},
        "mensualite_superieure_au_revenu",
    ),
]


@pytest.mark.exigence("EX14", "EX04")
@pytest.mark.parametrize(
    "nom,modifs,alerte", HORS_DISTRIBUTION, ids=[h[0] for h in HORS_DISTRIBUTION]
)
def test_entree_valide_hors_distribution_signalee(client, demande, nom, modifs, alerte):
    """TR07 Entrée valide mais loin des données d'entraînement : 200 + alerte + analyse."""
    demande.update(modifs)
    r = client.post("/predict", json=demande)
    assert r.status_code == 200
    res = r.json()
    assert_probabilite_valide(res)
    assert alerte in res["alertes"]
    assert res["analyse_complementaire_requise"] is True


@pytest.mark.exigence("EX14")
def test_entree_typique_sans_alerte(client, demande):
    """TR08 Une demande typique ne déclenche aucune alerte (pas de fausse alerte)."""
    assert client.post("/predict", json=demande).json()["alertes"] == []


# ===================================================================== schéma incorrect
SCHEMAS_INCORRECTS = [
    ("liste d'objets", [DEMANDE_VALIDE]),
    ("objet imbriqué", {"demande": DEMANDE_VALIDE}),
    ("noms en majuscules", {k.upper(): v for k, v in DEMANDE_VALIDE.items()}),
    (
        "nom mal orthographié",
        {**{k: v for k, v in DEMANDE_VALIDE.items() if k != "age"}, "agee": 35},
    ),
    ("valeurs en tableau", {k: [v] for k, v in DEMANDE_VALIDE.items()}),
    ("objet vide", {}),
]


@pytest.mark.exigence("EX06", "EX09")
@pytest.mark.parametrize("nom,corps", SCHEMAS_INCORRECTS, ids=[s[0] for s in SCHEMAS_INCORRECTS])
def test_schema_incorrect(client, nom, corps):
    """TR09 Schéma incorrect (imbriqué, renommé, tableau…) : 422, jamais 200 ni 500."""
    r = client.post("/predict", json=corps)
    assert r.status_code == 422


@pytest.mark.exigence("EX11")
def test_cles_dupliquees_dans_le_json(client):
    """TR10 Clé dupliquée : le parseur garde la dernière valeur, qui est validée.

    Comportement documenté (RFC 8259 laisse le choix) ; une valeur invalide en double
    est bien rejetée.
    """
    corps = json.dumps(DEMANDE_VALIDE)[:-1] + ', "age": -3}'
    assert poster_brut(client, corps).status_code == 422


@pytest.mark.exigence("EX11")
def test_encodage_non_utf8(client):
    """TR11 Corps non UTF-8 : 400 ou 422, pas d'erreur 500."""
    corps = json.dumps({**DEMANDE_VALIDE, "x": "é"}, ensure_ascii=False).encode("latin-1")
    r = client.post("/predict", content=corps, headers={"content-type": "application/json"})
    assert r.status_code in (400, 422)


# ===================================================================== cohérence des prédictions
@pytest.mark.exigence("EX15")
def test_determinisme_appels_repetes(client, demande):
    """TR12 La même requête envoyée 20 fois donne exactement la même réponse."""
    reponses = {
        json.dumps(client.post("/predict", json=demande).json(), sort_keys=True) for _ in range(20)
    }
    assert len(reponses) == 1


@pytest.mark.exigence("EX15")
def test_ordre_des_champs_sans_effet(client, demande):
    """TR13 L'ordre des clés JSON n'influence pas la prédiction."""
    inverse = dict(reversed(list(demande.items())))
    assert (
        client.post("/predict", json=inverse).json() == client.post("/predict", json=demande).json()
    )


@pytest.mark.exigence("EX15")
def test_entier_et_decimal_equivalents(client, demande):
    """TR14 revenu 250000 et 250000.0 donnent la même probabilité."""
    a = client.post("/predict", json=demande).json()
    demande["revenu_mensuel"] = 250000.0
    assert client.post("/predict", json=demande).json() == a


# ===================================================================== propriétés (Hypothesis)
demandes_valides = st.fixed_dictionaries(
    {
        "age": st.integers(config.AGE_MIN, config.AGE_MAX),
        "revenu_mensuel": st.floats(1, config.REVENU_MAX, allow_nan=False),
        "montant_credit": st.floats(1, config.MONTANT_MAX, allow_nan=False),
        "duree_mois": st.integers(config.DUREE_MIN, config.DUREE_MAX),
        "fraction_anciennete": st.floats(0, 1),
    }
).map(
    lambda d: {
        **{k: v for k, v in d.items() if k != "fraction_anciennete"},
        "anciennete_activite": round(d["fraction_anciennete"] * min(60, d["age"] - 12), 2),
    }
)

REGLAGES = settings(
    max_examples=150, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


@pytest.mark.exigence("EX04", "EX14")
@REGLAGES
@given(d=demandes_valides)
def test_propriete_toute_entree_valide_donne_une_probabilite(client, d):
    """TR15 Propriété : toute entrée valide (150 tirages) → 200 et probabilité dans [0, 1]."""
    r = client.post("/predict", json=d)
    assert r.status_code == 200, (d, r.text)
    assert_probabilite_valide(r.json())


valeurs_quelconques = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(-(10**20), 10**20),
    st.floats(allow_nan=False, allow_infinity=False),  # inf : testé en JSON brut (TR04)
    st.text(max_size=20),
    st.lists(st.integers(), max_size=3),
)


@pytest.mark.exigence("EX06", "EX10", "EX12")
@REGLAGES
@given(
    corps=st.dictionaries(
        st.sampled_from([*config.VARIABLES_ENTREE, "autre"]), valeurs_quelconques, max_size=7
    )
)
def test_fuzzing_aucune_erreur_500(client, corps):
    """TR16 Fuzzing (150 corps aléatoires) : jamais de 500 ; 200 ⇒ probabilité valide."""
    r = client.post("/predict", json=corps)
    assert r.status_code in (200, 422), (corps, r.status_code, r.text)
    if r.status_code == 200:
        assert_probabilite_valide(r.json())


def _taux(d):
    return d["montant_credit"] / d["duree_mois"] / d["revenu_mensuel"]


@pytest.mark.exigence("EX19")
@REGLAGES
@given(d=demandes_valides.filter(lambda d: _taux(d) >= 0.01), facteur=st.floats(1.01, 10))
def test_monotonie_montant(service_charge, d, facteur):
    """TR17 Propriété métier : à profil égal, un montant plus élevé ne baisse pas le risque.

    Domaine : mensualité >= 1 % du revenu (100 % des dossiers d'entraînement, minimum 1,9 %).
    """
    from app.preprocessing import transformer

    plus = {**d, "montant_credit": min(d["montant_credit"] * facteur, config.MONTANT_MAX)}
    p0, p1 = service_charge.predire_probabilites(transformer([d, plus]))
    assert p1 >= p0 - 1e-12


@pytest.mark.exigence("EX19")
@pytest.mark.xfail(
    strict=True,
    reason="Anomalie A02 : monotonie rompue si mensualité < 0,44 % "
    "du revenu (coefficient négatif sur log_montant)",
)
def test_monotonie_montant_domaine_complet(service_charge):
    """TR17b Anomalie connue : hors domaine réaliste, le risque baisse quand le montant monte."""
    from app.preprocessing import transformer

    d = {
        "age": 18,
        "revenu_mensuel": 3.0,
        "montant_credit": 1.0,
        "duree_mois": 109,
        "anciennete_activite": 0.0,
    }
    p0, p1 = service_charge.predire_probabilites(transformer([d, {**d, "montant_credit": 2.0}]))
    assert p1 >= p0


@pytest.mark.exigence("EX19")
@REGLAGES
@given(d=demandes_valides, facteur=st.floats(1.01, 10))
def test_monotonie_revenu(service_charge, d, facteur):
    """TR18 Propriété métier : à profil égal, un revenu plus élevé ne hausse pas le risque."""
    from app.preprocessing import transformer

    plus = {**d, "revenu_mensuel": min(d["revenu_mensuel"] * facteur, config.REVENU_MAX)}
    p0, p1 = service_charge.predire_probabilites(transformer([d, plus]))
    assert p1 <= p0 + 1e-12
