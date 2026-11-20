"""Comparaison d'une version candidate du système à la version de référence (v1.0.0).

Usage :
    python -m scripts.non_regression     # compare v1 à 4 candidates et écrit le rapport

Les tolérances sont lues dans reports/baseline/tolerances.json, fichier figé AVANT toute
comparaison (règle du sujet). Deux familles de critères :
* métriques sur le jeu de test versionné (bloquant) ;
* écarts de probabilité sur 200 demandes de référence (bloquant au-delà du seuil
  d'investigation).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app import config

BASE = config.RACINE / "reports" / "baseline"


def charger_tolerances() -> dict[str, Any]:
    return json.loads((BASE / "tolerances.json").read_text(encoding="utf-8"))


def charger_baseline() -> dict[str, Any]:
    return json.loads((BASE / "metriques_v1.json").read_text(encoding="utf-8"))


def charger_reference() -> pd.DataFrame:
    return pd.read_csv(BASE / "predictions_reference_v1.csv")


def comparer_metriques(reference: dict, candidate: dict, tolerances: dict) -> list[dict]:
    """Pour chaque métrique suivie : baisse observée vs baisse maximale tolérée."""
    lignes = []
    for metrique, regle in tolerances["metriques"].items():
        ref, cand = reference[metrique], candidate[metrique]
        baisse = ref - cand
        statut = "OK"
        if baisse > regle["baisse_max"]:
            statut = "REGRESSION"
        elif cand < regle.get("plancher", -np.inf):
            statut = "SOUS_PLANCHER"
        lignes.append(
            {
                "metrique": metrique,
                "reference": ref,
                "candidate": cand,
                "variation": round(cand - ref, 6),
                "baisse_max": regle["baisse_max"],
                "plancher": regle.get("plancher"),
                "statut": statut,
            }
        )
    return lignes


def comparer_probabilites(
    p_ref: np.ndarray, p_cand: np.ndarray, tolerances: dict, meme_modele: bool
) -> dict:
    ecart = np.abs(np.asarray(p_cand) - np.asarray(p_ref))
    regle = tolerances["probabilites"]["meme_modele" if meme_modele else "nouvelle_version"]
    max_, moy = float(ecart.max()), float(ecart.mean())
    ok = max_ <= regle["ecart_max"] and moy <= regle["ecart_moyen_max"]
    return {
        "ecart_max": max_,
        "ecart_moyen": moy,
        "regle": regle,
        "statut": "OK" if ok else "INVESTIGATION",
    }


def decision(lignes: list[dict], probas: dict) -> str:
    if any(ligne["statut"] != "OK" for ligne in lignes):
        return "REJETEE"
    if probas["statut"] != "OK":
        return "A_INVESTIGUER"
    return "ACCEPTEE"


# ----------------------------------------------------------------------------- campagne
def main() -> None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    import app.preprocessing as pre
    from app.prediction import ServiceModele
    from scripts import entrainement as ent

    tol = charger_tolerances()
    baseline = charger_baseline()["metriques_test"]
    ref = charger_reference()
    df = pd.read_csv(config.RACINE / "data" / "credit_synthetique.csv")
    train, _, _ = ent.partitionner(df)
    test = pd.read_csv(config.RACINE / "data" / "test.csv")
    y = test["defaut"].to_numpy()
    X_ref_brut = ref[list(config.VARIABLES_ENTREE)]

    svc = ServiceModele()
    svc.charger(config.CHEMIN_MODELE)
    pipeline_v1 = svc.bundle["pipeline"]

    def scorer(pipeline, transfo=ent.matrice):
        return (
            pipeline.predict_proba(transfo(test))[:, 1],
            pipeline.predict_proba(transfo(X_ref_brut))[:, 1],
        )

    candidats: dict[str, dict] = {}

    # C0 : v1 rechargée depuis le disque (contrôle : doit être strictement identique)
    candidats["C0 v1.0.0 rechargée (contrôle)"] = dict(
        zip(("p_test", "p_ref"), scorer(pipeline_v1), strict=True),
        meme_modele=True,
        description="Même fichier modèle, rechargé : contrôle du déterminisme.",
    )

    # C1 : réentraînement avec une régularisation différente (évolution légitime)
    p1 = ent.entrainer(train, C=1.0)
    candidats["C1 v1.1.0 réentraînée C=1,0"] = dict(
        zip(("p_test", "p_ref"), scorer(p1), strict=True),
        meme_modele=False,
        description="Hyperparamètre C passé de 0,01 à 1,0, mêmes données.",
    )

    # C2 : régression de CODE — mensualité calculée en années au lieu de mois
    def construire_bug(d):
        v = original(d)
        mensualite_fausse = d["montant_credit"] / (d["duree_mois"] * 12)
        v["log_taux_endettement"] = float(np.log1p(mensualite_fausse / d["revenu_mensuel"]))
        return v

    original = pre.construire_variables
    try:
        pre.construire_variables = construire_bug
        candidats["C2 v1.2.0 bug de prétraitement"] = dict(
            zip(("p_test", "p_ref"), scorer(pipeline_v1), strict=True),
            meme_modele=False,
            description="Modèle v1 inchangé, mais le code calcule la mensualité "
            "sur la durée en années (montant / (mois × 12)).",
        )
    finally:
        pre.construire_variables = original

    # C3 : régression de MODÈLE — étiquettes d'entraînement bruitées à 30 %
    rng = np.random.default_rng(7)
    bruit = train.copy()
    masque = rng.random(len(bruit)) < 0.30
    bruit.loc[masque, "defaut"] = rng.integers(0, 2, masque.sum())
    p3 = Pipeline(
        [
            ("standardisation", StandardScaler()),
            ("classifieur", LogisticRegression(C=0.01, max_iter=1000)),
        ]
    )
    p3.fit(ent.matrice(bruit), bruit["defaut"].to_numpy())
    candidats["C3 v2.0.0 données d'entraînement dégradées"] = dict(
        zip(("p_test", "p_ref"), scorer(p3), strict=True),
        meme_modele=False,
        description="30 % des étiquettes d'entraînement remplacées au hasard "
        "(simule un défaut de qualité des données).",
    )

    resultats = {}
    for nom, c in candidats.items():
        m = ent.evaluer(c["p_test"], y)
        lignes = comparer_metriques(baseline, m, tol)
        probas = comparer_probabilites(
            ref["probabilite_defaut"].to_numpy(), c["p_ref"], tol, c["meme_modele"]
        )
        resultats[nom] = {
            "description": c["description"],
            "metriques": m,
            "comparaison": lignes,
            "probabilites": probas,
            "decision": decision(lignes, probas),
        }

    sortie = config.RACINE / "reports" / "resultats"
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "non_regression.json").write_text(
        json.dumps(resultats, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    ecrire_rapport(resultats, tol, baseline, sortie.parent / "05_rapport_non_regression.md")
    for nom, r in resultats.items():
        print(f"{nom:45s} → {r['decision']}")


def _f(x, n=3):
    return "—" if x is None else f"{x:.{n}f}".replace(".", ",")


def _e(x):
    return f"{x:.2e}".replace(".", ",")


def ecrire_rapport(resultats: dict, tol: dict, baseline: dict, chemin: Path) -> None:
    L = [
        "# Rapport de non-régression",
        "",
        "*Généré par `python -m scripts.non_regression`. Ne pas modifier à la main.*",
        "",
        "## 1. Version de référence",
        "",
        f"Modèle **v1.0.0** (`models/model_v1.joblib`), baseline figée dans "
        f"`reports/baseline/` : métriques sur `data/test.csv` (n = {baseline['n']}, "
        f"taux de défaut {_f(baseline['taux_defaut'] * 100, 1)} %) et 200 prédictions de "
        f"référence. Seuil de classification : probabilité ≥ {_f(baseline['seuil'], 2)} "
        "(au moins « risque modéré »).",
        "",
        "## 2. Tolérances (fixées avant la comparaison)",
        "",
        f"Fichier `reports/baseline/tolerances.json`, daté du {tol['date_fixation']}.",
        "",
        "| Métrique | Baisse maximale tolérée | Plancher absolu |",
        "|---|---:|---:|",
    ]
    for k, v in tol["metriques"].items():
        L.append(f"| {k} | {_f(v['baisse_max'])} | {_f(v.get('plancher'))} |")
    pm, pn = tol["probabilites"]["meme_modele"], tol["probabilites"]["nouvelle_version"]
    L += [
        "",
        "| Écart de probabilité (200 demandes de référence) | Max | Moyen |",
        "|---|---:|---:|",
        f"| Même modèle (rechargement) | {pm['ecart_max']:.0e} | {pm['ecart_moyen_max']:.0e} |",
        f"| Nouvelle version | {_f(pn['ecart_max'], 2)} | {_f(pn['ecart_moyen_max'], 2)} |",
        "",
        "Règle de décision : une métrique en régression ou sous plancher → **REJETÉE** ; "
        "métriques conformes mais écarts de probabilité au-delà de la tolérance → "
        "**À INVESTIGUER** ; sinon **ACCEPTÉE**.",
        "",
        "## 3. Synthèse",
        "",
        "| Candidate | Rappel | F1 | ROC-AUC | Écart max p | Décision |",
        "|---|---:|---:|---:|---:|---|",
        f"| Référence v1.0.0 | {_f(baseline['rappel'])} | {_f(baseline['f1'])} | "
        f"{_f(baseline['roc_auc'])} | — | — |",
    ]
    for nom, r in resultats.items():
        m = r["metriques"]
        L.append(
            f"| {nom} | {_f(m['rappel'])} | {_f(m['f1'])} | {_f(m['roc_auc'])} | "
            f"{_e(r['probabilites']['ecart_max'])} | **{r['decision']}** |"
        )
    L += ["", "## 4. Détail par candidate", ""]
    for nom, r in resultats.items():
        L += [
            f"### {nom}",
            "",
            r["description"],
            "",
            "| Métrique | Référence | Candidate | Variation | Statut |",
            "|---|---:|---:|---:|---|",
        ]
        for c in r["comparaison"]:
            L.append(
                f"| {c['metrique']} | {_f(c['reference'])} | {_f(c['candidate'])} | "
                f"{c['variation']:+.3f}".replace(".", ",")
                + f" | {c['statut']} |"
            )
        p = r["probabilites"]
        mc = r["metriques"]["matrice_confusion"]
        L += [
            "",
            f"Matrice de confusion (TN / FP / FN / TP) : {mc['tn']} / {mc['fp']} / "
            f"{mc['fn']} / {mc['tp']}. Écart de probabilité : max {_e(p['ecart_max'])}, "
            f"moyen {_e(p['ecart_moyen'])} → {p['statut']}.",
            "",
            f"**Décision : {r['decision']}**",
            "",
        ]
    chemin.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
