# Rapport final de qualification : CreditRisk v1.0.0

| | |
|---|---|
| **Objet** | Qualification du système d'estimation du risque de défaut de remboursement (microfinance) |
| **Version** | API 1.0.0, modèle `model_v1.joblib` (StandardScaler + régression logistique, C = 0,01), SHA-256 `7c9037960dbb…` |
| **Données** | Synthétiques, 20 000 demandes, taux de défaut de 13,9 %, processus de génération documenté (`data/README.md`) |
| **Date** | 20 novembre 2026 |
| **Décision** | **Logiciel QUALIFIÉ. Pilote AUTORISÉ en mode observation uniquement, sans usage décisionnel.** Le modèle v1 n'est **pas** apte à orienter des décisions de crédit réelles (§ 10). |

---

## 1. Contexte et exigences

Une institution de microfinance veut fournir à ses agents de crédit une estimation du risque de défaut d'un demandeur. Le système reçoit 5 variables (âge, revenu mensuel, montant, durée, ancienneté d'activité), les valide, construit 6 variables dérivées, applique un modèle de régression logistique et renvoie une probabilité, un niveau de risque (faible < 0,20 ≤ modéré < 0,50 ≤ élevé), une recommandation et d'éventuelles alertes.

La qualification porte sur **le système complet**, et pas seulement sur le modèle : contrat d'entrée, prétraitement, modèle, API, gestion des pannes, reproductibilité, non-régression, performance et automatisation.

**22 exigences** ont été retenues : les 7 imposées (EX01 à EX07) et **15 ajoutées** (EX08 à EX22). Parmi les ajouts : montant, champs en trop, valeurs non finies, requêtes mal formées, absence de trace technique, cohérence âge / ancienneté, signalement des entrées inhabituelles, reproductibilité, traçabilité de version, intégrité du modèle, performance, monotonie métier, interprétation, conformité du prétraitement, et capacité de la CI à échouer.

Hors périmètre : infrastructure de production, authentification, intégration au système d'information de l'institution, conformité réglementaire et équité. Ces points sont repris au § 10.3.

## 2. Stratégie de test et matrice de traçabilité

Détail : `01_plan_de_test.md`. La stratégie combine 7 niveaux (unitaire, fonctionnel, intégration, robustesse, non-régression, performance, CI), priorisés selon la gravité des conséquences d'une défaillance (critique, majeure, mineure, info). Chaque test porte un marqueur `@pytest.mark.exigence(...)`. Un greffon pytest exporte les résultats par exigence : la matrice est donc **générée à partir de l'exécution**, et non tenue à la main.

| Exigence | Cas | Résultat | | Exigence | Cas | Résultat |
|---|---:|---|---|---|---:|---|
| EX01 Âge | 35 | ✅ | | EX12 Pas de trace technique | 15 | ✅ |
| EX02 Revenu | 91 | ✅ | | EX13 Cohérence âge / ancienneté | 13 | ✅ |
| EX03 Durée | 84 | ✅ | | EX14 Entrées inhabituelles signalées | 10 | ✅ |
| EX04 Probabilité dans [0, 1] | 27 | ✅ | | EX15 Reproductibilité | 8 | ✅ |
| EX05 Modèle indisponible | 13 | ✅ | | EX16 Traçabilité de version | 4 | ✅ |
| EX06 Entrée incomplète | 31 | ✅ | | EX17 Intégrité du modèle | 6 | ✅ |
| EX07 Non-régression | 11 | ✅ | | EX18 Performance | 2 + bancs | ✅ |
| EX08 Montant | 82 | ✅ | | EX19 Monotonie métier | 3 | ⚠️ 2 ✅, 1 anomalie connue (A02) |
| EX09 Champs en trop | 8 | ✅ | | EX20 Interprétation | 8 | ✅ |
| EX10 Valeurs non finies | 36 | ✅ | | EX21 Prétraitement | 19 | ✅ |
| EX11 Requête mal formée | 15 | ✅ | | EX22 La CI échoue sur un test défaillant | 1 | ✅ vérifié (code de sortie 1) |

*Un cas peut couvrir plusieurs exigences : les colonnes ne s'additionnent pas.*

## 3. Tests fonctionnels et d'intégration

**Bilan global** (`02_resultats_tests.md`) : **102 fonctions de test, 293 cas, 291 réussis, 0 échec**, 1 anomalie connue (xfail strict), 1 test de démonstration ignoré. S'y ajoutent 600 entrées générées par Hypothesis. Couverture de `app/` : **100 % des lignes et des branches**. Ruff : aucune erreur. Durée : environ 10 s.

