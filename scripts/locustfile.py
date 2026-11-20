"""Scénario de charge Locust (test local léger).

    uvicorn app.main:app --port 8765 &
    locust -f scripts/locustfile.py --host http://127.0.0.1:8765 --headless \
           -u 50 -r 2 -t 45s --csv reports/resultats/locust

Profil : agents de crédit qui saisissent des demandes (90 % valides, 10 % invalides)
et consultent occasionnellement /health et /model-info. Temps de réflexion 0,1 à 0,5 s.
"""

import random

from locust import HttpUser, between, task

VALIDE = {
    "age": 35,
    "revenu_mensuel": 250000,
    "montant_credit": 1000000,
    "duree_mois": 12,
    "anciennete_activite": 4,
}


class AgentDeCredit(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(18)
    def demande_valide(self):
        d = dict(VALIDE)
        d["age"] = random.randint(18, 75)
        d["anciennete_activite"] = round(random.uniform(0, min(60, d["age"] - 12)), 1)
        d["revenu_mensuel"] = random.choice([50_000, 150_000, 250_000, 800_000])
        d["montant_credit"] = random.choice([200_000, 1_000_000, 5_000_000])
        d["duree_mois"] = random.choice([6, 12, 24, 36])
        self.client.post("/predict", json=d, name="POST /predict (valide)")

    @task(2)
    def demande_invalide(self):
        with self.client.post(
            "/predict",
            json={**VALIDE, "age": -5},
            name="POST /predict (invalide)",
            catch_response=True,
        ) as r:
            if r.status_code == 422:
                r.success()
            else:
                r.failure(f"422 attendu, {r.status_code} reçu")

    @task(1)
    def sante(self):
        self.client.get("/health")

    @task(1)
    def info(self):
        self.client.get("/model-info")
