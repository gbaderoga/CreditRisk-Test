# Plan de test et matrice de traçabilité

| | |
|---|---|
| **Système** | CreditRisk API v1.0.0 : estimation du risque de défaut d'un demandeur de microcrédit |
| **Composants** | `app/validation.py` · `app/preprocessing.py` · `app/prediction.py` · `app/main.py` |
| **Modèle** | `models/model_v1.joblib` (StandardScaler + régression logistique, C = 0,01), SHA-256 dans `models/model_v1.json` |
| **Données** | Synthétiques, 20 000 demandes, graine 42 (`data/README.md`) |
| **Outils** | Python 3.12/3.13, pytest, Hypothesis, FastAPI TestClient, pytest-cov, Ruff, Locust, GitHub Actions |
| **Date** | 20 novembre 2026 |

## 1. Stratégie

### 1.1 Objectif

Démontrer que **le système complet** respecte son contrat, et pas seulement que le modèle produit un nombre : données invalides rejetées proprement, données inhabituelles signalées, pannes gérées sans fuite d'information, prédictions reproductibles, absence de régression après une modification du code ou du modèle.

### 1.2 Niveaux de test

| Niveau | Cible | Technique | Fichier |
|---|---|---|---|
| Unitaire | Validation, prétraitement | Valeurs aux bornes, partitions d'équivalence, typage strict | `test_validation.py`, `test_preprocessing.py` |
| Fonctionnel | Contrat HTTP des 3 endpoints | Boîte noire via `TestClient`, 10 scénarios imposés (S01–S10) | `test_api.py` |
| Intégration | Validation → prétraitement → modèle → API | Espions (`monkeypatch`) aux jonctions, injection de pannes | `test_integration.py` |
| Robustesse | Entrées limites, non finies, hors distribution, schéma | Tables de cas, fuzzing et propriétés (Hypothesis) | `test_robustness.py` |
| Non-régression | Code et modèle par rapport à la baseline v1.0.0 | Métriques figées, 200 prédictions de référence, tolérances fixées à l'avance | `test_regression.py`, `scripts/non_regression.py` |
| Performance | Latence, P95, débit, montée en charge | Mesures `perf_counter`, uvicorn + httpx, Locust | `test_performance.py`, `scripts/benchmark.py` |
| Automatisation | Chaîne CI | GitHub Actions, Ruff, couverture ≥ 95 %, test d'échec volontaire | `.github/workflows/tests.yml` |

### 1.3 Règle invalide / inhabituel

| Catégorie | Définition | Comportement attendu |
|---|---|---|
| **Invalide** | Viole le contrat : type, champ, borne métier, cohérence, finitude | Rejet **4xx**, champ en cause identifié, aucune probabilité renvoyée |
| **Inhabituelle mais valide** | Respecte le contrat mais sort du domaine d'entraînement (quantiles 0,5 %–99,5 %) ou mensualité > revenu | **200**, probabilité valide, `alertes` non vide, `analyse_complementaire_requise = true` |

### 1.4 Échelle de gravité et priorité

| Gravité | Conséquence d'une défaillance | Priorité de test |
|---|---|---|
| **Critique** | Décision de crédit fondée sur une sortie fausse, ou donnée invalide qui atteint le modèle sans alerte | P1, bloquant |
| **Majeure** | Service indisponible sans signalement, fuite d'information, régression silencieuse du modèle | P1, bloquant |
| **Mineure** | Message d'erreur imprécis, comportement discutable hors domaine réaliste | P2 |
| **Info** | Amélioration souhaitable, pas de défaut fonctionnel | P3 |

### 1.5 Critères d'entrée et de sortie

* **Entrée** : modèle versionné présent et dont l'empreinte est vérifiée, dépendances figées (`requirements.txt`), tolérances de non-régression fixées (`reports/baseline/tolerances.json`).
* **Sortie (qualification technique)** : 100 % des tests P1 réussis, aucune anomalie critique ou majeure ouverte **sur le logiciel**, couverture de `app/` ≥ 95 %, Ruff sans erreur, workflow CI vert et capable d'échouer.

## 2. Matrice de traçabilité

EX01 à EX07 sont imposées par le sujet. **EX08 à EX22 sont ajoutées** (15 exigences).

