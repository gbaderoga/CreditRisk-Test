# Rapport de non-régression

*Généré par `python -m scripts.non_regression`. Ne pas modifier à la main.*

## 1. Version de référence

Modèle **v1.0.0** (`models/model_v1.joblib`), baseline figée dans `reports/baseline/` : métriques sur `data/test.csv` (n = 4000, taux de défaut 13,9 %) et 200 prédictions de référence. Seuil de classification : probabilité ≥ 0,20 (au moins « risque modéré »).

## 2. Tolérances (fixées avant la comparaison)

Fichier `reports/baseline/tolerances.json`, daté du 2026-11-20.

| Métrique | Baisse maximale tolérée | Plancher absolu |
|---|---:|---:|
| rappel | 0,030 | 0,400 |
| f1 | 0,030 | 0,350 |
| roc_auc | 0,020 | 0,700 |
| pr_auc | 0,030 | 0,330 |
| precision | 0,050 | 0,280 |

| Écart de probabilité (200 demandes de référence) | Max | Moyen |
|---|---:|---:|
| Même modèle (rechargement) | 1e-09 | 1e-09 |
| Nouvelle version | 0,10 | 0,02 |

Règle de décision : une métrique en régression ou sous plancher → **REJETÉE** ; métriques conformes mais écarts de probabilité au-delà de la tolérance → **À INVESTIGUER** ; sinon **ACCEPTÉE**.

## 3. Synthèse

| Candidate | Rappel | F1 | ROC-AUC | Écart max p | Décision |
|---|---:|---:|---:|---:|---|
| Référence v1.0.0 | 0,455 | 0,387 | 0,752 | — | — |
| C0 v1.0.0 rechargée (contrôle) | 0,455 | 0,387 | 0,752 | 5,00e-13 | **ACCEPTEE** |
| C1 v1.1.0 réentraînée C=1,0 | 0,458 | 0,387 | 0,752 | 6,82e-02 | **ACCEPTEE** |
| C2 v1.2.0 bug de prétraitement | 0,007 | 0,014 | 0,682 | 7,37e-01 | **REJETEE** |
| C3 v2.0.0 données d'entraînement dégradées | 0,933 | 0,289 | 0,751 | 1,62e-01 | **REJETEE** |

## 4. Détail par candidate

### C0 v1.0.0 rechargée (contrôle)

Même fichier modèle, rechargé : contrôle du déterminisme.

| Métrique | Référence | Candidate | Variation | Statut |
|---|---:|---:|---:|---|
| rappel | 0,455 | 0,455 | +0,000 | OK |
| f1 | 0,387 | 0,387 | +0,000 | OK |
| roc_auc | 0,752 | 0,752 | +0,000 | OK |
| pr_auc | 0,385 | 0,385 | +0,000 | OK |
| precision | 0,336 | 0,336 | +0,000 | OK |

Matrice de confusion (TN / FP / FN / TP) : 2949 / 497 / 302 / 252. Écart de probabilité : max 5,00e-13, moyen 2,63e-13 → OK.

**Décision : ACCEPTEE**

### C1 v1.1.0 réentraînée C=1,0

Hyperparamètre C passé de 0,01 à 1,0, mêmes données.

| Métrique | Référence | Candidate | Variation | Statut |
|---|---:|---:|---:|---|
| rappel | 0,455 | 0,458 | +0,004 | OK |
| f1 | 0,387 | 0,387 | +0,001 | OK |
| roc_auc | 0,752 | 0,752 | +0,000 | OK |
| pr_auc | 0,385 | 0,386 | +0,001 | OK |
| precision | 0,336 | 0,336 | -0,001 | OK |

Matrice de confusion (TN / FP / FN / TP) : 2943 / 503 / 300 / 254. Écart de probabilité : max 6,82e-02, moyen 8,91e-03 → OK.

**Décision : ACCEPTEE**

### C2 v1.2.0 bug de prétraitement

Modèle v1 inchangé, mais le code calcule la mensualité sur la durée en années (montant / (mois × 12)).

| Métrique | Référence | Candidate | Variation | Statut |
|---|---:|---:|---:|---|
| rappel | 0,455 | 0,007 | -0,448 | REGRESSION |
| f1 | 0,387 | 0,014 | -0,373 | REGRESSION |
| roc_auc | 0,752 | 0,682 | -0,069 | REGRESSION |
| pr_auc | 0,385 | 0,254 | -0,131 | REGRESSION |
| precision | 0,336 | 0,250 | -0,086 | REGRESSION |

Matrice de confusion (TN / FP / FN / TP) : 3434 / 12 / 550 / 4. Écart de probabilité : max 7,37e-01, moyen 7,84e-02 → INVESTIGATION.

**Décision : REJETEE**

### C3 v2.0.0 données d'entraînement dégradées

30 % des étiquettes d'entraînement remplacées au hasard (simule un défaut de qualité des données).

| Métrique | Référence | Candidate | Variation | Statut |
|---|---:|---:|---:|---|
| rappel | 0,455 | 0,933 | +0,478 | OK |
| f1 | 0,387 | 0,289 | -0,098 | REGRESSION |
| roc_auc | 0,752 | 0,751 | -0,000 | OK |
| pr_auc | 0,385 | 0,385 | +0,000 | OK |
| precision | 0,336 | 0,171 | -0,165 | REGRESSION |

Matrice de confusion (TN / FP / FN / TP) : 939 / 2507 / 37 / 517. Écart de probabilité : max 1,62e-01, moyen 1,20e-01 → INVESTIGATION.

**Décision : REJETEE**
