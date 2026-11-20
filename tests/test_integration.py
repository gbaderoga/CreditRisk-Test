"""Tests d'intégration : validation → prétraitement → modèle → API, et pannes du pipeline.

Les pannes sont injectées avec monkeypatch au point de jonction entre deux composants ;
on vérifie ensuite que l'API renvoie une erreur propre, sans trace technique.
"""

from __future__ import annotations

import json
import math

import joblib
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import config, prediction
from app.main import app, service
from app.prediction import (
    ErreurModeleIndisponible,
    ErreurPrediction,
    ServiceModele,
    empreinte_sha256,
)
from app.preprocessing import VARIABLES_MODELE, transformer
from app.validation import DemandeCredit

MOTS_INTERDITS = (
    "Traceback",
    'File "',
    "/home",
    "site-packages",
    ".py",
    "Error(",
    "RuntimeError",
    "secret",
)


def assert_sans_trace(response):
    texte = response.text
    for mot in MOTS_INTERDITS:
        assert mot not in texte, f"fuite d'information : {mot!r} dans {texte}"


# ============================================================ scénario principal
@pytest.mark.exigence("EX04", "EX16", "EX21")
def test_pipeline_bout_en_bout(client, demande, monkeypatch):
    """TI01 Requête valide : chaque composant est appelé dans l'ordre et la sortie est exacte."""
    appels = []
    vrai_transformer = prediction.transformer

    def espion_transformer(demandes):
        demandes = list(demandes)
        appels.append(("pretraitement", demandes))
        return vrai_transformer(demandes)

    vrai_predire = ServiceModele.predire_probabilites

    def espion_predire(self, X):
        appels.append(("modele", X.copy()))
        return vrai_predire(self, X)

    monkeypatch.setattr(prediction, "transformer", espion_transformer)
    monkeypatch.setattr(ServiceModele, "predire_probabilites", espion_predire)

    r = client.post("/predict", json=demande)
    assert r.status_code == 200

    # 1. validation : le prétraitement reçoit un objet DemandeCredit déjà validé
    assert [a[0] for a in appels] == ["pretraitement", "modele"]
    (recu,) = appels[0][1]
    assert isinstance(recu, DemandeCredit)
    # 2. transformation : vecteur attendu, dans l'ordre documenté
    X = appels[1][1]
    assert X.shape == (1, len(VARIABLES_MODELE))
    attendu = [
        35,
        math.log(250_000),
        math.log(1_000_000),
        12,
        4,
        math.log1p(1_000_000 / 12 / 250_000),
    ]
    np.testing.assert_allclose(X[0], attendu, rtol=1e-12)
    # 3. prédiction : identique à un appel direct du pipeline scikit-learn
    bundle = joblib.load(config.CHEMIN_MODELE)
    p_direct = bundle["pipeline"].predict_proba(X)[0, 1]
    assert r.json()["probabilite_defaut"] == pytest.approx(p_direct, abs=1e-6)


@pytest.mark.exigence("EX16")
def test_metadonnees_coherentes_avec_le_modele_charge(client, demande):
    """TI02 Version et empreinte cohérentes entre fichier, /model-info, /health et /predict."""
    info = client.get("/model-info").json()
    meta = json.loads(config.CHEMIN_MODELE.with_suffix(".json").read_text(encoding="utf-8"))
    assert info["sha256"] == empreinte_sha256(config.CHEMIN_MODELE) == meta["sha256"]
    assert info["version"] == meta["version"]
    assert client.get("/health").json()["version_modele"] == info["version"]
    assert client.post("/predict", json=demande).json()["version_modele"] == info["version"]
    assert info["variables_modele"] == list(VARIABLES_MODELE)
    n_attendu = joblib.load(config.CHEMIN_MODELE)["pipeline"].n_features_in_
    assert n_attendu == len(info["variables_modele"])


@pytest.mark.exigence("EX04", "EX15")
def test_prediction_par_lot_identique_a_l_unitaire(service_charge):
    """TI03 Prédire 50 demandes en lot ou une par une donne les mêmes probabilités."""
    import pandas as pd

    df = pd.read_csv(config.RACINE / "data" / "test.csv").head(50)
    demandes = df[list(config.VARIABLES_ENTREE)].to_dict("records")
    lot = service_charge.predire_probabilites(transformer(demandes))
    unitaire = [service_charge.predire_probabilites(transformer([d]))[0] for d in demandes]
    np.testing.assert_allclose(lot, unitaire, atol=1e-12)


