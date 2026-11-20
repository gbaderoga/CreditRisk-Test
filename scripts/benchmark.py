"""Mesures de performance : latence d'inférence, latence HTTP, P95, débit, charge progressive.

Usage :
    python -m scripts.benchmark          # écrit reports/resultats/performance.json

Démarre l'API avec uvicorn (1 processus) sur 127.0.0.1:8765, puis mesure :
1. la latence d'inférence (prétraitement + modèle, sans HTTP) ;
2. la latence HTTP séquentielle de POST /predict ;
3. le débit et la latence sous charge progressive (1 à 32 clients simultanés).
"""

from __future__ import annotations

import contextlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import numpy as np
import sklearn

from app import config
from app.prediction import ServiceModele
from app.preprocessing import transformer

URL = "http://127.0.0.1:8765"
DEMANDE = {
    "age": 35,
    "revenu_mensuel": 250000,
    "montant_credit": 1000000,
    "duree_mois": 12,
    "anciennete_activite": 4,
}
NIVEAUX_CHARGE = (1, 2, 4, 8, 16, 32)
DUREE_PALIER_S = 8.0


def stats(ms: list[float]) -> dict:
    a = np.asarray(ms)
    return {
        "n": int(a.size),
        "moyenne_ms": round(float(a.mean()), 3),
        "p50_ms": round(float(np.percentile(a, 50)), 3),
        "p95_ms": round(float(np.percentile(a, 95)), 3),
        "p99_ms": round(float(np.percentile(a, 99)), 3),
        "max_ms": round(float(a.max()), 3),
    }


def configuration() -> dict:
    cpu = "inconnu"
    with contextlib.suppress(OSError), open("/proc/cpuinfo", encoding="utf-8") as f:
        for ligne in f:
            if ligne.startswith("model name"):
                cpu = ligne.split(":", 1)[1].strip()
                break
    memoire = None
    with contextlib.suppress(ValueError, OSError):
        memoire = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 1)
    import fastapi
    import uvicorn

    return {
        "cpu": cpu,
        "coeurs_logiques": os.cpu_count(),
        "memoire_go": memoire,
        "os": platform.platform(),
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
        "fastapi": fastapi.__version__,
        "uvicorn": uvicorn.__version__,
        "httpx": httpx.__version__,
        "serveur": "uvicorn, 1 processus, client et serveur sur la même machine",
    }


def mesurer_inference(n: int = 5000) -> dict:
    svc = ServiceModele()
    svc.charger(config.CHEMIN_MODELE)
    for _ in range(200):
        svc.predire_probabilites(transformer([DEMANDE]))
    unitaire, modele_seul = [], []
    X = transformer([DEMANDE])
    for _ in range(n):
        t0 = time.perf_counter()
        svc.predire_probabilites(transformer([DEMANDE]))
        unitaire.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        svc.bundle["pipeline"].predict_proba(X)
        modele_seul.append((time.perf_counter() - t0) * 1000)
    lot = [DEMANDE] * 1000
    t0 = time.perf_counter()
    for _ in range(20):
        svc.predire_probabilites(transformer(lot))
    debit_lot = 20 * 1000 / (time.perf_counter() - t0)
    return {
        "pretraitement_plus_modele": stats(unitaire),
        "modele_seul": stats(modele_seul),
        "debit_par_lot_de_1000_par_s": round(debit_lot),
    }


def demarrer_serveur() -> subprocess.Popen:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
            "--log-level",
            "warning",
            "--no-access-log",
        ],
        cwd=config.RACINE,
    )
    for _ in range(100):
        try:
            if httpx.get(f"{URL}/health", timeout=0.5).status_code == 200:
                return proc
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    proc.kill()
    raise RuntimeError("le serveur n'a pas démarré")


def mesurer_http_sequentiel(n: int = 2000) -> dict:
    with httpx.Client(base_url=URL) as c:
        for _ in range(100):
            c.post("/predict", json=DEMANDE)
        durees, erreurs = [], 0
        for _ in range(n):
            t0 = time.perf_counter()
            r = c.post("/predict", json=DEMANDE)
            durees.append((time.perf_counter() - t0) * 1000)
            erreurs += r.status_code != 200
    return {**stats(durees), "erreurs": erreurs}


def palier(n_clients: int, duree_s: float = DUREE_PALIER_S) -> dict:
    fin = time.perf_counter() + duree_s
    durees: list[float] = []
    erreurs = [0]
    verrou = threading.Lock()

    def client():
        local, err = [], 0
        with httpx.Client(base_url=URL, timeout=10) as c:
            while time.perf_counter() < fin:
                t0 = time.perf_counter()
                try:
                    ok = c.post("/predict", json=DEMANDE).status_code == 200
                except httpx.HTTPError:
                    ok = False
                local.append((time.perf_counter() - t0) * 1000)
                err += not ok
        with verrou:
            durees.extend(local)
            erreurs[0] += err

    debut = time.perf_counter()
    with ThreadPoolExecutor(n_clients) as ex:
        for _ in range(n_clients):
            ex.submit(client)
    ecoule = time.perf_counter() - debut
    return {
        "clients": n_clients,
        **stats(durees),
        "debit_req_s": round(len(durees) / ecoule, 1),
        "erreurs": erreurs[0],
        "taux_erreur": round(erreurs[0] / max(len(durees), 1), 4),
    }


def main() -> None:
    resultats = {"configuration": configuration(), "date": time.strftime("%Y-%m-%d %H:%M")}
    print("Inférence…")
    resultats["inference"] = mesurer_inference()
    proc = demarrer_serveur()
    try:
        print("HTTP séquentiel…")
        resultats["http_sequentiel"] = mesurer_http_sequentiel()
        resultats["charge_progressive"] = []
        for n in NIVEAUX_CHARGE:
            r = palier(n)
            print(f"  {n:>2} clients : {r['debit_req_s']:>7} req/s, P95 {r['p95_ms']} ms")
            resultats["charge_progressive"].append(r)
    finally:
        proc.terminate()
        proc.wait(10)
    sortie = config.RACINE / "reports" / "resultats"
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "performance.json").write_text(
        json.dumps(resultats, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in resultats.items() if k != "charge_progressive"}, indent=1))


if __name__ == "__main__":
    main()
