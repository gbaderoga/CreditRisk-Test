# Rapport de performance

Sources : `reports/resultats/performance.json` (`python -m scripts.benchmark`) et `reports/resultats/locust_*.csv` (Locust). Mesures du 20/11/2026.

## 1. Configuration

| Élément | Valeur |
|---|---|
| CPU | Intel Xeon @ 2,10 GHz, **2 cœurs logiques** (machine virtuelle partagée) |
| Mémoire | 7,8 Go |
| Système | Linux 6.18, x86_64 |
| Logiciels | Python 3.13.18, scikit-learn 1.9.1, FastAPI 0.165.0, uvicorn 0.54.0, httpx 0.28.1, Locust 2.47.0 |
| Serveur | `uvicorn app.main:app`, **1 processus**, sans journal d'accès |
| Client | Même machine (boucle locale 127.0.0.1) : client et serveur se partagent les 2 cœurs |

## 2. Objectif de performance proposé

**Usage** : un agent de crédit saisit une demande et attend l'avis à l'écran. Hypothèse de dimensionnement : 200 agents × 40 dossiers par jour ≈ 8 000 requêtes par jour, soit moins de 1 req/s en moyenne et, avec un pic à 10 fois la moyenne, environ 3 req/s.

| Indicateur | Objectif | Justification |
|---|---|---|
| P95 de `POST /predict`, côté serveur, ≤ 32 clients simultanés | **≤ 100 ms** | Le temps de réponse perçu doit rester sous la seconde, réseau mobile compris (souvent 300 à 600 ms en agence). 100 ms côté serveur laisse cette marge. |
| Débit soutenu | **≥ 20 req/s** | Environ 6 fois le pic estimé |
| Taux d'erreur sous charge | **0 %** | Une erreur oblige l'agent à ressaisir le dossier |
| P95 d'inférence (prétraitement + modèle) | **≤ 10 ms** | Laisse l'essentiel du budget au réseau et à la validation |

## 3. Résultats

### 3.1 Latence d'inférence (sans HTTP, 5 000 appels)

| Mesure | Moyenne | P50 | **P95** | P99 | Max |
|---|---:|---:|---:|---:|---:|
| Prétraitement + modèle | 0,26 ms | 0,23 ms | **0,40 ms** | 0,49 ms | 2,26 ms |
| Modèle seul (`predict_proba`) | 0,24 ms | 0,21 ms | 0,35 ms | 0,43 ms | 4,72 ms |

En lot de 1 000 demandes, le débit d'inférence atteint **≈ 429 000 demandes/s**. Le coût unitaire tient surtout au surcoût fixe de scikit-learn pour chaque appel, pas au calcul lui-même.

### 3.2 Latence HTTP séquentielle (1 client, 2 000 requêtes)

| Moyenne | P50 | **P95** | P99 | Max | Erreurs |
|---:|---:|---:|---:|---:|---:|
| 3,09 ms | 3,02 ms | **3,97 ms** | 5,32 ms | 8,77 ms | 0 |

Sur environ 3 ms, l'inférence ne représente que 0,26 ms (9 %). Le reste revient à HTTP, à la validation pydantic et à la sérialisation JSON.

### 3.3 Charge progressive (paliers de 8 s, clients en boucle fermée, sans temps de réflexion)

| Clients simultanés | Requêtes | Débit (req/s) | P50 (ms) | **P95 (ms)** | P99 (ms) | Erreurs |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 680 | 334,9 | 2,9 | **3,7** | 4,7 | 0 |
| 2 | 3 256 | 406,7 | 4,8 | **6,8** | 8,0 | 0 |
| 4 | 3 625 | 452,7 | 8,6 | **12,7** | 15,5 | 0 |
| 8 | 3 704 | 462,1 | 16,9 | **22,8** | 26,1 | 0 |
| 16 | 3 529 | 439,3 | 35,1 | **48,0** | 61,2 | 0 |
| 32 | 3 553 | 440,3 | 69,6 | **88,1** | 127,9 | 0 |

Le débit plafonne vers **450 req/s dès 4 clients**. Au-delà, la latence augmente proportionnellement au nombre de clients (≈ 2,2 ms × clients), ce qui est le signe d'une file d'attente sur un serveur saturé et non d'une dégradation. Comme le client Python partage les 2 cœurs avec le serveur, ce plafond **sous-estime** la capacité réelle du serveur.

### 3.4 Scénario réaliste Locust (montée de 0 à 50 utilisateurs à 2/s, 45 s)

Profil : 82 % de demandes valides et variées, 9 % de demandes invalides (422 attendu), 9 % de `/health` et `/model-info` ; temps de réflexion de 0,1 à 0,5 s.

| Requête | Nombre | Échecs | Médiane | P95 | P99 | Max |
|---|---:|---:|---:|---:|---:|---:|
| `POST /predict` (valide) | 4 384 | 0 | 5 ms | **12 ms** | 16 ms | 28 ms |
| `POST /predict` (invalide → 422) | 501 | 0 | 3 ms | 7 ms | 10 ms | 22 ms |
| Toutes requêtes | 5 377 | **0** | 5 ms | **11 ms** | 16 ms | 28 ms |

Évolution de la charge : 10 utilisateurs → 9 req/s (P95 14 ms) ; 30 → 52 req/s (10 ms) ; 50 → 163 req/s en plateau (P95 11 ms). Le P95 reste stable pendant toute la montée en charge.

> Un premier passage avait signalé 3 échecs sur 4 450 requêtes. La cause était un **défaut du script de charge**, qui générait parfois une ancienneté supérieure à 60 ans. L'API avait correctement répondu 422. Après correction du générateur, aucun échec.

## 4. Conclusion

| Objectif | Mesure | Verdict |
|---|---|---|
| P95 `/predict` ≤ 100 ms jusqu'à 32 clients | 88,1 ms à 32 clients en boucle fermée (pire cas) ; 12 ms avec Locust à 50 utilisateurs | ✅ Respecté |
| Débit ≥ 20 req/s | ≈ 450 req/s (1 processus) | ✅ Respecté, avec une marge de 20 fois |
| 0 % d'erreur sous charge | 0 sur 25 724 requêtes de charge (paliers et Locust) | ✅ Respecté |
| P95 d'inférence ≤ 10 ms | 0,40 ms | ✅ Respecté |

**Limites** : mesures locales sur une machine virtuelle à 2 cœurs, client sur la même machine, sans réseau réel, sans TLS ni authentification, avec une seule demande répétée dans le benchmark (Locust varie les entrées). Un test sur l'infrastructure cible, avec la latence réseau des agences, reste nécessaire avant le pilote. Les objectifs sont respectés avec une marge suffisante pour que ces limites ne remettent pas le verdict en cause.
