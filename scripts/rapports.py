"""Génère reports/02_resultats_tests.md à partir de l'export pytest par exigence.

pytest --rapport-exigences=reports/resultats/resultats_tests.json
python -m scripts.rapports
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict, defaultdict

from app import config

RESULTATS = config.RACINE / "reports" / "resultats" / "resultats_tests.json"
SORTIE = config.RACINE / "reports" / "02_resultats_tests.md"

SUITES = OrderedDict(
    [
        ("test_validation.py", "Validation (unitaires)"),
        ("test_preprocessing.py", "Prétraitement (unitaires)"),
        ("test_api.py", "API (fonctionnels)"),
        ("test_integration.py", "Intégration"),
        ("test_robustness.py", "Robustesse"),
        ("test_regression.py", "Non-régression"),
        ("test_performance.py", "Performance (CI)"),
        ("test_echec_volontaire.py", "Démonstration CI"),
    ]
)
LIBELLES = {
    "reussi": "✅ Réussi",
    "echoue": "❌ Échoué",
    "ignore": "⏸ Ignoré",
    "echec_attendu": "⚠️ Anomalie connue",
}


def main() -> None:
    donnees = json.loads(RESULTATS.read_text(encoding="utf-8"))
    tests = donnees["tests"]

    # Regroupe les cas paramétrés sous leur fonction de test.
    groupes: dict[tuple[str, str], dict] = OrderedDict()
    for t in tests:
        fichier = t["test"].split("::")[0].split("/")[-1]
        fonction = re.sub(r"\[.*\]$", "", t["test"].split("::")[-1])
        g = groupes.setdefault(
            (fichier, fonction),
            {
                "description": t["description"],
                "exigences": set(),
                "cas": 0,
                "resultats": defaultdict(int),
            },
        )
        g["exigences"].update(t["exigences"])
        g["cas"] += 1
        g["resultats"][t["resultat"]] += 1

    total = defaultdict(int)
    for t in tests:
        total[t["resultat"]] += 1

    L = [
        "# Résultats d'exécution des tests",
        "",
        "*Généré par `python -m scripts.rapports` à partir de "
        "`reports/resultats/resultats_tests.json`. Ne pas modifier à la main.*",
        "",
        f"**{len(tests)} cas exécutés** : {total['reussi']} réussis, {total['echoue']} échoués, "
        f"{total['echec_attendu']} anomalie connue (xfail strict), {total['ignore']} ignoré "
        "(test d'échec volontaire, inactif hors démonstration).",
        "",
        "## 1. Synthèse par suite",
        "",
        "| Suite | Fichier | Fonctions | Cas | Réussis | Échoués | Autres |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for fichier, nom in SUITES.items():
        gs = [g for (f, _), g in groupes.items() if f == fichier]
        if not gs:
            continue
        cas = sum(g["cas"] for g in gs)
        ok = sum(g["resultats"]["reussi"] for g in gs)
        ko = sum(g["resultats"]["echoue"] for g in gs)
        L.append(
            f"| {nom} | `tests/{fichier}` | {len(gs)} | {cas} | {ok} | {ko} | {cas - ok - ko} |"
        )

    L += [
        "",
        "## 2. Synthèse par exigence",
        "",
        "| Exigence | Cas de test | Réussis | Échoués | Anomalie connue | Ignorés |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for ex, v in donnees["par_exigence"].items():
        L.append(
            f"| {ex} | {v['tests']} | {v['reussi']} | {v['echoue']} | "
            f"{v['echec_attendu']} | {v['ignore']} |"
        )

    L += ["", "## 3. Détail par fonction de test", ""]
    for fichier, nom in SUITES.items():
        gs = [(fn, g) for (f, fn), g in groupes.items() if f == fichier]
        if not gs:
            continue
        L += [
            f"### {nom} (`tests/{fichier}`)",
            "",
            "| Test | Description | Exigences | Cas | Résultat |",
            "|---|---|---|---:|---|",
        ]
        for fn, g in gs:
            res = ", ".join(
                f"{LIBELLES[k]} ×{n}" if g["cas"] > 1 else LIBELLES[k]
                for k, n in g["resultats"].items()
            )
            desc = g["description"].replace("|", "\\|")
            L.append(
                f"| `{fn}` | {desc} | {', '.join(sorted(g['exigences']))} | {g['cas']} | {res} |"
            )
        L.append("")
    SORTIE.write_text("\n".join(L), encoding="utf-8")
    print(f"{SORTIE.relative_to(config.RACINE)} : {len(groupes)} fonctions, {len(tests)} cas")


if __name__ == "__main__":
    main()
