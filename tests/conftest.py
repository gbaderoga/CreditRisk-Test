"""Fixtures partagées et traçabilité exigences ↔ tests.

Chaque test porte un marqueur `@pytest.mark.exigence("EXnn", ...)`. Avec l'option
`--rapport-exigences=chemin.json`, les résultats sont exportés par exigence : c'est la
source du tableau de résultats et de la matrice de traçabilité (reports/).
"""

from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app, obtenir_service, service
from app.prediction import ServiceModele

DEMANDE_VALIDE = {
    "age": 35,
    "revenu_mensuel": 250000,
    "montant_credit": 1000000,
    "duree_mois": 12,
    "anciennete_activite": 4,
}


# ----------------------------------------------------------------------- fixtures
@pytest.fixture
def demande() -> dict:
    """Copie fraîche d'une demande valide (modifiable par le test)."""
    return dict(DEMANDE_VALIDE)


@pytest.fixture
def client():
    """Client HTTP avec cycle de vie (chargement réel du modèle versionné)."""
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    if not service.est_disponible:
        service.charger(config.CHEMIN_MODELE)


@pytest.fixture
def client_sans_exception():
    """Client qui renvoie la réponse HTTP 500 au lieu de propager l'exception au test."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def service_indisponible():
    """Service dont le modèle n'a pas pu être chargé."""
    svc = ServiceModele()
    svc.erreur_chargement = "modèle non chargé (test)"
    app.dependency_overrides[obtenir_service] = lambda: svc
    yield svc
    app.dependency_overrides.clear()


@pytest.fixture
def copie_modele(tmp_path) -> Path:
    """Copie du modèle et de ses métadonnées dans un dossier temporaire (modifiable)."""
    src = Path(config.CHEMIN_MODELE)
    dst = tmp_path / src.name
    shutil.copy(src, dst)
    shutil.copy(src.with_suffix(".json"), dst.with_suffix(".json"))
    return dst


@pytest.fixture(scope="session")
def service_charge() -> ServiceModele:
    svc = ServiceModele()
    svc.charger(config.CHEMIN_MODELE)
    return svc


# ----------------------------------------------------------------------- traçabilité
def pytest_addoption(parser):
    parser.addoption(
        "--rapport-exigences",
        default=None,
        help="Exporter les résultats par exigence dans ce fichier JSON",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "exigence(*ids): exigence(s) vérifiée(s) par le test")
    config._resultats_exigences = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    rapport = (yield).get_result()
    if rapport.when == "call" or (rapport.when == "setup" and rapport.outcome != "passed"):
        ids = [i for m in item.iter_markers("exigence") for i in m.args]
        if hasattr(rapport, "wasxfail"):
            resultat = "echec_attendu"  # anomalie connue, documentée (xfail strict)
        else:
            resultat = {"passed": "reussi", "failed": "echoue", "skipped": "ignore"}[
                rapport.outcome
            ]
        item.config._resultats_exigences.append(
            {
                "test": item.nodeid,
                "exigences": sorted(set(ids)),
                "resultat": resultat,
                "duree_s": round(rapport.duration, 4),
                "description": (item.function.__doc__ or "").strip().split("\n")[0],
            }
        )


def pytest_sessionfinish(session, exitstatus):
    chemin = session.config.getoption("--rapport-exigences")
    if not chemin:
        return
    resultats = session.config._resultats_exigences
    cles = ("reussi", "echoue", "ignore", "echec_attendu")
    par_exigence = defaultdict(lambda: {"tests": 0, **dict.fromkeys(cles, 0)})
    for r in resultats:
        for ex in r["exigences"] or ["(aucune)"]:
            par_exigence[ex]["tests"] += 1
            par_exigence[ex][r["resultat"]] += 1
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    Path(chemin).write_text(
        json.dumps(
            {"tests": resultats, "par_exigence": dict(sorted(par_exigence.items()))},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
