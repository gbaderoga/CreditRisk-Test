"""API de prédiction du risque de défaut (FastAPI).

Endpoints :
* GET  /health      disponibilité du service et du modèle (200 ou 503)
* POST /predict     estimation du risque d'un demandeur (200, 400, 413, 415, 422, 500, 503)
* GET  /model-info  métadonnées de la version du modèle (200 ou 503)

Toutes les erreurs suivent le même format, sans trace technique :
    {"erreur": {"code": "...", "message": "...", "details": [...], "id_incident": "..."}}
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import config
from app.prediction import ErreurModeleIndisponible, ErreurPrediction, ServiceModele
from app.preprocessing import ErreurPretraitement
from app.validation import DemandeCredit, formater_erreurs

journal = logging.getLogger("creditrisk.api")

TAILLE_MAX_REQUETE = 10_000  # octets ; une demande valide en fait environ 150

service = ServiceModele()


@asynccontextmanager
async def cycle_de_vie(application: FastAPI):
    # L'API démarre même sans modèle : /health signale l'indisponibilité (EX05).
    with contextlib.suppress(ErreurModeleIndisponible):
        service.charger(config.CHEMIN_MODELE)
    yield


app = FastAPI(
    title="CreditRisk API",
    version="1.0.0",
    description="Estimation du risque de défaut de remboursement (prototype, aide à la décision).",
    lifespan=cycle_de_vie,
)


def obtenir_service() -> ServiceModele:
    return service


# ---------------------------------------------------------------- schémas de sortie
class ReponsePrediction(BaseModel):
    probabilite_defaut: float
    niveau_risque: str
    recommandation: str
    analyse_complementaire_requise: bool
    alertes: list[str]
    version_modele: str


def erreur(statut: int, code: str, message: str, details: list | None = None, incident=None):
    corps: dict[str, Any] = {"code": code, "message": message}
    if details:
        corps["details"] = details
    if incident:
        corps["id_incident"] = incident
    return JSONResponse(status_code=statut, content={"erreur": corps})


# ---------------------------------------------------------------- middleware
@app.middleware("http")
async def controler_requete(request: Request, call_next):
    if request.method == "POST":
        type_contenu = request.headers.get("content-type", "")
        if type_contenu.split(";")[0].strip().lower() != "application/json":
            return erreur(415, "TYPE_CONTENU_NON_SUPPORTE", "Content-Type application/json requis.")
    longueur = request.headers.get("content-length")
    if longueur is not None:
        try:
            trop_grand = int(longueur) > TAILLE_MAX_REQUETE
        except ValueError:
            return erreur(400, "REQUETE_MAL_FORMEE", "En-tête Content-Length invalide.")
        if trop_grand:
            return erreur(413, "REQUETE_TROP_VOLUMINEUSE", "Corps de requête trop volumineux.")
    return await call_next(request)


# ---------------------------------------------------------------- gestion des erreurs
@app.exception_handler(RequestValidationError)
async def _validation(request: Request, exc: RequestValidationError):
    erreurs = exc.errors()
    if any(e.get("type") == "json_invalid" for e in erreurs):
        return erreur(400, "REQUETE_MAL_FORMEE", "Le corps de la requête n'est pas un JSON valide.")
    if any(e.get("type") == "missing" and tuple(e.get("loc", ())) == ("body",) for e in erreurs):
        return erreur(400, "REQUETE_MAL_FORMEE", "Le corps de la requête est absent.")
    return erreur(
        422,
        "DONNEES_INVALIDES",
        "Les données du demandeur ne respectent pas le contrat d'entrée.",
        formater_erreurs(erreurs),
    )


@app.exception_handler(ErreurModeleIndisponible)
async def _indisponible(request: Request, exc: ErreurModeleIndisponible):
    return erreur(503, "MODELE_INDISPONIBLE", "Le modèle de prédiction est indisponible.")


@app.exception_handler(ErreurPretraitement)
@app.exception_handler(ErreurPrediction)
async def _interne_connue(request: Request, exc: Exception):
    incident = uuid.uuid4().hex[:12]
    journal.error("Incident %s (%s) : %s", incident, type(exc).__name__, exc)
    return erreur(500, "ERREUR_INTERNE", "La prédiction n'a pas pu être calculée.", None, incident)


@app.exception_handler(Exception)
async def _interne(request: Request, exc: Exception):
    incident = uuid.uuid4().hex[:12]
    journal.exception("Incident %s : erreur non prévue", incident)
    return erreur(500, "ERREUR_INTERNE", "Erreur interne du service.", None, incident)


# ---------------------------------------------------------------- endpoints
@app.get("/health")
def health(svc: ServiceModele = Depends(obtenir_service)):
    if svc.est_disponible:
        return {"statut": "ok", "modele_charge": True, "version_modele": svc.metadonnees["version"]}
    return JSONResponse(
        status_code=503,
        content={"statut": "indisponible", "modele_charge": False},
    )


@app.post("/predict", response_model=ReponsePrediction)
def predict(demande: DemandeCredit, svc: ServiceModele = Depends(obtenir_service)):
    return svc.predire(demande)


@app.get("/model-info")
def model_info(svc: ServiceModele = Depends(obtenir_service)):
    return svc.informations()
