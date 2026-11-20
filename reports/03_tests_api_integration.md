# Tests fonctionnels de l'API et tests d'intégration

## 1. Contrat de l'API

| Endpoint | Succès | Erreurs possibles |
|---|---|---|
| `GET /health` | 200 `{"statut":"ok","modele_charge":true,"version_modele":"1.0.0"}` | 503 `{"statut":"indisponible","modele_charge":false}` |
| `POST /predict` | 200 (schéma ci-dessous) | 400, 413, 415, 422, 500, 503 |
| `GET /model-info` | 200 : nom, version, algorithme, date, SHA-256, variables, seuils, métriques de test, avertissement sur les données | 503 |

Réponse 200 de `POST /predict` :

```json
{
  "probabilite_defaut": 0.123832,
  "niveau_risque": "faible",
  "recommandation": "Avis favorable : instruction standard du dossier.",
  "analyse_complementaire_requise": false,
  "alertes": [],
  "version_modele": "1.0.0"
}
```

Toute erreur a la même forme, sans trace technique ni recopie de la valeur reçue :

```json
{"erreur": {"code": "DONNEES_INVALIDES", "message": "...", "details": [{"champ": "age", "type": "greater_than_equal", "message": "valeur trop petite (doit être >= 18)"}]}}
```

| Code | `erreur.code` | Cause |
|---|---|---|
| 400 | `REQUETE_MAL_FORMEE` | JSON syntaxiquement invalide, corps absent, `Content-Length` invalide |
| 413 | `REQUETE_TROP_VOLUMINEUSE` | Corps > 10 ko (une demande fait environ 150 octets) |
| 415 | `TYPE_CONTENU_NON_SUPPORTE` | `Content-Type` différent de `application/json` |
| 422 | `DONNEES_INVALIDES` | Champ absent, en trop, mal typé, non fini, hors bornes ou incohérent |
| 500 | `ERREUR_INTERNE` | Panne du prétraitement ou du modèle ; `id_incident` pour retrouver l'entrée du journal |
| 503 | `MODELE_INDISPONIBLE` | Modèle non chargé, absent, altéré ou illisible |

## 2. Scénarios obligatoires (`tests/test_api.py`)

Tous les résultats ci-dessous ont été **observés** lors de l'exécution du 20/11/2026 (291 réussis, 0 échec).

| # | Scénario | Code attendu | Contenu attendu | Comportement de l'application | Observé |
|---|---|---|---|---|---|
| S01 | Requête valide | 200 | 6 clés, `0 ≤ p ≤ 1`, version 1.0.0 | Validation → prétraitement → modèle → interprétation | ✅ 200, p = 0,123832, « faible » |
| S02 | Champ obligatoire absent (×5) | 422 | `details[].champ` = champ absent, `type = missing` | Rejet avant le modèle | ✅ 5/5 |
| S03 | Âge négatif | 422 | champ `age`, « valeur trop petite (doit être >= 18) » | Rejet | ✅ |
| S04 | Revenu en texte (`"250000"`, `"deux cent mille"`, `""`) | 422 | champ `revenu_mensuel`, « un nombre est attendu » | Typage strict : un texte n'est jamais converti | ✅ 3/3 |
| S05 | Montant nul ou négatif | 422 | champ `montant_credit` | Rejet | ✅ 2/2 |
| S06 | Durée non entière (`12.5`, `12.0`, `"12"`) | 422 | champ `duree_mois`, « un nombre entier est attendu » | `12.0` est aussi refusé : une durée est un entier | ✅ 3/3 |
| S07 | Champ supplémentaire (`ethnie`) | 422 | `type = extra_forbidden` | Une variable non prévue (ici sensible) n'est jamais ignorée en silence | ✅ |
| S08a | Valeurs extrêmes au-delà des plafonds (montant 10¹⁵, revenu 10¹⁵, âge 10¹², durée 10⁹) | 422 | « valeur trop grande » | Rejet | ✅ 4/4 |
| S08b | Valeurs très élevées **sous** les plafonds (montant 500 M, revenu 100 M) | 200 | alertes `hors_domaine:*`, `analyse_complementaire_requise = true` | Prédiction fournie **et signalée comme peu fiable** | ✅ (après correction de A03) |
| S09 | Modèle indisponible | 503 | `MODELE_INDISPONIBLE` ; `/health` `modele_charge:false` | L'API reste joignable et le dit | ✅ 4 tests |
| S10 | Requête mal formée | 400 / 415 / 413 | `REQUETE_MAL_FORMEE`, etc. | Aucun 500 | ✅ 11 tests |

