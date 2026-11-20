"""Test de performance léger, exécuté en CI (le rapport complet : scripts/benchmark.py)."""

from __future__ import annotations

import time

import numpy as np
import pytest

from app.preprocessing import transformer

OBJECTIF_P95_API_MS = 100.0  # objectif du plan de test (EX18), marge large pour la CI
OBJECTIF_P95_INFERENCE_MS = 10.0


@pytest.mark.exigence("EX18")
def test_latence_p95_api(client, demande):
    """TPF01 P95 de POST /predict (client de test, 200 appels) ≤ 100 ms."""
    for _ in range(20):  # échauffement
        client.post("/predict", json=demande)
    durees = []
    for _ in range(200):
        t0 = time.perf_counter()
        assert client.post("/predict", json=demande).status_code == 200
        durees.append((time.perf_counter() - t0) * 1000)
    assert np.percentile(durees, 95) <= OBJECTIF_P95_API_MS


@pytest.mark.exigence("EX18")
def test_latence_p95_inference(service_charge, demande):
    """TPF02 P95 prétraitement + inférence d'une demande ≤ 10 ms."""
    durees = []
    for _ in range(300):
        t0 = time.perf_counter()
        service_charge.predire_probabilites(transformer([demande]))
        durees.append((time.perf_counter() - t0) * 1000)
    assert np.percentile(durees, 95) <= OBJECTIF_P95_INFERENCE_MS
