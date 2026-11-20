"""Tests fonctionnels de l'API : contrat de GET /health, POST /predict, GET /model-info.

Les 10 scénarios obligatoires du sujet sont repérés S01 à S10.
"""

from __future__ import annotations

import math

import pytest

from app import config

CLES_REPONSE = {
    "probabilite_defaut",
    "niveau_risque",
    "recommandation",
    "analyse_complementaire_requise",
    "alertes",
    "version_modele",
}


def assert_erreur(response, statut: int, code: str, champ: str | None = None):
    assert response.status_code == statut, response.text
    corps = response.json()
    assert set(corps) == {"erreur"}
    assert corps["erreur"]["code"] == code
    assert corps["erreur"]["message"]
    if champ is not None:
        assert champ in {d["champ"] for d in corps["erreur"]["details"]}
    return corps["erreur"]


# =============================================================== S01 requête valide
@pytest.mark.exigence("EX04", "EX20")
def test_s01_requete_valide(client, demande):
    """S01 Requête valide : 200, probabilité dans [0, 1] et contrat de réponse complet."""
    r = client.post("/predict", json=demande)
    assert r.status_code == 200
    res = r.json()
    assert set(res) == CLES_REPONSE
    p = res["probabilite_defaut"]
    assert isinstance(p, float) and math.isfinite(p) and 0.0 <= p <= 1.0
    assert res["niveau_risque"] in {"faible", "modere", "eleve"}
    assert isinstance(res["alertes"], list)
    assert res["version_modele"] == "1.0.0"


# =============================================================== S02 champ manquant
@pytest.mark.exigence("EX06")
@pytest.mark.parametrize("champ", config.VARIABLES_ENTREE)
def test_s02_champ_obligatoire_absent(client, demande, champ):
    """S02 Requête sans champ obligatoire : 422 DONNEES_INVALIDES sur le champ absent."""
    del demande[champ]
    err = assert_erreur(client.post("/predict", json=demande), 422, "DONNEES_INVALIDES", champ)
    assert any(d["type"] == "missing" for d in err["details"])


# =============================================================== S03 âge négatif
@pytest.mark.exigence("EX01")
def test_s03_age_negatif(client, demande):
    """S03 Âge négatif : 422 sur le champ age."""
    demande["age"] = -5
    assert_erreur(client.post("/predict", json=demande), 422, "DONNEES_INVALIDES", "age")


# =============================================================== S04 revenu texte
@pytest.mark.exigence("EX02")
@pytest.mark.parametrize("revenu", ["250000", "deux cent mille", ""])
def test_s04_revenu_texte(client, demande, revenu):
    """S04 Revenu sous forme de texte (même numérique) : 422 sur revenu_mensuel."""
    demande["revenu_mensuel"] = revenu
    assert_erreur(client.post("/predict", json=demande), 422, "DONNEES_INVALIDES", "revenu_mensuel")


# =============================================================== S05 montant nul/négatif
@pytest.mark.exigence("EX08")
@pytest.mark.parametrize("montant", [0, -1000000])
def test_s05_montant_nul_ou_negatif(client, demande, montant):
    """S05 Montant nul ou négatif : 422 sur montant_credit."""
    demande["montant_credit"] = montant
    assert_erreur(client.post("/predict", json=demande), 422, "DONNEES_INVALIDES", "montant_credit")


# =============================================================== S06 durée non entière
@pytest.mark.exigence("EX03")
@pytest.mark.parametrize("duree", [12.5, 12.0, "12"])
def test_s06_duree_non_entiere(client, demande, duree):
    """S06 Durée non entière (12.5, 12.0, "12") : 422 sur duree_mois."""
    demande["duree_mois"] = duree
    assert_erreur(client.post("/predict", json=demande), 422, "DONNEES_INVALIDES", "duree_mois")