| ID | Exigence | Résultat attendu | Risque si défaillance | Gravité | Prio. | Tests |
|---|---|---|---|---|---|---|
| EX01 | Âge entier dans [18, 75] | Hors bornes, décimal, texte, booléen ou null → 422 sur `age` | Crédit accordé à un mineur ; extrapolation du modèle | Critique | P1 | TV02–TV04, S03, TR05, TR06 |
| EX02 | Revenu numérique, > 0 et ≤ 100 M FCFA | Texte (même `"250000"`), ≤ 0, booléen → 422 | Division par zéro, log d'un négatif, probabilité absurde | Critique | P1 | TV05–TV07, S04, S08a, TR03, TR05, TR06 |
| EX03 | Durée entière dans [1, 120] mois | 12.5, 12.0, `"12"`, 0, 121 → 422 | Mensualité faussée, durée hors offre | Majeure | P1 | TV08, TV09, S06, TR03, TR05, TR06 |
| EX04 | Probabilité finie dans [0, 1] | `0 ≤ p ≤ 1`, `isfinite(p)` ; toute sortie aberrante du modèle bloquée (500) | Décision fondée sur un score invalide | Critique | P1 | S01, TI01, TI03, TI17, TR05, TR07, TR15, TN03 |
| EX05 | Indisponibilité du modèle signalée | `/health` 503, `/predict` et `/model-info` 503 `MODELE_INDISPONIBLE` ; l'API démarre quand même | Service muet ou crash au démarrage | Majeure | P1 | S09, TA02, TI04–TI11 |
| EX06 | Entrée incomplète validée | Champ absent ou null → 422, **tous** les champs manquants listés | Imputation silencieuse, prédiction sur données partielles | Critique | P1 | TV11–TV13, S02, TP04, TR01, TR02, TR09, TR16 |
| EX07 | Pas de dégradation des critères critiques | Rappel, F1, ROC-AUC, PR-AUC, précision dans les tolérances ; candidate dégradée rejetée | Modèle dégradé mis en service | Majeure | P1 | TN01–TN07, `scripts/non_regression.py` |
| EX08 | Montant numérique, > 0 et ≤ 500 M FCFA | 0, négatif, texte, > plafond → 422 | Log d'un nombre ≤ 0, score absurde | Critique | P1 | TV10, S05, S08a, TR03, TR05, TR06 |
| EX09 | Champs supplémentaires refusés | Champ inconnu → 422 `extra_forbidden` | Variable sensible (ethnie, sexe) transmise sans contrôle ; faute de frappe ignorée | Majeure | P1 | TV14, S07, TR09 |
| EX10 | Valeurs non finies refusées | NaN, ±Infinity, 1e400 dans le JSON brut → 422 | NaN propagé jusqu'au modèle | Critique | P1 | TV15, TP07, TR04, TR16 |
| EX11 | Requête mal formée gérée | JSON invalide ou vide → 400 ; Content-Type ≠ JSON → 415 ; > 10 ko → 413 ; GET /predict → 405 | Erreur 500, saturation par corps volumineux | Majeure | P1 | S10, TA01, TA06, TR10, TR11 |
| EX12 | Erreurs internes sans trace technique | 500 générique `ERREUR_INTERNE` + `id_incident` ; ni trace, ni chemin, ni type d'exception, ni valeur d'entrée | Fuite d'information (chemins, versions, données personnelles) | Majeure | P1 | TV19, TV20, TI12–TI18, TR16 |
| EX13 | Cohérence âge / ancienneté | `anciennete_activite ≤ age − 12`, ≥ 0 et ≤ 60 | Dossier incohérent (saisie erronée) noté comme valide | Mineure | P2 | TV16–TV18, TR06 |
| EX14 | Entrée inhabituelle mais valide signalée | 200 + alerte `hors_domaine:<variable>` ou `mensualite_superieure_au_revenu` ; pas de fausse alerte sur un dossier typique | Extrapolation silencieuse du modèle | Majeure | P1 | S08b, TR07, TR08, TR15 |
| EX15 | Reproductibilité | Même entrée → même sortie ; sauvegarde/rechargement ≤ 1e-12 ; entraînement déterministe | Décisions différentes pour un même dossier ; audit impossible | Majeure | P1 | TI03, TR12–TR14, TN07–TN10 |
| EX16 | Traçabilité de la version | `/model-info` : version, SHA-256, variables, seuils, métriques ; même version dans `/health` et `/predict` | Impossible de savoir quel modèle a produit une décision | Majeure | P1 | TA03, TI01, TI02, TN02 |
| EX17 | Intégrité du modèle | Empreinte SHA-256 vérifiée **avant** désérialisation ; fichier absent, corrompu ou d'un format inattendu refusé | Exécution de code via un fichier pickle altéré | Critique | P1 | TI04–TI09 |
| EX18 | Performance | P95 de `/predict` ≤ 100 ms jusqu'à 32 clients simultanés ; débit ≥ 20 req/s | Attente pour l'agent de crédit ; indisponibilité en pic | Mineure | P2 | TPF01, TPF02, `scripts/benchmark.py`, Locust |
| EX19 | Cohérence métier (monotonie) | À profil égal : montant ↑ ⇒ risque non décroissant ; revenu ↑ ⇒ risque non croissant | Modèle contre-intuitif, inexplicable à l'agent et au client | Majeure | P1 | TR17, TR17b, TR18 |
| EX20 | Interprétation de la probabilité | Seuils 0,20 / 0,50 → faible / modéré / élevé ; risque élevé ⇒ analyse requise | Mauvais avis transmis à l'agent | Majeure | P1 | S01, TA04, TA05 |
| EX21 | Prétraitement conforme | 6 variables dérivées exactes, dans l'ordre attendu par le modèle ; erreurs → `ErreurPretraitement` | Décalage de colonnes : prédiction fausse sans erreur visible | Critique | P1 | TP01–TP08, TI01, TI09, TI12–TI14 |
| EX22 | La CI détecte un échec | Un test défaillant rend le workflow rouge | Régression fusionnée sans être vue | Majeure | P1 | TCI01 (`test_echec_volontaire.py`) |

