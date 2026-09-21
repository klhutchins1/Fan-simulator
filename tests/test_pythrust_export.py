# tests/test_pythrust_export.py
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from fansim.prop_spec import get_prop_spec
from fansim.propeller.geometry import prop_blade_params


def test_default_export_grid_includes_static_j():
    from fansim.propeller.pythrust_export import default_export_grid

    rpms, js = default_export_grid(rpm_max=9000.0)
    assert rpms  # non-empty
    assert max(rpms) <= 9000.0 + 1e-9
    assert 0.0 in js
    assert max(js) == pytest.approx(0.60)


def test_prop_id_for_export_sanitizes():
    from fansim.propeller.pythrust_export import prop_id_for_export

    assert prop_id_for_export("cine_3inch") == "FANSIM_cine_3inch_BEMT"
    assert " " not in prop_id_for_export("weird name!")


def test_export_bemt_pythrust_catalog_tiny_grid(tmp_path: Path):
    from fansim.propeller.pythrust_export import (
        CSV_HEADER,
        export_bemt_pythrust_catalog,
    )

    spec = get_prop_spec("cine_3inch")
    params = prop_blade_params(spec)
    out = export_bemt_pythrust_catalog(
        params,
        prop_id="FANSIM_TEST_TINY",
        diameter_in=spec.diameter_in,
        pitch_in=spec.pitch_in,
        blade_count=spec.n_blades,
        out_dir=tmp_path,
        rpm_list=[3000.0],
        j_list=[0.0, 0.2],
        geometry_match="design_blade",
    )
    assert out["n_rows"] == 2
    csv_path = Path(out["csv"])
    json_path = Path(out["json"])
    meta_path = Path(out["export_meta"])
    assert csv_path.is_file() and json_path.is_file() and meta_path.is_file()

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert tuple(rows[0]) == CSV_HEADER
    assert len(rows) == 3  # header + 2
    for row in rows[1:]:
        ct = float(row[4])
        cp = float(row[5])
        assert ct == ct and cp == cp  # not NaN
        assert cp >= 0.0

    meta = json.loads(json_path.read_text(encoding="utf-8"))
    assert meta["id"] == "FANSIM_TEST_TINY"
    assert meta["manufacturer"] == "fansim"
    assert meta["data_csv"] == "FANSIM_TEST_TINY.csv"
    assert set(meta.keys()) == {
        "id",
        "manufacturer",
        "model",
        "diameter_in",
        "pitch_in",
        "blade_count",
        "data_csv",
    }

    exp = json.loads(meta_path.read_text(encoding="utf-8"))
    assert exp["source"] == "bemt"
    assert exp["geometry_match"] == "design_blade"
