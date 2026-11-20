# Résultats d'exécution des tests

*Généré par `python -m scripts.rapports` à partir de `reports/resultats/resultats_tests.json`. Ne pas modifier à la main.*

**293 cas exécutés** : 291 réussis, 0 échoués, 1 anomalie connue (xfail strict), 1 ignoré (test d'échec volontaire, inactif hors démonstration).

## 1. Synthèse par suite

| Suite | Fichier | Fonctions | Cas | Réussis | Échoués | Autres |
|---|---|---:|---:|---:|---:|---:|
| Validation (unitaires) | `tests/test_validation.py` | 20 | 68 | 68 | 0 | 0 |
| Prétraitement (unitaires) | `tests/test_preprocessing.py` | 8 | 12 | 12 | 0 | 0 |
| API (fonctionnels) | `tests/test_api.py` | 24 | 47 | 47 | 0 | 0 |
| Intégration | `tests/test_integration.py` | 18 | 24 | 24 | 0 | 0 |
| Robustesse | `tests/test_robustness.py` | 19 | 125 | 124 | 0 | 1 |
| Non-régression | `tests/test_regression.py` | 10 | 14 | 14 | 0 | 0 |
| Performance (CI) | `tests/test_performance.py` | 2 | 2 | 2 | 0 | 0 |
| Démonstration CI | `tests/test_echec_volontaire.py` | 1 | 1 | 0 | 0 | 1 |

## 2. Synthèse par exigence

| Exigence | Cas de test | Réussis | Échoués | Anomalie connue | Ignorés |
|---|---:|---:|---:|---:|---:|
| EX01 | 35 | 35 | 0 | 0 | 0 |
| EX02 | 91 | 91 | 0 | 0 | 0 |
| EX03 | 84 | 84 | 0 | 0 | 0 |
| EX04 | 27 | 27 | 0 | 0 | 0 |
| EX05 | 13 | 13 | 0 | 0 | 0 |
| EX06 | 31 | 31 | 0 | 0 | 0 |
| EX07 | 11 | 11 | 0 | 0 | 0 |
| EX08 | 82 | 82 | 0 | 0 | 0 |
| EX09 | 8 | 8 | 0 | 0 | 0 |
| EX10 | 36 | 36 | 0 | 0 | 0 |
| EX11 | 15 | 15 | 0 | 0 | 0 |
| EX12 | 15 | 15 | 0 | 0 | 0 |
| EX13 | 13 | 13 | 0 | 0 | 0 |
| EX14 | 10 | 10 | 0 | 0 | 0 |
| EX15 | 8 | 8 | 0 | 0 | 0 |
| EX16 | 4 | 4 | 0 | 0 | 0 |
| EX17 | 6 | 6 | 0 | 0 | 0 |
| EX18 | 2 | 2 | 0 | 0 | 0 |
| EX19 | 3 | 2 | 0 | 1 | 0 |
| EX20 | 8 | 8 | 0 | 0 | 0 |
| EX21 | 19 | 19 | 0 | 0 | 0 |
| EX22 | 1 | 0 | 0 | 0 | 1 |

## 3. Détail par fonction de test

### Validation (unitaires) (`tests/test_validation.py`)

| Test | Description | Exigences | Cas | Résultat |
|---|---|---|---:|---|
| `test_demande_valide_acceptee` | TV01 Une demande conforme est acceptée et convertie sans perte. | EX01, EX02, EX03, EX08 | 1 | ✅ Réussi, ❌ Échoué |
| `test_age_aux_bornes_accepte` | TV02 Les âges situés aux bornes incluses (18 et 75) sont acceptés. | EX01 | 3 | ✅ Réussi ×3, ❌ Échoué ×0 |
| `test_age_hors_limites_rejete` | TV03 Un âge hors de [18, 75] est rejeté sur le champ age. | EX01 | 5 | ✅ Réussi ×5, ❌ Échoué ×0 |
| `test_age_non_entier_rejete` | TV04 Un âge décimal, textuel, booléen ou nul est rejeté (typage strict). | EX01 | 5 | ✅ Réussi ×5, ❌ Échoué ×0 |
| `test_revenu_invalide_rejete` | TV05 Un revenu nul, négatif ou non numérique provoque une erreur contrôlée. | EX02 | 8 | ✅ Réussi ×8, ❌ Échoué ×0 |
| `test_revenu_positif_accepte` | TV06 Un revenu entier ou décimal strictement positif et <= max est accepté. | EX02 | 4 | ✅ Réussi ×4, ❌ Échoué ×0 |
| `test_revenu_au_dessus_du_maximum_rejete` | TV07 Un revenu supérieur au plafond documenté est rejeté. | EX02 | 1 | ✅ Réussi, ❌ Échoué |
| `test_duree_valide_acceptee` | TV08 Les durées entières de 1 à 120 mois sont acceptées. | EX03 | 3 | ✅ Réussi ×3, ❌ Échoué ×0 |
| `test_duree_invalide_rejetee` | TV09 Une durée nulle, négative, > 120, décimale ou textuelle est rejetée. | EX03 | 7 | ✅ Réussi ×7, ❌ Échoué ×0 |
| `test_montant_invalide_rejete` | TV10 Un montant nul, négatif, textuel ou au-delà du plafond est rejeté. | EX08 | 5 | ✅ Réussi ×5, ❌ Échoué ×0 |
| `test_champ_obligatoire_absent` | TV11 L'absence de chacun des 5 champs obligatoires est signalée sur ce champ. | EX06 | 5 | ✅ Réussi ×5, ❌ Échoué ×0 |
| `test_demande_vide_signale_tous_les_champs` | TV12 Un objet vide produit une erreur par champ obligatoire. | EX06 | 1 | ✅ Réussi, ❌ Échoué |
| `test_entree_qui_n_est_pas_un_objet` | TV13 Une entrée qui n'est pas un objet est rejetée par une erreur contrôlée. | EX06 | 5 | ✅ Réussi ×5, ❌ Échoué ×0 |
| `test_champ_supplementaire_rejete` | TV14 Un champ non prévu au contrat est refusé (pas ignoré silencieusement). | EX09 | 1 | ✅ Réussi, ❌ Échoué |
| `test_valeurs_non_finies_rejetees` | TV15 NaN, +inf et -inf sont rejetés sur les champs décimaux. | EX10 | 9 | ✅ Réussi ×9, ❌ Échoué ×0 |
| `test_anciennete_incompatible_avec_age` | TV16 Une ancienneté supérieure à (âge - 12) ans est rejetée sur ce champ. | EX13 | 1 | ✅ Réussi, ❌ Échoué |
| `test_anciennete_a_la_limite_de_coherence_acceptee` | TV17 Une ancienneté exactement égale à (âge - 12) est acceptée. | EX13 | 1 | ✅ Réussi, ❌ Échoué |
| `test_anciennete_negative_rejetee` | TV18 Une ancienneté négative est rejetée. | EX13 | 1 | ✅ Réussi, ❌ Échoué |
| `test_message_d_erreur_ne_reflete_pas_la_valeur` | TV19 Le détail d'erreur ne recopie pas la valeur reçue (donnée personnelle). | EX12 | 1 | ✅ Réussi, ❌ Échoué |
| `test_formatage_erreur_sans_contexte` | TV20 Une erreur pydantic sans contexte ou de type inconnu reste formatée proprement. | EX12 | 1 | ✅ Réussi, ❌ Échoué |

### Prétraitement (unitaires) (`tests/test_preprocessing.py`)

| Test | Description | Exigences | Cas | Résultat |
|---|---|---|---:|---|
| `test_variables_derivees_calculees_exactement` | TP01 Les 6 variables dérivées ont les valeurs attendues (calcul à la main). | EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_objet_valide_et_dictionnaire_donnent_le_meme_resultat` | TP02 Un DemandeCredit et le dict équivalent produisent le même vecteur. | EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_dimensions_de_sortie` | TP03 n demandes donnent une matrice (n, 6) de flottants finis. | EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_variable_absente` | TP04 Une variable absente lève ErreurPretraitement (pas KeyError). | EX06, EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_division_ou_log_impossible` | TP05 Revenu, montant ou durée nuls (non validés) : erreur contrôlée, pas de crash. | EX21 | 3 | ✅ Réussi ×3, ❌ Échoué ×0 |
| `test_valeur_non_numerique` | TP06 Une valeur non convertible lève ErreurPretraitement. | EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_valeur_non_finie_produite` | TP07 Une valeur infinie qui aurait échappé à la validation est bloquée. | EX10, EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_entrees_non_prises_en_charge` | TP08 Liste vide ou éléments de type inattendu : ErreurPretraitement. | EX21 | 3 | ✅ Réussi ×3, ❌ Échoué ×0 |

### API (fonctionnels) (`tests/test_api.py`)

| Test | Description | Exigences | Cas | Résultat |
|---|---|---|---:|---|
| `test_s01_requete_valide` | S01 Requête valide : 200, probabilité dans [0, 1] et contrat de réponse complet. | EX04, EX20 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s02_champ_obligatoire_absent` | S02 Requête sans champ obligatoire : 422 DONNEES_INVALIDES sur le champ absent. | EX06 | 5 | ✅ Réussi ×5, ❌ Échoué ×0 |
| `test_s03_age_negatif` | S03 Âge négatif : 422 sur le champ age. | EX01 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s04_revenu_texte` | S04 Revenu sous forme de texte (même numérique) : 422 sur revenu_mensuel. | EX02 | 3 | ✅ Réussi ×3, ❌ Échoué ×0 |
| `test_s05_montant_nul_ou_negatif` | S05 Montant nul ou négatif : 422 sur montant_credit. | EX08 | 2 | ✅ Réussi ×2, ❌ Échoué ×0 |
| `test_s06_duree_non_entiere` | S06 Durée non entière (12.5, 12.0, "12") : 422 sur duree_mois. | EX03 | 3 | ✅ Réussi ×3, ❌ Échoué ×0 |
| `test_s07_champ_supplementaire` | S07 Champ non autorisé (ex. variable sensible) : 422 extra_forbidden. | EX09 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s08_valeurs_au_dela_des_plafonds_rejetees` | S08a Valeurs extrêmement élevées au-delà des plafonds : 422 (invalide). | EX02, EX08 | 4 | ✅ Réussi ×4, ❌ Échoué ×0 |
| `test_s08_valeurs_tres_elevees_mais_valides_signalees` | S08b Valeurs très élevées mais sous les plafonds : 200 + alerte, pas de rejet. | EX04, EX14 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s09_predict_modele_indisponible` | S09 Modèle non chargé : POST /predict renvoie 503 MODELE_INDISPONIBLE. | EX05 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s09_health_modele_indisponible` | S09 Modèle non chargé : GET /health renvoie 503 et modele_charge=false. | EX05 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s09_model_info_modele_indisponible` | S09 Modèle non chargé : GET /model-info renvoie 503. | EX05 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s09_validation_avant_disponibilite` | S09b Requête invalide + modèle indisponible : la validation (422) prime. | EX05, EX06 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s10_json_mal_forme` | S10 JSON syntaxiquement invalide : 400 REQUETE_MAL_FORMEE. | EX11 | 4 | ✅ Réussi ×4, ❌ Échoué ×0 |
| `test_s10_corps_absent` | S10 Corps vide : 400 REQUETE_MAL_FORMEE. | EX11 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s10_json_valide_mais_pas_un_objet` | S10 JSON valide qui n'est pas un objet : 422 DONNEES_INVALIDES. | EX11 | 4 | ✅ Réussi ×4, ❌ Échoué ×0 |
| `test_s10_mauvais_content_type` | S10 Content-Type non JSON : 415 TYPE_CONTENU_NON_SUPPORTE. | EX11 | 1 | ✅ Réussi, ❌ Échoué |
| `test_s10_corps_trop_volumineux` | S10 Corps > 10 ko : 413 REQUETE_TROP_VOLUMINEUSE (protection simple). | EX11 | 1 | ✅ Réussi, ❌ Échoué |
| `test_methode_non_autorisee` | TA01 GET /predict n'est pas autorisé : 405. | EX11 | 1 | ✅ Réussi, ❌ Échoué |
| `test_health_ok` | TA02 Service disponible : GET /health renvoie 200 et la version chargée. | EX05 | 1 | ✅ Réussi, ❌ Échoué |
| `test_model_info_contrat` | TA03 GET /model-info expose version, empreinte, variables, seuils et métriques. | EX16 | 1 | ✅ Réussi, ❌ Échoué |
| `test_niveau_de_risque_selon_seuils` | TA04 Le niveau de risque respecte les seuils documentés (bornes incluses). | EX20 | 6 | ✅ Réussi ×6, ❌ Échoué ×0 |
| `test_risque_eleve_exige_analyse` | TA05 Une demande à risque élevé exige une analyse complémentaire. | EX20 | 1 | ✅ Réussi, ❌ Échoué |
| `test_content_length_invalide` | TA06 En-tête Content-Length non numérique : 400 REQUETE_MAL_FORMEE. | EX11 | 1 | ✅ Réussi, ❌ Échoué |

### Intégration (`tests/test_integration.py`)

| Test | Description | Exigences | Cas | Résultat |
|---|---|---|---:|---|
| `test_pipeline_bout_en_bout` | TI01 Requête valide : chaque composant est appelé dans l'ordre et la sortie est exacte. | EX04, EX16, EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_metadonnees_coherentes_avec_le_modele_charge` | TI02 Version et empreinte cohérentes entre fichier, /model-info, /health et /predict. | EX16 | 1 | ✅ Réussi, ❌ Échoué |
| `test_prediction_par_lot_identique_a_l_unitaire` | TI03 Prédire 50 demandes en lot ou une par une donne les mêmes probabilités. | EX04, EX15 | 1 | ✅ Réussi, ❌ Échoué |
| `test_fichier_modele_absent` | TI04 Fichier modèle absent : ErreurModeleIndisponible avec message explicite. | EX05, EX17 | 1 | ✅ Réussi, ❌ Échoué |
| `test_metadonnees_absentes` | TI05 Métadonnées absentes : le modèle n'est pas chargé. | EX05, EX17 | 1 | ✅ Réussi, ❌ Échoué |
| `test_modele_altere_refuse_avant_deserialisation` | TI06 Fichier modifié (SHA-256 différent) : refusé SANS appeler joblib.load. | EX17 | 1 | ✅ Réussi, ❌ Échoué |
| `test_modele_corrompu` | TI07 Fichier illisible mais empreinte cohérente : erreur contrôlée, pas d'exception brute. | EX05, EX17 | 1 | ✅ Réussi, ❌ Échoué |
| `test_format_de_modele_inattendu` | TI08 Objet désérialisé au mauvais format : refusé. | EX05, EX17 | 2 | ✅ Réussi ×2, ❌ Échoué ×0 |
| `test_variables_du_modele_incompatibles_avec_le_code` | TI09 Modèle entraîné avec d'autres variables que le code : refusé au chargement. | EX05, EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_api_demarre_sans_modele_et_signale_503` | TI10 Au démarrage avec un modèle absent, l'API répond (503) au lieu de planter. | EX05 | 1 | ✅ Réussi, ❌ Échoué |
| `test_modele_decharge_en_cours_de_fonctionnement` | TI11 Modèle déchargé à chaud : 503, puis 200 après rechargement. | EX05 | 1 | ✅ Réussi, ❌ Échoué |
| `test_erreur_de_pretraitement` | TI12 Le prétraitement échoue : 500 ERREUR_INTERNE avec identifiant d'incident. | EX12, EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_variable_attendue_absente_apres_pretraitement` | TI13 Une variable disparaît entre validation et modèle : erreur 500 contrôlée. | EX12, EX21 | 1 | ✅ Réussi, ❌ Échoué |
| `test_dimensions_incompatibles` | TI14 Dimensions différentes de celles attendues par le modèle : 500 contrôlée. | EX12, EX21 | 3 | ✅ Réussi ×3, ❌ Échoué ×0 |
| `test_dimensions_incompatibles_niveau_service` | TI15 Le service refuse explicitement une matrice de mauvaise largeur. | EX12 | 1 | ✅ Réussi, ❌ Échoué |
| `test_exception_interne_du_modele` | TI16 Le modèle lève une exception : 500 sans message, ni type, ni chemin. | EX12 | 1 | ✅ Réussi, ❌ Échoué |
| `test_probabilite_aberrante_bloquee` | TI17 Une sortie du modèle hors [0, 1] ou non finie n'est jamais renvoyée au client. | EX04, EX12 | 4 | ✅ Réussi ×4, ❌ Échoué ×0 |
| `test_erreur_imprevue_attrapee_par_le_gestionnaire_global` | TI18 Exception non prévue (ZeroDivisionError) : 500 générique, pas de trace. | EX12 | 1 | ✅ Réussi, ❌ Échoué |

### Robustesse (`tests/test_robustness.py`)

| Test | Description | Exigences | Cas | Résultat |
|---|---|---|---:|---|
| `test_valeur_null` | TR01 Valeur JSON null sur un champ : 422, le champ est identifié. | EX06 | 5 | ✅ Réussi ×5, ❌ Échoué ×0 |
| `test_plusieurs_champs_manquants_tous_signales` | TR02 Plusieurs champs absents : toutes les erreurs sont listées en une réponse. | EX06 | 1 | ✅ Réussi, ❌ Échoué |
| `test_valeurs_non_numeriques` | TR03 Texte, liste, objet ou booléen dans un champ numérique : 422 (10 × 5 cas). | EX02, EX03, EX08 | 50 | ✅ Réussi ×50, ❌ Échoué ×0 |
| `test_valeurs_non_finies_dans_le_json_brut` | TR04 NaN / Infinity / 1e400 (débordement) envoyés tels quels : 422 (5 × 5 cas). | EX10 | 25 | ✅ Réussi ×25, ❌ Échoué ×0 |
| `test_valeurs_aux_bornes_acceptees` | TR05 Chaque borne autorisée est acceptée et donne une probabilité valide. | EX01, EX02, EX03, EX04, EX08 | 10 | ✅ Réussi ×10, ❌ Échoué ×0 |
| `test_valeurs_juste_hors_bornes_rejetees` | TR06 La première valeur au-delà de chaque borne est rejetée. | EX01, EX02, EX03, EX08, EX13 | 10 | ✅ Réussi ×10, ❌ Échoué ×0 |
| `test_entree_valide_hors_distribution_signalee` | TR07 Entrée valide mais loin des données d'entraînement : 200 + alerte + analyse. | EX04, EX14 | 7 | ✅ Réussi ×7, ❌ Échoué ×0 |
| `test_entree_typique_sans_alerte` | TR08 Une demande typique ne déclenche aucune alerte (pas de fausse alerte). | EX14 | 1 | ✅ Réussi, ❌ Échoué |
| `test_schema_incorrect` | TR09 Schéma incorrect (imbriqué, renommé, tableau…) : 422, jamais 200 ni 500. | EX06, EX09 | 6 | ✅ Réussi ×6, ❌ Échoué ×0 |
| `test_cles_dupliquees_dans_le_json` | TR10 Clé dupliquée : le parseur garde la dernière valeur, qui est validée. | EX11 | 1 | ✅ Réussi, ❌ Échoué |
| `test_encodage_non_utf8` | TR11 Corps non UTF-8 : 400 ou 422, pas d'erreur 500. | EX11 | 1 | ✅ Réussi, ❌ Échoué |
| `test_determinisme_appels_repetes` | TR12 La même requête envoyée 20 fois donne exactement la même réponse. | EX15 | 1 | ✅ Réussi, ❌ Échoué |
| `test_ordre_des_champs_sans_effet` | TR13 L'ordre des clés JSON n'influence pas la prédiction. | EX15 | 1 | ✅ Réussi, ❌ Échoué |
| `test_entier_et_decimal_equivalents` | TR14 revenu 250000 et 250000.0 donnent la même probabilité. | EX15 | 1 | ✅ Réussi, ❌ Échoué |
| `test_propriete_toute_entree_valide_donne_une_probabilite` | TR15 Propriété : toute entrée valide (150 tirages) → 200 et probabilité dans [0, 1]. | EX04, EX14 | 1 | ✅ Réussi, ❌ Échoué |
| `test_fuzzing_aucune_erreur_500` | TR16 Fuzzing (150 corps aléatoires) : jamais de 500 ; 200 ⇒ probabilité valide. | EX06, EX10, EX12 | 1 | ✅ Réussi, ❌ Échoué |
| `test_monotonie_montant` | TR17 Propriété métier : à profil égal, un montant plus élevé ne baisse pas le risque. | EX19 | 1 | ✅ Réussi, ❌ Échoué |
| `test_monotonie_montant_domaine_complet` | TR17b Anomalie connue : hors domaine réaliste, le risque baisse quand le montant monte. | EX19 | 1 | ⚠️ Anomalie connue, ✅ Réussi, ❌ Échoué |
| `test_monotonie_revenu` | TR18 Propriété métier : à profil égal, un revenu plus élevé ne hausse pas le risque. | EX19 | 1 | ✅ Réussi, ❌ Échoué |

### Non-régression (`tests/test_regression.py`)

| Test | Description | Exigences | Cas | Résultat |
|---|---|---|---:|---|
| `test_tolerances_definies_avant_comparaison` | TN01 Le fichier de tolérances existe, est daté et couvre rappel, F1 et ROC-AUC. | EX07 | 1 | ✅ Réussi, ❌ Échoué |
| `test_modele_courant_identifie` | TN02 Le modèle versionné est identifié : si son empreinte change, la baseline aussi. | EX07, EX16 | 1 | ✅ Réussi, ❌ Échoué |
| `test_sorties_du_pipeline_conformes_au_contrat` | TN03 Sur 500 demandes réelles du jeu de test, chaque sortie respecte le contrat. | EX04, EX07 | 1 | ✅ Réussi, ❌ Échoué |
| `test_pas_de_regression_des_metriques` | TN04 Chaque métrique reste dans la tolérance de baisse et au-dessus de son plancher. | EX07 | 5 | ✅ Réussi ×5, ❌ Échoué ×0 |
| `test_rappel_et_f1_detectent_une_baisse_excessive` | TN05 Le comparateur signale une baisse de rappel ou de F1 au-delà de la tolérance. | EX07 | 1 | ✅ Réussi, ❌ Échoué |
| `test_candidate_degradee_rejetee` | TN06 Un modèle réellement dégradé (étiquettes mélangées) est REJETÉ par le comparateur. | EX07 | 1 | ✅ Réussi, ❌ Échoué |
| `test_predictions_de_reference` | TN07 Les 200 probabilités de référence sont reproduites (tolérance selon la version). | EX07, EX15 | 1 | ✅ Réussi, ❌ Échoué |
| `test_coherence_apres_sauvegarde_et_rechargement` | TN08 Modèle sauvegardé puis rechargé : probabilités identiques (≤ 1e-12) sur 4 000 cas. | EX15 | 1 | ✅ Réussi, ❌ Échoué |
| `test_cycle_complet_entrainement_sauvegarde_service` | TN09 Entraîner → sauvegarder (avec SHA-256) → charger via le service → même résultat. | EX15 | 1 | ✅ Réussi, ❌ Échoué |
| `test_entrainement_reproductible` | TN10 Deux entraînements avec la même graine donnent des coefficients identiques. | EX15 | 1 | ✅ Réussi, ❌ Échoué |

### Performance (CI) (`tests/test_performance.py`)

| Test | Description | Exigences | Cas | Résultat |
|---|---|---|---:|---|
| `test_latence_p95_api` | TPF01 P95 de POST /predict (client de test, 200 appels) ≤ 100 ms. | EX18 | 1 | ✅ Réussi, ❌ Échoué |
| `test_latence_p95_inference` | TPF02 P95 prétraitement + inférence d'une demande ≤ 10 ms. | EX18 | 1 | ✅ Réussi, ❌ Échoué |

### Démonstration CI (`tests/test_echec_volontaire.py`)

| Test | Description | Exigences | Cas | Résultat |
|---|---|---|---:|---|
| `test_echec_volontaire` | TCI01 Échec volontaire : ce test DOIT rendre le workflow rouge lorsqu'il est activé. | EX22 | 1 | ⏸ Ignoré, ✅ Réussi, ❌ Échoué |
