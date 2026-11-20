"""Chargement du modèle versionné, prédiction et interprétation métier.

Le fichier modèle (joblib) est accompagné d'un fichier de métadonnées JSON contenant son
empreinte SHA-256. L'empreinte est vérifiée AVANT la désérialisation : joblib/pickle peut
exécuter du code arbitraire, on ne charge donc jamais un fichier modifié.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app import config
from app.preprocessing import VARIABLES_MODELE, transformer
from app.validation import DemandeCredit

journal = logging.getLogger("creditrisk.prediction")


class ErreurModeleIndisponible(Exception):
    """Le modèle n'est pas chargé ou ne peut pas l'être."""


class ErreurPrediction(Exception):
    """Erreur interne pendant l'inférence (dimensions, valeur aberrante, exception du modèle)."""


def empreinte_sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(65536), b""):
            h.update(bloc)
    return h.hexdigest()


def chemin_metadonnees(chemin_modele: Path) -> Path:
    return Path(chemin_modele).with_suffix(".json")


def niveau_risque(probabilite: float) -> str:
    if probabilite >= config.SEUIL_RISQUE_ELEVE:
        return "eleve"
    if probabilite >= config.SEUIL_RISQUE_MODERE:
        return "modere"
    return "faible"


RECOMMANDATIONS = {
    "faible": "Avis favorable : instruction standard du dossier.",
    "modere": "Analyse complémentaire recommandée avant décision.",
    "eleve": "Avis défavorable sauf garanties ou éléments complémentaires.",
}
RECOMMANDATION_HORS_DOMAINE = (
    "Dossier inhabituel (hors du domaine d'entraînement) : score peu fiable, "
    "vérification manuelle requise."
)


class ServiceModele:
    """Encapsule le modèle chargé. Une instance est partagée par l'API."""

    def __init__(self) -> None:
        self.bundle: dict[str, Any] | None = None
        self.metadonnees: dict[str, Any] | None = None
        self.erreur_chargement: str | None = None

    # ------------------------------------------------------------------ chargement
    def charger(self, chemin: Path | str) -> None:
        chemin = Path(chemin)
        self.bundle = None
        self.metadonnees = None
        try:
            meta_path = chemin_metadonnees(chemin)
            if not chemin.is_file():
                raise ErreurModeleIndisponible(f"fichier modèle introuvable : {chemin.name}")
            if not meta_path.is_file():
                raise ErreurModeleIndisponible(f"métadonnées introuvables : {meta_path.name}")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            attendu = meta.get("sha256")
            obtenu = empreinte_sha256(chemin)
            if attendu != obtenu:
                raise ErreurModeleIndisponible("empreinte SHA-256 du modèle invalide")
            bundle = joblib.load(chemin)
            if not isinstance(bundle, dict) or "pipeline" not in bundle:
                raise ErreurModeleIndisponible("format de modèle inattendu")
            if tuple(bundle.get("variables", ())) != VARIABLES_MODELE:
                raise ErreurModeleIndisponible("variables du modèle incompatibles avec le code")
        except ErreurModeleIndisponible as exc:
            self.erreur_chargement = str(exc)
            journal.error("Chargement du modèle impossible : %s", exc)
            raise
        except Exception as exc:  # fichier corrompu, version sklearn incompatible...
            self.erreur_chargement = f"modèle illisible ({type(exc).__name__})"
            journal.exception("Chargement du modèle impossible")
            raise ErreurModeleIndisponible(self.erreur_chargement) from exc
        self.bundle = bundle
        self.metadonnees = meta
        self.erreur_chargement = None
        journal.info("Modèle %s chargé", meta.get("version"))

    def decharger(self) -> None:
        self.bundle = None
        self.metadonnees = None
        self.erreur_chargement = "modèle déchargé"

    @property
    def est_disponible(self) -> bool:
        return self.bundle is not None

    # ------------------------------------------------------------------ inférence
    def predire_probabilites(self, X: np.ndarray) -> np.ndarray:
        if not self.est_disponible:
            raise ErreurModeleIndisponible(self.erreur_chargement or "modèle non chargé")
        pipeline = self.bundle["pipeline"]
        attendu = getattr(pipeline, "n_features_in_", len(VARIABLES_MODELE))
        if X.ndim != 2 or X.shape[1] != attendu:
            raise ErreurPrediction(
                f"dimensions incompatibles : {X.shape} reçu, {attendu} variables attendues"
            )
        try:
            proba = pipeline.predict_proba(X)[:, 1]
        except Exception as exc:
            raise ErreurPrediction(f"échec de l'inférence ({type(exc).__name__})") from exc
        proba = np.asarray(proba, dtype=float)
        if not np.all(np.isfinite(proba)) or np.any((proba < 0) | (proba > 1)):
            raise ErreurPrediction("probabilité hors de [0, 1] ou non finie")
        return proba

    def alertes(self, demande: DemandeCredit) -> list[str]:
        """Signale les entrées valides mais inhabituelles (hors domaine d'entraînement)."""
        alertes = []
        domaine = (self.bundle or {}).get("domaine", {})
        valeurs = demande.model_dump()
        for variable, (bas, haut) in domaine.items():
            v = valeurs.get(variable)
            if v is not None and not (bas <= v <= haut):
                alertes.append(f"hors_domaine:{variable}")
        mensualite = demande.montant_credit / demande.duree_mois
        if mensualite / demande.revenu_mensuel > config.TAUX_ENDETTEMENT_ALERTE:
            alertes.append("mensualite_superieure_au_revenu")
        return alertes

    def predire(self, demande: DemandeCredit) -> dict[str, Any]:
        X = transformer([demande])
        p = float(self.predire_probabilites(X)[0])  # finitude et bornes déjà contrôlées
        niveau = niveau_risque(p)
        alertes = self.alertes(demande)
        # Correction de l'anomalie A03 : un avis « favorable » n'est plus affiché
        # lorsque le dossier sort du domaine où le modèle a été entraîné.
        recommandation = RECOMMANDATIONS[niveau]
        if alertes and niveau == "faible":
            recommandation = RECOMMANDATION_HORS_DOMAINE
        return {
            "probabilite_defaut": round(p, 6),
            "niveau_risque": niveau,
            "recommandation": recommandation,
            "analyse_complementaire_requise": niveau != "faible" or bool(alertes),
            "alertes": alertes,
            "version_modele": self.metadonnees.get("version"),
        }

    def informations(self) -> dict[str, Any]:
        if not self.est_disponible:
            raise ErreurModeleIndisponible(self.erreur_chargement or "modèle non chargé")
        m = self.metadonnees
        return {
            "nom": m.get("nom"),
            "version": m.get("version"),
            "algorithme": m.get("algorithme"),
            "date_entrainement": m.get("date_entrainement"),
            "sha256": m.get("sha256"),
            "variables_entree": list(config.VARIABLES_ENTREE),
            "variables_modele": list(VARIABLES_MODELE),
            "seuils_risque": {
                "modere": config.SEUIL_RISQUE_MODERE,
                "eleve": config.SEUIL_RISQUE_ELEVE,
            },
            "metriques_test": m.get("metriques_test"),
            "donnees": m.get("donnees"),
        }