Compléments : `GET /predict` → 405 (TA01), `/health` nominal (TA02), contrat de `/model-info` (TA03), seuils de risque aux bornes exactes 0,20 et 0,50 (TA04), risque élevé ⇒ analyse requise (TA05), `Content-Length` invalide → 400 (TA06). S09b vérifie que la validation (422) passe avant la disponibilité du modèle : une requête invalide reste signalée comme telle même pendant une panne.

## 3. Tests d'intégration (`tests/test_integration.py`)

### 3.1 Scénario principal

TI01 envoie la requête S01 et place un **espion** à chaque jonction :

1. **Validation** : le prétraitement reçoit un objet `DemandeCredit` déjà validé, jamais le JSON brut.
2. **Transformation** : la matrice transmise au modèle est `(1, 6)` et vaut exactement `[35, ln 250 000, ln 1 000 000, 12, 4, ln(1 + 83 333,33 / 250 000)]` (écart relatif ≤ 1e-12).
3. **Prédiction** : la probabilité renvoyée égale l'appel direct `pipeline.predict_proba` à 1e-6 près (arrondi de la réponse).
4. **Structure** : les 6 clés du contrat.
5. **Métadonnées** (TI02) : SHA-256 identique entre le fichier, `model_v1.json` et `/model-info` ; même version dans `/health`, `/model-info` et `/predict` ; `n_features_in_` du modèle = nombre de variables déclarées.

TI03 vérifie en plus que 50 demandes prédites en lot ou une par une donnent les mêmes probabilités (≤ 1e-12).

### 3.2 Scénarios de panne

| Test | Panne injectée | Réponse attendue et observée |
|---|---|---|
| TI04 | Fichier modèle absent | `ErreurModeleIndisponible("…introuvable")` |
| TI05 | Métadonnées absentes | Refus du chargement |
| TI06 | Modèle altéré (1 octet ajouté) | Refus **avant** `joblib.load` (vérifié : `load` jamais appelé) |
| TI07 | Fichier illisible avec empreinte recalculée | `ErreurModeleIndisponible("modèle illisible (…)")`, pas d'exception brute |
| TI08 | Objet désérialisé au mauvais format | Refus « format de modèle inattendu » |
| TI09 | Modèle entraîné avec d'autres variables | Refus « variables du modèle incompatibles avec le code » |
| TI10 | Démarrage de l'API sans modèle | L'API démarre, `/health` 503, `/predict` 503, le nom du fichier n'est pas exposé |
| TI11 | Modèle déchargé à chaud puis rechargé | 503 puis 200 |
| TI12 | Le prétraitement lève une erreur | 500 `ERREUR_INTERNE` + `id_incident` de 12 caractères |
| TI13 | Une variable dérivée disparaît | 500 contrôlée. **A révélé l'anomalie A01** (voir § 3.3) |
| TI14 | Dimensions (1, 5), (1, 7), (6,) | 500 contrôlée (vérification explicite de `n_features_in_`) |
| TI15 | Matrice de largeur 4 au niveau service | `ErreurPrediction("dimensions incompatibles…")` |
| TI16 | Le modèle lève `RuntimeError("secret /home/app/model.py")` | 500 sans le message, le type ni le chemin |
| TI17 | Le modèle renvoie 1,5, −0,1, NaN ou +inf | 500 ; aucune probabilité aberrante ne sort |
| TI18 | Exception imprévue (`ZeroDivisionError`) | 500 générique via le gestionnaire global, sans trace |

Le contrôle « sans trace technique » vérifie l'absence de : `Traceback`, `File "`, `/home`, `site-packages`, `.py`, `Error(`, `RuntimeError`, `secret`.

### 3.3 Anomalie révélée

**A01**. Lors du premier passage de TI13, la suppression d'une variable dérivée provoquait un `KeyError` brut dans `transformer()`. Il était bien attrapé par le gestionnaire global (500 générique), mais sans être identifié comme une erreur de prétraitement : pas d'erreur métier dans le journal, et l'exception remontait jusqu'au serveur. **Correction** : `transformer()` vérifie la présence des 6 variables et lève `ErreurPretraitement`. TI13 sert désormais de test de non-régression.