# =============================================================== S07 champs supplémentaires
@pytest.mark.exigence("EX09")
def test_s07_champ_supplementaire(client, demande):
    """S07 Champ non autorisé (ex. variable sensible) : 422 extra_forbidden."""
    demande["ethnie"] = "X"
    err = assert_erreur(client.post("/predict", json=demande), 422, "DONNEES_INVALIDES", "ethnie")
    assert err["details"][0]["type"] == "extra_forbidden"


# =============================================================== S08 valeurs extrêmes
@pytest.mark.exigence("EX08", "EX02")
@pytest.mark.parametrize(
    "champ,valeur",
    [
        ("montant_credit", 1e15),
        ("revenu_mensuel", 1e15),
        ("age", 10**12),
        ("duree_mois", 10**9),
    ],
)
def test_s08_valeurs_au_dela_des_plafonds_rejetees(client, demande, champ, valeur):
    """S08a Valeurs extrêmement élevées au-delà des plafonds : 422 (invalide)."""
    demande[champ] = valeur
    assert_erreur(client.post("/predict", json=demande), 422, "DONNEES_INVALIDES", champ)


@pytest.mark.exigence("EX14", "EX04")
def test_s08_valeurs_tres_elevees_mais_valides_signalees(client, demande):
    """S08b Valeurs très élevées mais sous les plafonds : 200 + alerte, pas de rejet."""
    demande.update(montant_credit=config.MONTANT_MAX, revenu_mensuel=config.REVENU_MAX)
    r = client.post("/predict", json=demande)
    assert r.status_code == 200
    res = r.json()
    assert 0.0 <= res["probabilite_defaut"] <= 1.0
    assert "hors_domaine:montant_credit" in res["alertes"]
    assert "hors_domaine:revenu_mensuel" in res["alertes"]
    assert res["analyse_complementaire_requise"] is True
    # Anomalie A03 (corrigée) : pas d'avis « favorable » sur un dossier hors domaine
    assert "favorable" not in res["recommandation"].lower()
    assert "vérification manuelle" in res["recommandation"]


# =============================================================== S09 modèle indisponible
@pytest.mark.exigence("EX05")
def test_s09_predict_modele_indisponible(client, service_indisponible, demande):
    """S09 Modèle non chargé : POST /predict renvoie 503 MODELE_INDISPONIBLE."""
    assert_erreur(client.post("/predict", json=demande), 503, "MODELE_INDISPONIBLE")


@pytest.mark.exigence("EX05")
def test_s09_health_modele_indisponible(client, service_indisponible):
    """S09 Modèle non chargé : GET /health renvoie 503 et modele_charge=false."""
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json() == {"statut": "indisponible", "modele_charge": False}


@pytest.mark.exigence("EX05")
def test_s09_model_info_modele_indisponible(client, service_indisponible):
    """S09 Modèle non chargé : GET /model-info renvoie 503."""
    assert_erreur(client.get("/model-info"), 503, "MODELE_INDISPONIBLE")


@pytest.mark.exigence("EX05", "EX06")
def test_s09_validation_avant_disponibilite(client, service_indisponible):
    """S09b Requête invalide + modèle indisponible : la validation (422) prime."""
    assert client.post("/predict", json={}).status_code == 422


# =============================================================== S10 requête mal formée
@pytest.mark.exigence("EX11")
@pytest.mark.parametrize("corps", ['{"age": 35,', "{age: 35}", "nimporte quoi", '{"age": 35}}'])
def test_s10_json_mal_forme(client, corps):
    """S10 JSON syntaxiquement invalide : 400 REQUETE_MAL_FORMEE."""
    r = client.post("/predict", content=corps, headers={"content-type": "application/json"})
    assert_erreur(r, 400, "REQUETE_MAL_FORMEE")


@pytest.mark.exigence("EX11")
def test_s10_corps_absent(client):
    """S10 Corps vide : 400 REQUETE_MAL_FORMEE."""
    r = client.post("/predict", content=b"", headers={"content-type": "application/json"})
    assert_erreur(r, 400, "REQUETE_MAL_FORMEE")