## 3. Fiches de cas de test représentatifs

Les 102 fonctions de test (293 cas paramétrés) sont listées dans `02_resultats_tests.md`. Les fiches ci-dessous détaillent les cas P1 de chaque exigence imposée.

| Cas | Exigence | Préconditions | Données d'entrée | Résultat attendu |
|---|---|---|---|---|
| S01 | EX04 | Modèle v1 chargé | `{"age":35,"revenu_mensuel":250000,"montant_credit":1000000,"duree_mois":12,"anciennete_activite":4}` | 200 ; 6 clés ; `0 ≤ probabilite_defaut ≤ 1` ; `version_modele = "1.0.0"` |
| S02 | EX06 | Modèle chargé | Demande valide sans `age` (puis chacun des 5 champs) | 422 `DONNEES_INVALIDES`, détail `{champ: age, type: missing}` |
| S03 | EX01 | Modèle chargé | `age = -5` | 422, champ `age`, message « valeur trop petite (doit être >= 18) » |
| S04 | EX02 | Modèle chargé | `revenu_mensuel = "250000"`, `"deux cent mille"`, `""` | 422 sur `revenu_mensuel` (typage strict : un texte n'est jamais converti) |
| S05 | EX08 | Modèle chargé | `montant_credit = 0` puis `-1000000` | 422 sur `montant_credit` |
| S06 | EX03 | Modèle chargé | `duree_mois = 12.5`, `12.0`, `"12"` | 422 sur `duree_mois` |
| S07 | EX09 | Modèle chargé | Demande valide + `"ethnie": "X"` | 422 `extra_forbidden` sur `ethnie` |
| S08a | EX02, EX08 | Modèle chargé | `montant_credit = 1e15` ; `age = 10¹²` ; `duree_mois = 10⁹` | 422 (au-delà des plafonds) |
| S08b | EX14 | Modèle chargé | `montant_credit = 500 M`, `revenu_mensuel = 100 M` (plafonds exacts) | 200 ; alertes `hors_domaine:montant_credit` et `hors_domaine:revenu_mensuel` |
| S09 | EX05 | Service sans modèle (dépendance remplacée) | Demande valide | `/predict` 503 ; `/health` 503 `{"statut":"indisponible","modele_charge":false}` ; `/model-info` 503 |
| S10 | EX11 | Modèle chargé | `{"age": 35,` ; corps vide ; `text/plain` ; 20 ko | 400 ; 400 ; 415 ; 413 |
| TI06 | EX17 | Copie du modèle avec un octet ajouté | Chargement | `ErreurModeleIndisponible("empreinte SHA-256…")`, `joblib.load` jamais appelé |
| TI14 | EX12, EX21 | Prétraitement remplacé : matrice (1, 5) | Demande valide | 500 `ERREUR_INTERNE` + `id_incident`, aucun mot de la liste interdite (`Traceback`, `/home`, `.py`…) |
| TN04 | EX07 | Baseline v1 et tolérances figées | `data/test.csv` (4 000 demandes) | Pour rappel, F1, ROC-AUC, PR-AUC et précision : baisse ≤ tolérance et valeur ≥ plancher |
| TN08 | EX15 | Modèle chargé | 4 000 demandes, modèle sauvegardé puis rechargé | `max |Δp| ≤ 1e-12` |

## 4. Environnement et données de test

* **Jeu de test versionné** : `data/test.csv` (4 000 demandes, 554 défauts, 13,85 %). Il n'est jamais utilisé pour l'entraînement ni pour le choix des hyperparamètres (choisis sur la validation).
* **Baseline figée** : `reports/baseline/metriques_v1.json`, `predictions_reference_v1.csv` (200 demandes), `tolerances.json`.
* **Doubles de test** : `ServiceModele` vide (indisponibilité), `PipelineEnPanne` (exception ou sortie aberrante), espions sur `transformer` et `predire_probabilites`.
* Les tests ne réentraînent pas le modèle de production : ils utilisent le modèle versionné. Seuls TN06, TN09 et TN10 entraînent de petits modèles jetables (< 1 s).
