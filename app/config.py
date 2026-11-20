"""Paramètres centralisés du système : bornes métier, chemins, seuils.

Toutes les valeurs testées par la suite de tests sont définies ici, une seule fois,
afin que le contrat documenté (README, plan de test) et le code ne divergent pas.
"""

from __future__ import annotations

import os
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# --- Modèle versionné --------------------------------------------------------
MODELE_PAR_DEFAUT = RACINE / "models" / "model_v1.joblib"
CHEMIN_MODELE = Path(os.environ.get("CREDITRISK_MODEL_PATH", MODELE_PAR_DEFAUT))

# --- Ordre des variables brutes (contrat d'entrée) ---------------------------
VARIABLES_ENTREE: tuple[str, ...] = (
    "age",
    "revenu_mensuel",
    "montant_credit",
    "duree_mois",
    "anciennete_activite",
)

# --- Bornes de validation (au-delà : rejet HTTP 422) -------------------------
# Elles décrivent ce qui est *possible* pour un demandeur, pas ce qui est fréquent.
AGE_MIN, AGE_MAX = 18, 75  # majorité légale ; âge maximal à l'échéance
REVENU_MAX = 100_000_000.0  # 100 M FCFA / mois
MONTANT_MAX = 500_000_000.0  # 500 M FCFA
DUREE_MIN, DUREE_MAX = 1, 120  # 1 mois à 10 ans
ANCIENNETE_MAX = 60.0  # années
AGE_DEBUT_ACTIVITE_MIN = 12  # anciennete <= age - 12 (cohérence)

# --- Interprétation métier de la probabilité ---------------------------------
SEUIL_RISQUE_MODERE = 0.20
SEUIL_RISQUE_ELEVE = 0.50

# --- Règles d'alerte "inhabituel mais valide" --------------------------------
TAUX_ENDETTEMENT_ALERTE = 1.0  # mensualité > revenu mensuel