@pytest.mark.exigence("EX11")
@pytest.mark.parametrize("corps", ["[]", "42", '"texte"', "null"])
def test_s10_json_valide_mais_pas_un_objet(client, corps):
    """S10 JSON valide qui n'est pas un objet : 422 DONNEES_INVALIDES."""
    r = client.post("/predict", content=corps, headers={"content-type": "application/json"})
    assert r.status_code in (400, 422)
    assert r.json()["erreur"]["code"] in {"DONNEES_INVALIDES", "REQUETE_MAL_FORMEE"}


@pytest.mark.exigence("EX11")
def test_s10_mauvais_content_type(client):
    """S10 Content-Type non JSON : 415 TYPE_CONTENU_NON_SUPPORTE."""
    r = client.post("/predict", content="age=35", headers={"content-type": "text/plain"})
    assert_erreur(r, 415, "TYPE_CONTENU_NON_SUPPORTE")


@pytest.mark.exigence("EX11")
def test_s10_corps_trop_volumineux(client, demande):
    """S10 Corps > 10 ko : 413 REQUETE_TROP_VOLUMINEUSE (protection simple)."""
    demande["commentaire"] = "x" * 20_000
    assert_erreur(client.post("/predict", json=demande), 413, "REQUETE_TROP_VOLUMINEUSE")


@pytest.mark.exigence("EX11")
def test_methode_non_autorisee(client):
    """TA01 GET /predict n'est pas autorisé : 405."""
    assert client.get("/predict").status_code == 405


# =============================================================== /health et /model-info
@pytest.mark.exigence("EX05")
def test_health_ok(client):
    """TA02 Service disponible : GET /health renvoie 200 et la version chargée."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"statut": "ok", "modele_charge": True, "version_modele": "1.0.0"}


@pytest.mark.exigence("EX16")
def test_model_info_contrat(client):
    """TA03 GET /model-info expose version, empreinte, variables, seuils et métriques."""
    r = client.get("/model-info")
    assert r.status_code == 200
    info = r.json()
    for cle in (
        "nom",
        "version",
        "algorithme",
        "date_entrainement",
        "sha256",
        "variables_entree",
        "variables_modele",
        "seuils_risque",
        "metriques_test",
    ):
        assert info.get(cle) is not None, cle
    assert info["variables_entree"] == list(config.VARIABLES_ENTREE)
    assert len(info["sha256"]) == 64
    assert "synthétique" in info["donnees"]["avertissement"].lower()


# =============================================================== interprétation
@pytest.mark.exigence("EX20")
@pytest.mark.parametrize(
    "p,niveau",
    [
        (0.0, "faible"),
        (0.1999, "faible"),
        (0.20, "modere"),
        (0.4999, "modere"),
        (0.50, "eleve"),
        (1.0, "eleve"),
    ],
)
def test_niveau_de_risque_selon_seuils(p, niveau):
    """TA04 Le niveau de risque respecte les seuils documentés (bornes incluses)."""
    from app.prediction import niveau_risque

    assert niveau_risque(p) == niveau


@pytest.mark.exigence("EX20")
def test_risque_eleve_exige_analyse(client, demande):
    """TA05 Une demande à risque élevé exige une analyse complémentaire."""
    demande.update(
        montant_credit=20_000_000,
        duree_mois=3,
        revenu_mensuel=50_000,
        age=22,
        anciennete_activite=0,
    )
    res = client.post("/predict", json=demande).json()
    assert res["niveau_risque"] == "eleve"
    assert res["analyse_complementaire_requise"] is True


@pytest.mark.exigence("EX11")
def test_content_length_invalide(client):
    """TA06 En-tête Content-Length non numérique : 400 REQUETE_MAL_FORMEE."""
    r = client.post(
        "/predict",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": "abc"},
    )
    assert_erreur(r, 400, "REQUETE_MAL_FORMEE")
