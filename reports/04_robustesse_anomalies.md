# Tests de robustesse et registre des anomalies

Suite : `tests/test_robustness.py`, 19 fonctions, 125 cas, dont 4 propriétés Hypothesis (150 tirages chacune, soit 600 entrées générées en plus).

## 1. Analyse par test

| Test | Risque visé | Comportement attendu | Résultat observé | Gravité de l'anomalie éventuelle | Correction recommandée |
|---|---|---|---|---|---|
| **TR01** Valeur `null` (×5 champs) | Une valeur manquante est imputée ou propagée | 422, champ identifié | ✅ 5/5 rejetés | — | — |
| **TR02** Plusieurs champs absents | L'agent corrige un champ à la fois | Toutes les erreurs dans une seule réponse | ✅ 4 champs listés | — | — |
| **TR03** Non numériques : `""`, `" "`, `"abc"`, `"1e5"`, `"250 000"`, `"250,000"`, `[1]`, `{"v":1}`, `true`, `false` (×5 champs) | Conversion implicite (« 1e5 » lu comme 100 000, booléen lu comme 1) | 422 sur les 50 combinaisons | ✅ 50/50 | — | — |
| **TR04** Non finies : `NaN`, `Infinity`, `-Infinity`, `1e400`, `-1e400` dans le JSON **brut** (×5 champs) | Le parseur JSON de Python accepte ces littéraux non standard ; `1e400` déborde en `inf` | 422 : aucune valeur n'atteint le modèle | ✅ 25/25 (`allow_inf_nan=False` + typage strict) | — | — |
| **TR05** Bornes incluses (18, 75, 1 et 120 mois, revenu 1 et 100 M, montant 1 et 500 M, ancienneté 0) | Erreur « ≤ » / « < » aux bornes | 200 et probabilité valide | ✅ 10/10 | **A05** : un revenu de 10⁻⁹ FCFA est accepté (alerte seulement) | Plancher de revenu plausible (voir A05) |
| **TR06** Première valeur au-delà de chaque borne (17, 76, 0, 121, revenu × 1,000001…) | Bornes décalées | 422 | ✅ 10/10 | — | — |
| **TR07** Valide mais hors distribution (revenu 1 000 ou 50 M, montant 300 M, durée 120, âge 75, ancienneté 50, mensualité > revenu) | Le modèle extrapole sans prévenir | 200 + alerte ciblée + analyse requise | ✅ 7/7 | **A06** : contrôle par variable, pas de détection des combinaisons atypiques | Détecteur multivarié |
| **TR08** Dossier typique | Fausses alertes qui lassent l'agent | `alertes = []` | ✅ | — | — |
| **TR09** Schéma incorrect : liste, objet imbriqué, clés en majuscules, clé mal orthographiée, valeurs en tableau, objet vide | Un schéma voisin est accepté ou provoque un 500 | 422 | ✅ 6/6 | — | — |
| **TR10** Clé JSON dupliquée | Deux valeurs pour un même champ | Valeur retenue validée | ✅ rejet si la dernière est invalide | **A07** : la *dernière* valeur gagne en silence | Refuser les clés dupliquées |
| **TR11** Corps encodé en Latin-1 | `UnicodeDecodeError` → 500 | 400 ou 422 | ✅ 400 | — | — |
| **TR12** 20 envois identiques | Non-déterminisme | Réponses identiques | ✅ 1 seule réponse distincte | — | — |
| **TR13** Ordre des clés inversé | Dépendance à l'ordre des colonnes | Même réponse | ✅ | — | — |
| **TR14** `250000` et `250000.0` | Traitement différent entier / décimal | Même réponse | ✅ | — | — |
| **TR15** Propriété : toute entrée valide (150 tirages sur tout le domaine autorisé) | Combinaison valide qui casse le calcul (log, division, débordement) | 200, `0 ≤ p ≤ 1`, p finie | ✅ 150/150 | — | — |
| **TR16** Fuzzing : 150 corps aléatoires (types mêlés, clés inconnues, entiers de ±10²⁰) | Erreur 500 sur une entrée imprévue | Uniquement 200 ou 422 ; 200 ⇒ p valide | ✅ aucun 500 | — | — |
| **TR17** Monotonie du montant, domaine réaliste (mensualité ≥ 1 % du revenu) | Risque qui baisse quand le montant augmente | p non décroissante | ✅ 150/150 | — | — |
| **TR17b** Monotonie du montant, domaine complet | Idem, hors domaine réaliste | p non décroissante | ⚠️ **Échec documenté** (xfail strict) | **A02** Mineure | Voir A02 |
| **TR18** Monotonie du revenu | Risque qui monte quand le revenu augmente | p non croissante | ✅ 150/150 | — | — |

