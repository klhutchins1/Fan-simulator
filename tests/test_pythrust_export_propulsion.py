# tests/test_pythrust_export_propulsion.py
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pythrust")
pytestmark = pytest.mark.propulsion


def test_pythrust_database_loads_exported_catalog(tmp_path: Path):
    from pythrust.propellers.database import PropellerDatabase

    from fansim.prop_spec import get_prop_spec
    from fansim.propeller.geometry import prop_blade_params
    from fansim.propeller.pythrust_export import export_bemt_pythrust_catalog

    spec = get_prop_spec("cine_3inch")
    prop_id = "FANSIM_LOAD_SMOKE"
    export_bemt_pythrust_catalog(
        prop_blade_params(spec),
        prop_id=prop_id,
        diameter_in=spec.diameter_in,
        pitch_in=spec.pitch_in,
        blade_count=spec.n_blades,
        out_dir=tmp_path,
        rpm_list=[5000.0],
        j_list=[0.0, 0.1],
    )
    db = PropellerDatabase()
    assert db.load(tmp_path) is True
    entry = db.get(prop_id)
    assert entry is not None
    assert float(entry.metadata.diameter_in) == pytest.approx(spec.diameter_in)
