"""Module de validation : format et cohérence des données d'un demandeur.

Règles appliquées (voir reports/01_plan_de_test.md, EX01 à EX06, EX08 à EX10) :
* types stricts : un texte "250000" n'est pas un nombre, 12.0 n'est pas une durée entière,
  un booléen n'est pas un nombre ;
* valeurs finies uniquement (NaN et ±inf rejetés) ;
* bornes métier définies dans app.config ;
* champs supplémentaires interdits ;
* cohérence croisée : ancienneté d'activité compatible avec l'âge.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator

from app import config


class DemandeCredit(BaseModel):
    """Contrat d'entrée de POST /predict."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    age: int = Field(..., ge=config.AGE_MIN, le=config.AGE_MAX, description="Âge en années")
    revenu_mensuel: float = Field(..., gt=0, le=config.REVENU_MAX, description="FCFA / mois")
    montant_credit: float = Field(..., gt=0, le=config.MONTANT_MAX, description="FCFA")
    duree_mois: int = Field(..., ge=config.DUREE_MIN, le=config.DUREE_MAX, description="Mois")
    anciennete_activite: float = Field(
        ..., ge=0, le=config.ANCIENNETE_MAX, description="Années d'activité"
    )

    @field_validator("anciennete_activite")
    @classmethod
    def _coherence_age_anciennete(cls, valeur: float, info: ValidationInfo) -> float:
        age = info.data.get("age")
        if age is None:  # l'âge est déjà en erreur : pas de contrôle croisé
            return valeur
        limite = age - config.AGE_DEBUT_ACTIVITE_MIN
        if valeur > limite:
            raise ValueError(
                f"incompatible avec l'âge ({age} ans) : au plus {limite} ans d'activité"
            )
        return valeur


class ErreurValidation(Exception):
    """Erreur contrôlée levée hors API (usage programmatique du module)."""

    def __init__(self, details: list[dict[str, str]]):
        self.details = details
        super().__init__("; ".join(f"{d['champ']}: {d['message']}" for d in details))


MESSAGES = {
    "missing": "champ obligatoire absent",
    "extra_forbidden": "champ non autorisé",
    "int_type": "un nombre entier est attendu",
    "float_type": "un nombre est attendu",
    "finite_number": "un nombre fini est attendu (NaN et infini refusés)",
    "greater_than": "valeur trop petite (doit être > {gt})",
    "greater_than_equal": "valeur trop petite (doit être >= {ge})",
    "less_than_equal": "valeur trop grande (doit être <= {le})",
    "model_attributes_type": "un objet JSON est attendu",
    "model_type": "un objet JSON est attendu",
}


def formater_erreurs(erreurs: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Transforme les erreurs pydantic en messages lisibles, SANS recopier la valeur reçue.

    Ne pas renvoyer `input` évite de refléter des données personnelles (revenu, âge)
    dans les journaux ou les réponses d'erreur.
    """
    details = []
    for err in erreurs:
        loc = [str(p) for p in err.get("loc", ()) if p != "body"]
        type_err = str(err.get("type", "inconnu"))
        gabarit = MESSAGES.get(type_err)
        if gabarit:
            try:
                message = gabarit.format(**(err.get("ctx") or {}))
            except (KeyError, IndexError):
                message = gabarit
        else:
            message = str(err.get("msg", "valeur invalide")).removeprefix("Value error, ")
        details.append(
            {"champ": ".".join(loc) or "(requête)", "type": type_err, "message": message}
        )
    return details


def valider_demande(donnees: Any) -> DemandeCredit:
    """Valide un dictionnaire Python ; lève ErreurValidation en cas d'échec."""
    if not isinstance(donnees, dict):
        raise ErreurValidation(
            [{"champ": "(requête)", "type": "type_objet", "message": "un objet JSON est attendu"}]
        )
    try:
        return DemandeCredit.model_validate(donnees)
    except ValidationError as exc:
        raise ErreurValidation(formater_erreurs(exc.errors())) from None