# ============================================================ le modèle ne peut pas être chargé
@pytest.mark.exigence("EX05", "EX17")
def test_fichier_modele_absent(tmp_path):
    """TI04 Fichier modèle absent : ErreurModeleIndisponible avec message explicite."""
    svc = ServiceModele()
    with pytest.raises(ErreurModeleIndisponible, match="introuvable"):
        svc.charger(tmp_path / "absent.joblib")
    assert not svc.est_disponible


@pytest.mark.exigence("EX05", "EX17")
def test_metadonnees_absentes(copie_modele):
    """TI05 Métadonnées absentes : le modèle n'est pas chargé."""
    copie_modele.with_suffix(".json").unlink()
    with pytest.raises(ErreurModeleIndisponible, match="métadonnées"):
        ServiceModele().charger(copie_modele)


@pytest.mark.exigence("EX17")
def test_modele_altere_refuse_avant_deserialisation(copie_modele, monkeypatch):
    """TI06 Fichier modifié (SHA-256 différent) : refusé SANS appeler joblib.load."""
    with open(copie_modele, "ab") as f:
        f.write(b"\x00")
    appele = []
    monkeypatch.setattr(prediction.joblib, "load", lambda *a, **k: appele.append(1))
    with pytest.raises(ErreurModeleIndisponible, match="SHA-256"):
        ServiceModele().charger(copie_modele)
    assert appele == []


