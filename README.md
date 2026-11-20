# CreditRisk-Test

Qualification d'un système IA d'estimation du risque de défaut de remboursement pour une institution de microfinance : tests fonctionnels, d'intégration, de robustesse, de non-régression, de performance, et automatisation avec GitHub Actions.

> ⚠️ **Prototype pédagogique entraîné sur des données synthétiques** (`data/README.md`). Les tests démontrent la qualité **technique** du système. Ils ne démontrent pas que le modèle est performant sur de vrais emprunteurs, équitable, ni légalement utilisable pour une décision de crédit.

![tests](https://github.com/<UTILISATEUR>/CreditRisk-Test/actions/workflows/tests.yml/badge.svg)

## Résultats

| | |
|---|---|
| Tests | **291 réussis**, 0 échec, 1 anomalie connue (xfail strict), 1 test d'échec volontaire inactif. 102 fonctions, 293 cas, plus 600 entrées Hypothesis |
| Couverture `app/` | **100 %** (lignes et branches) |
| Ruff | Aucune erreur |
| Non-régression | 4 versions candidates : 2 acceptées, 2 rejetées (bug de prétraitement, données dégradées) |
| Performance | P95 de 3,97 ms (1 client), de 88 ms à 32 clients ; ≈ 450 req/s ; 0 erreur |
| Décision | **Logiciel qualifié. Pilote possible en mode observation uniquement**, sans usage décisionnel (`reports/RAPPORT_QUALIFICATION.md`) |

## Architecture

```
POST /predict ──► validation.py ──► preprocessing.py ──► prediction.py ──► réponse
  (JSON)          DemandeCredit      6 variables          Pipeline sklearn    probabilité
                  typage strict      dérivées             (scaler + logreg)   niveau de risque
                  bornes, extra      ordre fixe           SHA-256 vérifié     recommandation
                  NaN/inf refusés                         domaine → alertes   alertes
```

| Fichier | Rôle |
|---|---|
| `app/config.py` | Bornes métier, seuils de risque, chemin du modèle (une seule source de vérité) |
| `app/validation.py` | Contrat d'entrée pydantic : `extra="forbid"`, `strict=True`, `allow_inf_nan=False`, cohérence âge / ancienneté |
| `app/preprocessing.py` | `log(revenu)`, `log(montant)`, `log(1 + mensualité / revenu)`, etc. |
| `app/prediction.py` | Chargement sécurisé (SHA-256 vérifiée avant `joblib.load`), contrôle des dimensions et de la sortie, interprétation, alertes hors domaine |
| `app/main.py` | FastAPI : `/health`, `/predict`, `/model-info`, format d'erreur unique, aucune trace technique exposée |
| `scripts/entrainement.py` | Génération des données, entraînement, baseline |
| `scripts/non_regression.py` | Comparaison de versions candidates à la baseline |
| `scripts/benchmark.py`, `scripts/locustfile.py` | Mesures de performance |
| `scripts/rapports.py` | Tableau des résultats de tests par exigence |

## Contrat de l'API

```bash
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" \
  -d '{"age":35,"revenu_mensuel":250000,"montant_credit":1000000,"duree_mois":12,"anciennete_activite":4}'
```

```json
{"probabilite_defaut":0.123832,"niveau_risque":"faible",
 "recommandation":"Avis favorable : instruction standard du dossier.",
 "analyse_complementaire_requise":false,"alertes":[],"version_modele":"1.0.0"}
```

| Champ | Type | Bornes |
|---|---|---|
| `age` | entier | 18 à 75 |
| `revenu_mensuel` | nombre (FCFA) | > 0 et ≤ 100 000 000 |
| `montant_credit` | nombre (FCFA) | > 0 et ≤ 500 000 000 |
| `duree_mois` | entier | 1 à 120 |
| `anciennete_activite` | nombre (années) | 0 à 60, et ≤ âge − 12 |

Codes : 200, 400 (JSON invalide), 413 (> 10 ko), 415 (pas JSON), 422 (contrat non respecté), 500 (erreur interne, avec `id_incident`), 503 (modèle indisponible). Détails : `reports/03_tests_api_integration.md`. Documentation interactive : `http://127.0.0.1:8000/docs`.

## Exécution locale

Python 3.12 ou 3.13.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows : .venv\Scripts\activate
pip install -r requirements.txt

# Qualité
ruff check .
ruff format --check .

# Tests + couverture (comme en CI)
pytest --cov --cov-report=term-missing --cov-fail-under=95

# Une suite à la fois
pytest tests/test_api.py -v
pytest tests/test_robustness.py -v

# Démonstration : le test volontairement défaillant fait échouer pytest (code de sortie 1)
ECHEC_VOLONTAIRE=1 pytest                       # Windows PowerShell : $env:ECHEC_VOLONTAIRE=1; pytest

# Lancer l'API
uvicorn app.main:app --reload
```

### Régénérer les rapports

```bash
pytest --rapport-exigences=reports/resultats/resultats_tests.json && python -m scripts.rapports
python -m scripts.non_regression      # → reports/05_rapport_non_regression.md
python -m scripts.benchmark           # → reports/resultats/performance.json (≈ 1 min)

uvicorn app.main:app --port 8765 &
locust -f scripts/locustfile.py --host http://127.0.0.1:8765 --headless -u 50 -r 2 -t 45s \
       --csv reports/resultats/locust
```

`python -m scripts.entrainement` régénère les données, le modèle **et la baseline**. Ne le lancez que pour créer volontairement une nouvelle version de référence : changez alors la version dans le script et documentez la décision.

## Publier sur GitHub

```bash
git init -b main
git add .
git commit -m "Qualification CreditRisk v1.0.0"
git remote add origin https://github.com/<UTILISATEUR>/CreditRisk-Test.git
git push -u origin main
```

Puis suivre `reports/07_ci_github_actions.md` § 4 pour produire les preuves d'exécution (workflow vert, PR, échec volontaire rouge).

## Rapports (`reports/`)

| Fichier | Contenu |
|---|---|
| `01_plan_de_test.md` | Stratégie, matrice de traçabilité (22 exigences), risques, priorités, fiches de cas |
| `02_resultats_tests.md` | Résultats par suite, par exigence et par test (généré) |
| `03_tests_api_integration.md` | Contrat de l'API, scénarios S01–S10, intégration et pannes |
| `04_robustesse_anomalies.md` | Analyse des tests de robustesse, registre des anomalies |
| `05_rapport_non_regression.md` | Baseline contre 4 versions candidates (généré) |
| `06_rapport_performance.md` | Latence, P95, débit, montée en charge, configuration |
| `07_ci_github_actions.md` | Workflow, preuve d'échec, captures à produire |
| `RAPPORT_QUALIFICATION.md` | **Rapport final et décision** |
| `baseline/` | Référence figée v1.0.0 : métriques, prédictions, tolérances |
| `resultats/` | Sorties brutes : JSON, JUnit, CSV Locust |
