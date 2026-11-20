"""Test volontairement défaillant : prouve qu'un test en échec fait échouer le workflow.

Inactif par défaut. Activé par la variable ECHEC_VOLONTAIRE=1, positionnée par le
déclenchement manuel du workflow (Actions → tests → Run workflow → echec_volontaire).
"""

import os

import pytest


@pytest.mark.exigence("EX22")
@pytest.mark.skipif(os.environ.get("ECHEC_VOLONTAIRE") != "1", reason="démonstration inactive")
def test_echec_volontaire():
    """TCI01 Échec volontaire : ce test DOIT rendre le workflow rouge lorsqu'il est activé."""
    probabilite_simulee = float("1.5")
    assert 0.0 <= probabilite_simulee <= 1.0, "Échec volontaire : probabilité hors de [0, 1]"
