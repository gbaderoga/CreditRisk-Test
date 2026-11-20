"""Tests de non-régression du logiciel et du modèle par rapport à la baseline v1.0.0.

S'exécutent à chaque Pull Request (GitHub Actions) sans réentraînement complet : ils
s'appuient sur le modèle versionné models/model_v1.joblib et la baseline reports/baseline/.
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import pytest

from app import config
from app.prediction import ServiceModele, empreinte_sha256
from app.preprocessing import transformer
from app.validation import valider_demande
from scripts import entrainement as ent
from scripts import non_regression as nr


@pytest.fixture(scope="module")
def tolerances():
    return nr.charger_tolerances()


@pytest.fixture(scope="module")
def baseline():
    return nr.charger_baseline()


@pytest.fixture(scope="module")
def jeu_test():
    return pd.read_csv(config.RACINE / "data" / "test.csv")


@pytest.fixture(scope="module")
def metriques_courantes(service_charge, jeu_test):
    p = service_charge.predire_probabilites(ent.matrice(jeu_test))
    return ent.evaluer(p, jeu_test["defaut"].to_numpy())


# ===================================================================== baseline et tolérances
@pytest.mark.exigence("EX07")
def test_tolerances_definies_avant_comparaison(tolerances):
    """TN01 Le fichier de tolérances existe, est daté et couvre rappel, F1 et ROC-AUC."""
    assert tolerances["date_fixation"]
    assert {"rappel", "f1", "roc_auc"} <= set(tolerances["metriques"])
    for regle in tolerances["metriques"].values():
        assert 0 < regle["baisse_max"] < 0.1


@pytest.mark.exigence("EX07", "EX16")
def test_modele_courant_identifie(baseline, service_charge):
    """TN02 Le modèle versionné est identifié : si son empreinte change, la baseline aussi."""
    sha = empreinte_sha256(config.CHEMIN_MODELE)
    if sha == baseline["sha256"]:
        assert service_charge.metadonnees["version"] == baseline["version"]
    else:  # nouvelle version : la comparaison métrique ci-dessous devient décisive
        assert service_charge.metadonnees["version"] != baseline["version"], (
            "Le fichier modèle a changé sans changement de version"
        )


# ===================================================================== contrat de sortie
@pytest.mark.exigence("EX04", "EX07")
def test_sorties_du_pipeline_conformes_au_contrat(service_charge, jeu_test):
    """TN03 Sur 500 demandes réelles du jeu de test, chaque sortie respecte le contrat."""
    for d in jeu_test.drop(columns="defaut").head(500).to_dict("records"):
        res = service_charge.predire(
            valider_demande(
                {k: (int(v) if k in ("age", "duree_mois") else float(v)) for k, v in d.items()}
            )
        )
        assert 0.0 <= res["probabilite_defaut"] <= 1.0
        assert res["niveau_risque"] in {"faible", "modere", "eleve"}
        assert isinstance(res["alertes"], list)
        assert res["version_modele"]


# ===================================================================== métriques
@pytest.mark.exigence("EX07")
@pytest.mark.parametrize("metrique", ["rappel", "f1", "roc_auc", "pr_auc", "precision"])
def test_pas_de_regression_des_metriques(metrique, metriques_courantes, baseline, tolerances):
    """TN04 Chaque métrique reste dans la tolérance de baisse et au-dessus de son plancher."""
    ref = baseline["metriques_test"][metrique]
    cour = metriques_courantes[metrique]
    regle = tolerances["metriques"][metrique]
    assert ref - cour <= regle["baisse_max"], f"{metrique} : {ref} → {cour}"
    assert cour >= regle["plancher"], f"{metrique} sous le plancher : {cour}"


@pytest.mark.exigence("EX07")
def test_rappel_et_f1_detectent_une_baisse_excessive(baseline, tolerances):
    """TN05 Le comparateur signale une baisse de rappel ou de F1 au-delà de la tolérance."""
    ref = baseline["metriques_test"]
    degrade = {**ref, "rappel": ref["rappel"] - 0.031, "f1": ref["f1"] - 0.031}
    statuts = {
        ligne["metrique"]: ligne["statut"]
        for ligne in nr.comparer_metriques(ref, degrade, tolerances)
    }
    assert statuts["rappel"] == "REGRESSION" and statuts["f1"] == "REGRESSION"
    limite = {**ref, "rappel": ref["rappel"] - 0.029}
    assert {
        ligne["metrique"]: ligne["statut"]
        for ligne in nr.comparer_metriques(ref, limite, tolerances)
    }["rappel"] == "OK"


@pytest.mark.exigence("EX07")
def test_candidate_degradee_rejetee(jeu_test, tolerances, baseline):
    """TN06 Un modèle réellement dégradé (étiquettes mélangées) est REJETÉ par le comparateur."""
    df = pd.read_csv(config.RACINE / "data" / "credit_synthetique.csv")
    train, _, _ = ent.partitionner(df)
    train = train.assign(defaut=np.random.default_rng(0).permutation(train["defaut"].to_numpy()))
    p = ent.entrainer(train).predict_proba(ent.matrice(jeu_test))[:, 1]
    m = ent.evaluer(p, jeu_test["defaut"].to_numpy())
    lignes = nr.comparer_metriques(baseline["metriques_test"], m, tolerances)
    assert nr.decision(lignes, {"statut": "OK"}) == "REJETEE"


# ===================================================================== prédictions de référence
@pytest.mark.exigence("EX07", "EX15")
def test_predictions_de_reference(service_charge, baseline, tolerances):
    """TN07 Les 200 probabilités de référence sont reproduites (tolérance selon la version)."""
    ref = nr.charger_reference()
    p = service_charge.predire_probabilites(
        transformer(ref[list(config.VARIABLES_ENTREE)].to_dict("records"))
    )
    meme = empreinte_sha256(config.CHEMIN_MODELE) == baseline["sha256"]
    res = nr.comparer_probabilites(ref["probabilite_defaut"].to_numpy(), p, tolerances, meme)
    assert res["statut"] == "OK", res


# ===================================================================== sauvegarde / rechargement
@pytest.mark.exigence("EX15")
def test_coherence_apres_sauvegarde_et_rechargement(service_charge, jeu_test, tmp_path, tolerances):
    """TN08 Modèle sauvegardé puis rechargé : probabilités identiques (≤ 1e-12) sur 4 000 cas."""
    X = ent.matrice(jeu_test)
    avant = service_charge.predire_probabilites(X)
    chemin = tmp_path / "modele.joblib"
    joblib.dump(service_charge.bundle, chemin)
    recharge = joblib.load(chemin)["pipeline"].predict_proba(X)[:, 1]
    assert np.max(np.abs(avant - recharge)) <= tolerances["sauvegarde_rechargement"]["ecart_max"]


@pytest.mark.exigence("EX15")
def test_cycle_complet_entrainement_sauvegarde_service(tmp_path, jeu_test, monkeypatch):
    """TN09 Entraîner → sauvegarder (avec SHA-256) → charger via le service → même résultat."""
    df = pd.read_csv(config.RACINE / "data" / "credit_synthetique.csv")
    train, _, _ = ent.partitionner(df)
    pipeline = ent.entrainer(train, C=0.01)
    chemin = tmp_path / "model_test.joblib"
    ent.sauvegarder(pipeline, train, chemin, "test", {}, {"C": 0.01})
    svc = ServiceModele()
    svc.charger(chemin)
    X = ent.matrice(jeu_test.head(100))
    np.testing.assert_allclose(
        svc.predire_probabilites(X), pipeline.predict_proba(X)[:, 1], atol=1e-12
    )


@pytest.mark.exigence("EX15")
def test_entrainement_reproductible():
    """TN10 Deux entraînements avec la même graine donnent des coefficients identiques."""
    df = ent.generer_donnees(n=3000)
    assert df.equals(ent.generer_donnees(n=3000))
    train, _, _ = ent.partitionner(df)
    a, b = ent.entrainer(train), ent.entrainer(train)
    np.testing.assert_array_equal(a[-1].coef_, b[-1].coef_)
