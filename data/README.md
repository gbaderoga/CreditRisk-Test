# Données synthétiques

> **Avertissement** : ces données sont **synthétiques**. Elles servent à **tester le système logiciel** (contrat d'entrée, pipeline, non-régression, performance). Elles **ne permettent pas** de démontrer la performance réelle d'un modèle de crédit, ni son équité, ni sa conformité.

| Fichier | Contenu |
|---|---|
| `credit_synthetique.csv` | 20 000 demandes générées par `scripts/entrainement.py` (graine 42) |
| `test.csv` | Partition de test (20 %, 4 000 demandes, 554 défauts), stratifiée. **Versionnée** : c'est la référence de la non-régression. |

## Processus de génération

| Variable | Loi |
|---|---|
| `age` | Entier uniforme sur [18, 70] |
| `anciennete_activite` | min(âge − 12, Gamma(2, 3)), arrondie à 0,1 an |
| `revenu_mensuel` | Log-normale de médiane 180 000 FCFA (σ = 0,6), bornée à [20 000 ; 5 000 000], arrondie au millier |
| `montant_credit` | revenu × Log-normale de médiane 4 (σ = 0,7), borné à [50 000 ; 100 000 000], arrondi à la dizaine de milliers |
| `duree_mois` | {3, 6, 9, 12, 18, 24, 36, 48} avec les probabilités {5, 15, 10, 30, 15, 15, 7, 3} % |
| `defaut` | Bernoulli(σ(z)), avec τ = (montant / durée) / revenu et z = −1,9 + 2,8·[ln(1+τ) − ln(1,35)] − 0,03·(âge − 38) − 0,12·(ancienneté − 4) + 0,015·(durée − 12) − 0,30·ln(revenu / 180 000) |

Taux de défaut obtenu : **13,9 %**. Le processus étant connu, on peut calculer la ROC-AUC du « modèle parfait », qui utilise la vraie probabilité : **0,753** sur `test.csv`. Le modèle v1 atteint 0,752. Ses limites prédictives viennent donc du **bruit intrinsèque** des données (le défaut est tiré au hasard), pas d'un défaut d'apprentissage.

Partition : 60 % entraînement, 20 % validation (choix de C), 20 % test, stratifiée sur `defaut`, graine 42.
