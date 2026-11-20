"""Génération des données synthétiques, entraînement et évaluation du modèle.

Usage :
    python -m scripts.entrainement            # régénère data/, models/model_v1.*, la baseline

AVERTISSEMENT : les données sont SYNTHÉTIQUES. Elles servent à tester le système logiciel
(contrat, pipeline, non-régression) et ne permettent PAS de démontrer la performance réelle
d'un modèle de crédit. Le processus de génération est documenté dans data/README.md.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app import config
from app.prediction import empreinte_sha256
from app.preprocessing import VARIABLES_MODELE, transformer

RACINE = config.RACINE
GRAINE = 42
N_OBSERVATIONS = 20_000
SEUIL_CLASSIFICATION = config.SEUIL_RISQUE_MODERE  # "détecté" = au moins risque modéré


# ----------------------------------------------------------------------------- données
def generer_donnees(n: int = N_OBSERVATIONS, graine: int = GRAINE) -> pd.DataFrame:
    """Jeu synthétique : relation connue et documentée entre variables et défaut."""
    rng = np.random.default_rng(graine)
    age = rng.integers(18, 71, n)
    anciennete = np.minimum(age - 12, rng.gamma(2.0, 3.0, n)).round(1)
    revenu = np.clip(rng.lognormal(np.log(180_000), 0.6, n), 20_000, 5_000_000).round(-3)
    ratio = rng.lognormal(np.log(4.0), 0.7, n)
    montant = np.clip(revenu * ratio, 50_000, 100_000_000).round(-4)
    duree = rng.choice(
        [3, 6, 9, 12, 18, 24, 36, 48], n, p=[0.05, 0.15, 0.10, 0.30, 0.15, 0.15, 0.07, 0.03]
    )
    taux = (montant / duree) / revenu
    logit = (
        -1.9
        + 2.8 * (np.log1p(taux) - np.log1p(0.35))
        - 0.03 * (age - 38)
        - 0.12 * (anciennete - 4)
        + 0.015 * (duree - 12)
        - 0.30 * (np.log(revenu) - np.log(180_000))
    )
    defaut = rng.binomial(1, 1 / (1 + np.exp(-logit)))
    return pd.DataFrame(
        {
            "age": age.astype(int),
            "revenu_mensuel": revenu.astype(float),
            "montant_credit": montant.astype(float),
            "duree_mois": duree.astype(int),
            "anciennete_activite": anciennete.astype(float),
            "defaut": defaut.astype(int),
        }
    )


def partitionner(df: pd.DataFrame, graine: int = GRAINE):
    """60 / 20 / 20 stratifié sur la cible."""
    train, reste = train_test_split(df, test_size=0.4, stratify=df["defaut"], random_state=graine)
    val, test = train_test_split(
        reste, test_size=0.5, stratify=reste["defaut"], random_state=graine
    )
    return train.reset_index(drop=True), val.reset_index(drop=True), test.reset_index(drop=True)


def matrice(df: pd.DataFrame) -> np.ndarray:
    return transformer(df[list(config.VARIABLES_ENTREE)].to_dict("records"))


# ----------------------------------------------------------------------------- modèle
def entrainer(train: pd.DataFrame, C: float = 1.0, graine: int = GRAINE) -> Pipeline:
    pipeline = Pipeline(
        [
            ("standardisation", StandardScaler()),
            ("classifieur", LogisticRegression(C=C, max_iter=1000, random_state=graine)),
        ]
    )
    pipeline.fit(matrice(train), train["defaut"].to_numpy())
    return pipeline


def evaluer(proba: np.ndarray, y: np.ndarray, seuil: float = SEUIL_CLASSIFICATION) -> dict:
    pred = (proba >= seuil).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "seuil": seuil,
        "n": int(len(y)),
        "taux_defaut": round(float(y.mean()), 6),
        "rappel": round(float(recall_score(y, pred, zero_division=0)), 6),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 6),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 6),
        "roc_auc": round(float(roc_auc_score(y, proba)), 6),
        "pr_auc": round(float(average_precision_score(y, proba)), 6),
        "matrice_confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def domaine(train: pd.DataFrame) -> dict[str, list[float]]:
    """Domaine d'entraînement par variable brute : quantiles 0,5 % – 99,5 %."""
    return {
        v: [float(train[v].quantile(0.005)), float(train[v].quantile(0.995))]
        for v in config.VARIABLES_ENTREE
    }


def sauvegarder(
    pipeline: Pipeline,
    train: pd.DataFrame,
    chemin: Path,
    version: str,
    metriques: dict,
    hyperparametres: dict,
) -> dict:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    bundle = {"pipeline": pipeline, "variables": VARIABLES_MODELE, "domaine": domaine(train)}
    joblib.dump(bundle, chemin)
    meta = {
        "nom": "creditrisk-logreg",
        "version": version,
        "algorithme": "StandardScaler + LogisticRegression",
        "hyperparametres": hyperparametres,
        "date_entrainement": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": empreinte_sha256(chemin),
        "scikit_learn": sklearn.__version__,
        "variables_modele": list(VARIABLES_MODELE),
        "metriques_test": metriques,
        "donnees": {
            "source": "synthétique (scripts/entrainement.py, graine 42)",
            "avertissement": "Données synthétiques : ne démontrent pas la performance réelle.",
            "n_entrainement": int(len(train)),
        },
    }
    Path(chemin).with_suffix(".json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return meta


def main() -> None:
    df = generer_donnees()
    (RACINE / "data").mkdir(exist_ok=True)
    df.to_csv(RACINE / "data" / "credit_synthetique.csv", index=False)
    train, val, test = partitionner(df)
    test.to_csv(RACINE / "data" / "test.csv", index=False)

    # Choix de C sur la validation (PR-AUC), jamais sur le test.
    selection = {}
    for C in (0.01, 0.1, 1.0, 10.0):
        p = entrainer(train, C=C).predict_proba(matrice(val))[:, 1]
        selection[C] = evaluer(p, val["defaut"].to_numpy())["pr_auc"]
    meilleur_C = max(selection, key=selection.get)

    pipeline = entrainer(train, C=meilleur_C)
    proba_test = pipeline.predict_proba(matrice(test))[:, 1]
    metriques = evaluer(proba_test, test["defaut"].to_numpy())
    meta = sauvegarder(
        pipeline,
        train,
        config.MODELE_PAR_DEFAUT,
        "1.0.0",
        metriques,
        {"C": meilleur_C, "selection_pr_auc_validation": selection},
    )

    # Baseline figée pour la non-régression : métriques + prédictions de référence.
    base = RACINE / "reports" / "baseline"
    base.mkdir(parents=True, exist_ok=True)
    (base / "metriques_v1.json").write_text(
        json.dumps(
            {"version": "1.0.0", "sha256": meta["sha256"], "metriques_test": metriques},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ref = test.drop(columns="defaut").head(200).copy()
    ref["probabilite_defaut"] = pipeline.predict_proba(matrice(ref))[:, 1]
    ref.to_csv(base / "predictions_reference_v1.csv", index=False, float_format="%.12f")

    print(json.dumps({"C": meilleur_C, "selection": selection, "test": metriques}, indent=2))


if __name__ == "__main__":
    main()