**Entrées invalides et entrées inhabituelles** : sur l'ensemble des cas, aucune entrée invalide n'a produit de probabilité, et aucune entrée valide n'a été rejetée. Les entrées inhabituelles reçoivent toujours une probabilité, accompagnée d'une alerte et d'une demande d'analyse.

### Analyse de A02 (monotonie)

Hypothesis a trouvé un contre-exemple minimal : âge 18, revenu 3 FCFA, montant 1 → 2 FCFA, durée 109 mois. La probabilité passe de 0,965530 à 0,965529. Le modèle combine `log_montant` (coefficient standardisé −0,011) et `log_taux_endettement` (+2,48). La dérivée du score par rapport au montant n'est négative que si la mensualité est inférieure à **0,44 % du revenu**. Ce cas ne se présente **dans aucune** des 20 000 demandes du jeu (minimum observé : 1,9 %). L'effet est donc réel mais minuscule, et confiné à des dossiers absurdes.

## 2. Registre des anomalies

| ID | Description | Détectée par | Gravité | Statut | Correction |
|---|---|---|---|---|---|
| **A01** | `KeyError` brut dans `transformer()` si une variable dérivée manque : l'erreur n'était pas identifiée comme une erreur de prétraitement | TI13 | Mineure | **Corrigée** | `transformer()` vérifie les 6 variables et lève `ErreurPretraitement`. TI13 sert de non-régression. |
| **A02** | Monotonie du montant rompue quand la mensualité est < 0,44 % du revenu | TR17b (Hypothesis) | Mineure | Ouverte, documentée par un xfail strict | Retirer `log_montant`, redondant avec le taux d'endettement, ou imposer une contrainte de monotonie, puis requalifier. Le xfail strict fera échouer la CI le jour où l'anomalie disparaît, ce qui obligera à mettre le registre à jour. |
| **A03** | Un dossier hors domaine à score faible recevait la recommandation « **Avis favorable** », alors que `analyse_complementaire_requise = true` : message contradictoire pour l'agent | Revue des réponses observées (S08b) | **Majeure** | **Corrigée** | Recommandation spécifique « Dossier inhabituel… vérification manuelle requise » ; assertion ajoutée dans S08b. |
| **A04** | Au seuil « modéré » (0,20), le rappel est de **0,455** : 302 des 554 défauts du jeu de test sont classés « risque faible » | Évaluation de la baseline | **Majeure** (métier) | Ouverte | Fixer les seuils avec le métier selon le coût d'un défaut et la capacité d'analyse. À 0,12 : rappel 0,73, mais 42 % des dossiers à analyser. Voir le rapport de qualification, § 6. |
| **A05** | Aucun plancher de revenu plausible : 10⁻⁹ FCFA est accepté (alerte hors domaine seulement) | TR05 | Mineure | Ouverte | Rejeter un revenu inférieur à un minimum défini avec le métier (par exemple 5 000 FCFA). |
| **A06** | Détection hors domaine variable par variable : une combinaison atypique de valeurs individuellement normales n'est pas signalée | Analyse de TR07 | Mineure | Ouverte | Ajouter une distance de Mahalanobis ou une Isolation Forest ajustée sur l'entraînement. |
| **A07** | Clé JSON dupliquée : la dernière valeur est retenue sans avertissement | TR10 | Mineure | Ouverte | `object_pairs_hook` qui rejette les doublons (400). |
| **A08** | Saturation vers 450 req/s avec 1 processus ; P95 de 88 ms à 32 clients | `scripts/benchmark.py` | Info | Ouverte | Plusieurs workers uvicorn (`--workers`) si la charge réelle l'exige. Elle est aujourd'hui 100 fois inférieure. |
| **A09** | Avertissement de dépréciation `httpx` du `TestClient` de Starlette dans un environnement neuf | Simulation de la CI | Info | Ouverte | Migrer vers le client recommandé lors de la prochaine montée de version. |
| **A10** | Ni authentification, ni chiffrement, ni limitation de débit sur l'API | Revue | Majeure **hors périmètre du prototype** | Ouverte | Obligatoire avant tout pilote : jeton par agent, TLS, limitation de débit, journal d'accès. |

**Bilan** : 0 critique ; 2 majeures ouvertes (A04 métier, A10 hors périmètre) ; 1 majeure corrigée (A03) ; 5 mineures, dont 1 corrigée ; 2 info.
