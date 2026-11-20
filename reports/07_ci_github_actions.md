# Automatisation : GitHub Actions

Workflow : `.github/workflows/tests.yml`.

## 1. Déclencheurs et étapes

| Déclencheur | Usage |
|---|---|
| `pull_request` | **Chaque Pull Request** : bloque la fusion si une étape échoue (à activer dans les règles de protection de `main`) |
| `push` sur `main` | Revalide la branche principale après fusion |
| `workflow_dispatch` (case à cocher `echec_volontaire`) | Démonstration : active le test volontairement défaillant |

```
qualite (Ruff)
  ├─ ruff check  (lint : pycodestyle, pyflakes, isort, bugbear, pyupgrade, simplify, pep8-naming, pylint)
  └─ ruff format --check
        │ needs
        ▼
tests (matrice Python 3.12 et 3.13, runner ubuntu-latest CPU)
  ├─ pip install -r requirements.txt   (versions figées, cache pip)
  ├─ vérification SHA-256 du modèle versionné
  ├─ pytest --cov --cov-fail-under=95 --junitxml --rapport-exigences
  ├─ résumé dans l'onglet Summary : nombre de tests, couverture, tableau par exigence
  └─ artefact « preuves-python-X.Y » : junit.xml, coverage.xml, resultats_tests_ci.json
```

Choix effectués :

* **Pas de réentraînement en CI**. Les tests s'appuient sur `models/model_v1.joblib`, versionné et vérifié par son empreinte. La suite complète dure environ 10 s, auxquelles s'ajoute l'installation des dépendances.
* **Couverture bloquante à 95 %** sur `app/`. Mesurée localement : 100 % des lignes et des branches.
* **Dépendances figées** : le modèle joblib est lié à scikit-learn 1.9.1, et une autre version pourrait le charger différemment.
* `permissions: contents: read` et `concurrency` : droits minimaux, et annulation des exécutions devenues obsolètes.
* Syntaxe du workflow validée par `actionlint` (aucune erreur).

## 2. Preuve que la CI peut échouer

`tests/test_echec_volontaire.py` contient un test qui échoue toujours (« probabilité 1,5 hors de [0, 1] »). Il est **ignoré** par défaut et activé par `ECHEC_VOLONTAIRE=1`, variable que positionne la case `echec_volontaire` du déclenchement manuel.

Vérification locale :

```text
$ ECHEC_VOLONTAIRE=1 pytest
FAILED tests/test_echec_volontaire.py::test_echec_volontaire - AssertionError...
1 failed, 291 passed, 1 xfailed
$ echo $?
1
```

Un code de sortie différent de 0 fait échouer l'étape « Pytest + couverture », donc le job, donc le workflow.

## 3. Simulation locale de la CI

Une exécution dans un environnement virtuel **neuf**, installé uniquement depuis `requirements.txt`, avec les commandes exactes du workflow, donne :

```text
ruff check --output-format=github .   → All checks passed!
ruff format --check .                 → 32 files already formatted
pytest --cov ... --cov-fail-under=95  → 291 passed, 1 skipped, 1 xfailed
                                        Required test coverage of 95% reached. Total coverage: 100.00%
```

## 4. Preuves à produire sur GitHub (à faire par l'étudiant)

Ce dépôt n'a pas encore été poussé sur GitHub : les captures ci-dessous restent à réaliser.

1. Créer le dépôt `CreditRisk-Test` et pousser `main` (commandes dans le README).
2. **Preuve 1 (vert)** : onglet *Actions* → exécution du push sur `main` → capture des deux jobs verts et de l'onglet *Summary* (tableau par exigence).
3. **Preuve 2 (Pull Request)** : créer une branche, modifier un fichier (par exemple le README), ouvrir une PR → capture des vérifications vertes dans la PR.
4. **Preuve 3 (rouge)** : *Actions* → *tests* → *Run workflow* → cocher `echec_volontaire` → capture du job rouge et de la ligne `FAILED tests/test_echec_volontaire.py`.
5. **Preuve 4 (régression réelle détectée)** : dans une PR, modifier `SEUIL_RISQUE_ELEVE = 0.50` en `0.60` dans `app/config.py` → TA04 échoue → PR bloquée. Annuler ensuite la modification.
6. *Settings* → *Branches* → règle de protection de `main` exigeant les vérifications `Qualité du code (Ruff)` et `Tests (Python 3.13)`.
7. Télécharger l'artefact `preuves-python-3.13` et le joindre au rendu.