@pytest.mark.exigence("EX05", "EX17")
def test_modele_corrompu(copie_modele):
    """TI07 Fichier illisible mais empreinte cohérente : erreur contrôlée, pas d'exception brute."""
    copie_modele.write_bytes(b"pas un modele joblib")
    meta_path = copie_modele.with_suffix(".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["sha256"] = empreinte_sha256(copie_modele)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ErreurModeleIndisponible, match="illisible"):
        ServiceModele().charger(copie_modele)


@pytest.mark.exigence("EX05", "EX17")
@pytest.mark.parametrize(
    "contenu",
    [
        {"pas_de_pipeline": 1},
        "chaine",
    ],
)
def test_format_de_modele_inattendu(copie_modele, contenu):
    """TI08 Objet désérialisé au mauvais format : refusé."""
    joblib.dump(contenu, copie_modele)
    meta_path = copie_modele.with_suffix(".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["sha256"] = empreinte_sha256(copie_modele)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ErreurModeleIndisponible, match="format"):
        ServiceModele().charger(copie_modele)


@pytest.mark.exigence("EX05", "EX21")
def test_variables_du_modele_incompatibles_avec_le_code(copie_modele):
    """TI09 Modèle entraîné avec d'autres variables que le code : refusé au chargement."""
    bundle = joblib.load(copie_modele)
    bundle["variables"] = ("age", "revenu")
    joblib.dump(bundle, copie_modele)
    meta_path = copie_modele.with_suffix(".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["sha256"] = empreinte_sha256(copie_modele)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ErreurModeleIndisponible, match="variables"):
        ServiceModele().charger(copie_modele)


@pytest.mark.exigence("EX05")
def test_api_demarre_sans_modele_et_signale_503(tmp_path, monkeypatch, demande):
    """TI10 Au démarrage avec un modèle absent, l'API répond (503) au lieu de planter."""
    monkeypatch.setattr(config, "CHEMIN_MODELE", tmp_path / "absent.joblib")
    try:
        with TestClient(app) as c:
            assert c.get("/health").status_code == 503
            r = c.post("/predict", json=demande)
            assert r.status_code == 503
            assert_sans_trace(r)
            assert "absent.joblib" not in r.text
    finally:
        monkeypatch.undo()
        service.charger(config.CHEMIN_MODELE)


@pytest.mark.exigence("EX05")
def test_modele_decharge_en_cours_de_fonctionnement(client, demande):
    """TI11 Modèle déchargé à chaud : 503, puis 200 après rechargement."""
    service.decharger()
    assert client.post("/predict", json=demande).status_code == 503
    service.charger(config.CHEMIN_MODELE)
    assert client.post("/predict", json=demande).status_code == 200


# ============================================================ pannes pendant le traitement
@pytest.mark.exigence("EX12", "EX21")
def test_erreur_de_pretraitement(client, demande, monkeypatch):
    """TI12 Le prétraitement échoue : 500 ERREUR_INTERNE avec identifiant d'incident."""
    from app.preprocessing import ErreurPretraitement

    def panne(_):
        raise ErreurPretraitement("secret: colonne interne manquante")

    monkeypatch.setattr(prediction, "transformer", panne)
    r = client.post("/predict", json=demande)
    assert r.status_code == 500
    err = r.json()["erreur"]
    assert err["code"] == "ERREUR_INTERNE" and len(err["id_incident"]) == 12
    assert_sans_trace(r)


@pytest.mark.exigence("EX12", "EX21")
def test_variable_attendue_absente_apres_pretraitement(client, demande, monkeypatch):
    """TI13 Une variable disparaît entre validation et modèle : erreur 500 contrôlée."""
    import app.preprocessing as pre

    original = pre.construire_variables

    def amputee(d):
        v = original(d)
        del v["log_taux_endettement"]
        return v

    monkeypatch.setattr(pre, "construire_variables", amputee)
    r = client.post("/predict", json=demande)
    assert r.status_code == 500
    assert_sans_trace(r)


@pytest.mark.exigence("EX12", "EX21")
@pytest.mark.parametrize("forme", [(1, 5), (1, 7), (6,)])
def test_dimensions_incompatibles(client, demande, monkeypatch, forme):
    """TI14 Dimensions différentes de celles attendues par le modèle : 500 contrôlée."""
    monkeypatch.setattr(prediction, "transformer", lambda _: np.zeros(forme))
    r = client.post("/predict", json=demande)
    assert r.status_code == 500
    assert r.json()["erreur"]["code"] == "ERREUR_INTERNE"
    assert_sans_trace(r)


@pytest.mark.exigence("EX12")
def test_dimensions_incompatibles_niveau_service(service_charge):
    """TI15 Le service refuse explicitement une matrice de mauvaise largeur."""
    with pytest.raises(ErreurPrediction, match="dimensions"):
        service_charge.predire_probabilites(np.zeros((1, 4)))


class PipelineEnPanne:
    n_features_in_ = len(VARIABLES_MODELE)

    def __init__(self, sortie=None, exception=None):
        self.sortie, self.exception = sortie, exception

    def predict_proba(self, X):
        if self.exception:
            raise self.exception
        return self.sortie


@pytest.fixture
def pipeline_remplace(monkeypatch):
    def _remplacer(faux):
        monkeypatch.setitem(service.bundle, "pipeline", faux)

    return _remplacer


@pytest.mark.exigence("EX12")
def test_exception_interne_du_modele(client, demande, pipeline_remplace):
    """TI16 Le modèle lève une exception : 500 sans message, ni type, ni chemin."""
    pipeline_remplace(PipelineEnPanne(exception=RuntimeError("secret /home/app/model.py")))
    r = client.post("/predict", json=demande)
    assert r.status_code == 500
    assert_sans_trace(r)


@pytest.mark.exigence("EX04", "EX12")
@pytest.mark.parametrize(
    "sortie",
    [
        np.array([[0.0, 1.5]]),
        np.array([[0.0, -0.1]]),
        np.array([[0.0, np.nan]]),
        np.array([[0.0, np.inf]]),
    ],
)
def test_probabilite_aberrante_bloquee(client, demande, pipeline_remplace, sortie):
    """TI17 Une sortie du modèle hors [0, 1] ou non finie n'est jamais renvoyée au client."""
    pipeline_remplace(PipelineEnPanne(sortie=sortie))
    r = client.post("/predict", json=demande)
    assert r.status_code == 500
    assert "probabilite_defaut" not in r.text


@pytest.mark.exigence("EX12")
def test_erreur_imprevue_attrapee_par_le_gestionnaire_global(
    client_sans_exception, demande, monkeypatch
):
    """TI18 Exception non prévue (ZeroDivisionError) : 500 générique, pas de trace."""

    def panne(self, d):
        return 1 / 0

    monkeypatch.setattr(ServiceModele, "alertes", panne)
    r = client_sans_exception.post("/predict", json=demande)
    assert r.status_code == 500
    assert r.json()["erreur"]["code"] == "ERREUR_INTERNE"
    assert "ZeroDivision" not in r.text
    assert_sans_trace(r)