**API** (`03_tests_api_integration.md`) : les 10 scénarios imposés sont conformes (47 cas). Typage strict : `"250000"` (texte) et `12.0` (durée) sont refusés. Les champs non prévus sont refusés, et non ignorés. Un JSON invalide renvoie 400 et non 500. Toutes les erreurs ont un format unique et ne recopient pas la valeur reçue.

**Intégration** (24 cas) : des espions placés à chaque jonction prouvent l'ordre des traitements et l'exactitude de la transformation (vecteur recalculé à la main, écart ≤ 1e-12). 15 pannes ont été injectées : modèle absent, altéré, corrompu, au mauvais format ou incompatible ; prétraitement en erreur ; variable manquante ; dimensions fausses ; exception du modèle ; probabilité aberrante ; erreur imprévue. Toutes donnent une erreur 503 ou 500 propre, sans trace, chemin ni type d'exception. **Le fichier modèle n'est jamais désérialisé si son empreinte SHA-256 ne correspond pas** (protection contre l'exécution de code par pickle).

## 4. Robustesse

Détail : `04_robustesse_anomalies.md` (125 cas). Aucune entrée invalide n'a produit de probabilité, et aucune entrée valide n'a été rejetée :

* **Valeurs manquantes, non numériques, schéma incorrect** (62 cas) : toujours 422.
* **Valeurs non finies** : `NaN`, `Infinity` et `1e400` envoyés en JSON brut sont refusés (25/25). Le parseur JSON de Python les accepte : sans `allow_inf_nan=False`, ils auraient atteint le modèle.
* **Bornes** : les 10 bornes incluses sont acceptées, et les 10 premières valeurs au-delà sont rejetées.
* **Hors distribution mais valide** : les 7 cas reçoivent une probabilité, une alerte ciblée et une demande d'analyse ; aucune fausse alerte sur un dossier typique.
* **Fuzzing** (150 corps aléatoires) : aucune erreur 500.
* **Propriétés métier** (Hypothesis) : le risque ne baisse pas quand le montant augmente (domaine réaliste) et ne monte pas quand le revenu augmente. Hypothesis a trouvé **un contre-exemple hors domaine réaliste** (A02).

## 5. Non-régression

Détail : `05_rapport_non_regression.md`. Baseline v1.0.0 figée : métriques sur 4 000 demandes et 200 prédictions de référence. **Tolérances fixées avant la comparaison** (`baseline/tolerances.json`) : baisse maximale de 0,03 pour le rappel, le F1 et la PR-AUC, de 0,02 pour la ROC-AUC et de 0,05 pour la précision, avec un plancher absolu pour chacune. Écart de probabilité ≤ 1e-9 pour un même modèle, et ≤ 0,10 au maximum (0,02 en moyenne) pour une nouvelle version.

| Candidate | Rappel | F1 | ROC-AUC | Écart max de p | Décision |
|---|---:|---:|---:|---:|---|
| Référence v1.0.0 | 0,455 | 0,387 | 0,752 | — | — |
| C0 v1.0.0 rechargée (contrôle) | 0,455 | 0,387 | 0,752 | 5,0e-13 | ✅ ACCEPTÉE |
| C1 réentraînée (C = 1,0) | 0,458 | 0,387 | 0,752 | 0,068 | ✅ ACCEPTÉE |
| C2 **bug de code** (mensualité calculée sur des années) | **0,007** | **0,014** | 0,682 | 0,737 | ❌ REJETÉE |
| C3 **données dégradées** (30 % d'étiquettes bruitées) | 0,933 | **0,289** | 0,751 | 0,162 | ❌ REJETÉE |

**Enseignement de C3** : la ROC-AUC est inchangée et le rappel *augmente*. Le modèle classe toujours les dossiers dans le bon ordre, mais ses probabilités sont décalées vers le haut : 76 % des dossiers deviennent « à risque ». Une surveillance limitée à la ROC-AUC ou au rappel aurait **accepté** cette version. C'est la combinaison de la précision, du F1 et de l'écart de probabilité qui la fait rejeter. Il faut donc toujours suivre plusieurs métriques, dont au moins une sensible au calibrage.

En CI, `test_regression.py` vérifie à chaque PR : les tolérances, le contrat des sorties sur 500 demandes, les 5 métriques, la détection d'une baisse de rappel ou de F1, le rejet d'un modèle dégradé, les 200 prédictions de référence, la cohérence après sauvegarde et rechargement (≤ 1e-12 sur 4 000 demandes) et le déterminisme de l'entraînement.

## 6. Performance prédictive (indicative)

| Métrique (test, n = 4 000, seuil 0,20) | Valeur | Commentaire |
|---|---:|---|
| ROC-AUC | 0,752 | Le « modèle parfait » (vraie probabilité de génération) obtient 0,753 : le modèle est au plafond atteignable sur ces données |
| PR-AUC | 0,385 | Taux de défaut de base de 0,139 |
| Rappel / précision / F1 | 0,455 / 0,336 / 0,387 | TN 2 949, FP 497, FN 302, TP 252 |
| Calibrage | Brier 0,104 (contre 0,119 pour une prédiction constante) | Probabilité moyenne et taux observé concordent sur les 10 déciles (écarts ≤ 0,03) |

| Seuil « modéré » | 0,10 | 0,12 | 0,15 | **0,20 (actuel)** | 0,30 |
|---|---:|---:|---:|---:|---:|
| Rappel | 0,80 | 0,73 | 0,63 | **0,45** | 0,26 |
| Précision | 0,22 | 0,24 | 0,28 | **0,34** | 0,45 |
| Part des dossiers à analyser | 52 % | 42 % | 31 % | **19 %** | 8 % |

Ces chiffres ne valent que pour les données synthétiques. Ils montrent cependant le **compromis à arbitrer par le métier** (A04) : au seuil actuel, 55 % des futurs défauts seraient classés « risque faible ».

## 7. Performance d'exécution

Détail : `06_rapport_performance.md`. Configuration : 2 cœurs Xeon à 2,1 GHz, 1 processus uvicorn, client sur la même machine.

| Indicateur | Mesure | Objectif | |
|---|---:|---:|---|
| P95 d'inférence (prétraitement + modèle) | 0,40 ms | ≤ 10 ms | ✅ |
| P95 HTTP, 1 client | 3,97 ms | ≤ 100 ms | ✅ |
| P95 HTTP, 32 clients en boucle fermée | 88,1 ms | ≤ 100 ms | ✅ |
| P95 Locust, 50 utilisateurs réalistes | 11 ms | ≤ 100 ms | ✅ |
| Débit soutenu | ≈ 450 req/s | ≥ 20 req/s | ✅ |
| Erreurs sous charge | 0 / 25 724 | 0 % | ✅ |

## 8. Anomalies

| ID | Description | Gravité | Statut |
|---|---|---|---|
| A01 | `KeyError` brut si une variable dérivée manque | Mineure | ✅ Corrigée (TI13) |
| A02 | Monotonie du montant rompue si mensualité < 0,44 % du revenu (aucun dossier du jeu de données concerné) | Mineure | Ouverte (xfail strict TR17b) |
| A03 | « Avis favorable » affiché sur un dossier hors domaine | **Majeure** | ✅ Corrigée (S08b) |
| A04 | Rappel de 0,455 au seuil actuel : 302 défauts sur 554 classés « risque faible » | **Majeure** (métier) | Ouverte |
| A05 | Pas de plancher de revenu plausible (10⁻⁹ FCFA accepté) | Mineure | Ouverte |
| A06 | Détection hors domaine variable par variable uniquement | Mineure | Ouverte |
| A07 | Clé JSON dupliquée : la dernière valeur gagne en silence | Mineure | Ouverte |
| A08 | Saturation vers 450 req/s avec 1 processus | Info | Ouverte |
| A09 | Dépréciation `httpx` dans le `TestClient` | Info | Ouverte |
| A10 | Ni authentification, ni TLS, ni limitation de débit | **Majeure** (hors périmètre) | Ouverte |

**0 anomalie critique.** Les 2 majeures ouvertes ne concernent pas la justesse du logiciel : l'une est un choix métier (A04), l'autre relève de l'infrastructure (A10).

## 9. Limites de l'évaluation

1. **Données synthétiques** : aucune métrique de ce rapport ne prédit la performance sur de vrais emprunteurs. La relation entre les variables et le défaut a été *choisie* : elle est simple, stationnaire et sans valeurs aberrantes de saisie.
2. **Cinq variables seulement** : un vrai modèle de microcrédit utilise l'historique de remboursement, le secteur d'activité, les garanties, la saisonnalité des revenus… Le contrat d'entrée devra être revu.
3. **Équité non évaluée** : il n'y a aucun attribut de groupe (et c'est voulu : EX09 refuse `ethnie`). L'âge est une variable du modèle, avec un coefficient négatif : les plus jeunes sont donc jugés plus risqués. C'est un **critère potentiellement discriminatoire**, à examiner juridiquement.
4. **Une seule partition de test**, consommée pour l'évaluation : toute nouvelle version doit être évaluée sur des données nouvelles.
5. **Seuils de risque (0,20 / 0,50) non validés** par le métier.
6. **Performance mesurée en local** sur une machine virtuelle partagée, sans réseau réel ni TLS.
7. **Robustesse adverse non testée** : un demandeur ou un agent qui ajuste ses déclarations pour passer sous le seuil n'est pas simulé.
8. **Preuve d'exécution GitHub Actions à produire** : le workflow est validé (`actionlint`) et simulé localement dans un environnement neuf, mais il n'a pas encore tourné sur GitHub (`07_ci_github_actions.md` § 4).

## 10. Décision

### 10.1 Verdict technique

| Volet | Verdict |
|---|---|
| Contrat d'entrée, validation, gestion des erreurs, absence de fuite | ✅ Conforme (EX01–EX03, EX05, EX06, EX08–EX13) |
| Pipeline et intégration, intégrité du modèle, traçabilité | ✅ Conforme (EX04, EX16, EX17, EX21) |
| Signalement des entrées inhabituelles | ✅ Conforme après correction de A03 (EX14) |
| Reproductibilité et non-régression | ✅ Conforme : 2 régressions réelles détectées et rejetées (EX07, EX15) |
| Performance d'exécution | ✅ Conforme avec une marge de 20 fois (EX18) |
| Cohérence métier du modèle | ⚠️ Conforme sur le domaine réaliste, anomalie mineure A02 hors domaine (EX19) |
| Automatisation | ✅ Conforme localement ; preuve GitHub à produire (EX22) |
| **Aptitude du modèle v1 à décider** | ❌ **Non démontrable** : données synthétiques, seuils non validés (A04) |

### 10.2 Décision : pilote en mode observation uniquement

**Le système logiciel est qualifié.** La chaîne validation → prétraitement → modèle → API se comporte conformément à son contrat, y compris face aux entrées invalides, inhabituelles ou hostiles et aux pannes. Elle détecte ses propres régressions et le fait automatiquement.

**Le modèle v1 ne doit pas orienter de décision de crédit.** Il a été entraîné sur des données synthétiques : sa qualité sur de vrais emprunteurs est inconnue.

Le prototype peut donc passer en **phase pilote en mode observation** (*shadow mode*). Les agents instruisent les dossiers comme aujourd'hui, sans voir le score. Le système note chaque dossier et l'on enregistre ensuite les remboursements réels. Ce pilote a pour objet de **constituer les données** qui permettront d'entraîner et de qualifier une version v2.

**Conditions préalables au pilote d'observation** :

1. Corriger A10 : authentification, TLS, limitation de débit, journal d'accès.
2. Faire valider par le métier le contrat d'entrée (plancher de revenu A05, plafonds) et le traitement des données personnelles. Le pilote implique la collecte de données de demandeurs réels : information des personnes, base légale, durée de conservation, conformément à la réglementation applicable sur la protection des données.
3. Pousser le dépôt et produire les preuves GitHub Actions.

**Conditions pour passer ensuite à un usage décisionnel (v2)** :

1. Entraîner sur les données réelles du pilote. Évaluer **une seule fois** sur une période postérieure jamais vue.
2. Fixer les seuils avec le métier, à partir du coût d'un défaut, de la marge et de la capacité d'analyse des agents (A04).
3. Mener un audit d'équité : effet de l'âge, du sexe, de la zone géographique, en mesurant les écarts de taux d'acceptation et d'erreur.
4. Corriger A02 et A06, puis rejouer l'intégralité du plan de test. Figer une baseline v2 par décision explicite.

### 10.3 Validation technique et décision métier

Une suite de 291 tests réussis prouve que **le logiciel fait ce qui a été spécifié**. Elle ne prouve pas que **ce qui a été spécifié est juste**. Les tests ne disent pas si les seuils de 0,20 et 0,50 sont bien choisis, si l'utilisation de l'âge est légale et équitable, si les agents interpréteront correctement le score, ni si les données synthétiques ressemblent à la réalité. Ces questions relèvent du métier, du juridique, de la conformité et de l'expérience utilisateur. Elles conditionnent tout usage décisionnel. Le système doit rester une **aide à la décision** : la décision finale et sa justification auprès du demandeur appartiennent à l'agent de crédit.

---

**Annexes** : `01_plan_de_test.md` · `02_resultats_tests.md` · `03_tests_api_integration.md` · `04_robustesse_anomalies.md` · `05_rapport_non_regression.md` · `06_rapport_performance.md` · `07_ci_github_actions.md` · `baseline/` · `resultats/`
