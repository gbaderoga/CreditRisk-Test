"""Module de prétraitement : construction des variables attendues par le modèle.

Le modèle ne reçoit pas les 5 variables brutes mais 6 variables dérivées, dans un ordre
fixe (VARIABLES_MODELE). La standardisation est faite *dans* le pipeline scikit-learn
sauvegardé, ce qui garantit qu'elle a été ajustée sur l'entraînement uniquement.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from app.config import VARIABLES_ENTREE

VARIABLES_MODELE: tuple[str, ...] = (
    "age",
    "log_revenu",
    "log_montant",
    "duree_mois",
    "anciennete_activite",
    "log_taux_endettement",
)


class ErreurPretraitement(Exception):
    """Le prétraitement n'a pas pu produire un vecteur exploitable."""


def _en_dict(demande: Any) -> Mapping[str, Any]:
    if hasattr(demande, "model_dump"):
        return demande.model_dump()
    if isinstance(demande, Mapping):
        return demande
    raise ErreurPretraitement(f"type de demande non pris en charge : {type(demande).__name__}")


def construire_variables(demande: Any) -> dict[str, float]:
    """Calcule les variables dérivées d'une demande (déjà validée)."""
    d = _en_dict(demande)
    manquantes = [v for v in VARIABLES_ENTREE if v not in d]
    if manquantes:
        raise ErreurPretraitement(f"variables absentes : {', '.join(manquantes)}")
    try:
        age = float(d["age"])
        revenu = float(d["revenu_mensuel"])
        montant = float(d["montant_credit"])
        duree = float(d["duree_mois"])
        anciennete = float(d["anciennete_activite"])
    except (TypeError, ValueError) as exc:
        raise ErreurPretraitement("variable non numérique") from exc

    if revenu <= 0 or montant <= 0 or duree <= 0:
        raise ErreurPretraitement("revenu, montant et durée doivent être strictement positifs")

    mensualite = montant / duree
    variables = {
        "age": age,
        "log_revenu": math.log(revenu),
        "log_montant": math.log(montant),
        "duree_mois": duree,
        "anciennete_activite": anciennete,
        "log_taux_endettement": math.log1p(mensualite / revenu),
    }
    if not all(math.isfinite(v) for v in variables.values()):
        raise ErreurPretraitement("le prétraitement a produit une valeur non finie")
    return variables


def transformer(demandes: Iterable[Any]) -> np.ndarray:
    """Transforme une ou plusieurs demandes en matrice (n, 6) dans l'ordre VARIABLES_MODELE."""
    lignes = [construire_variables(d) for d in demandes]
    if not lignes:
        raise ErreurPretraitement("aucune demande à transformer")
    # Correction de l'anomalie A01 : une variable dérivée manquante levait un KeyError brut.
    for ligne in lignes:
        manquantes = [v for v in VARIABLES_MODELE if v not in ligne]
        if manquantes:
            raise ErreurPretraitement(f"variables dérivées absentes : {', '.join(manquantes)}")
    return np.array([[ligne[v] for v in VARIABLES_MODELE] for ligne in lignes], dtype=float)
