"""R1.1a: reference_build skips only the print-hang check (lt120 prereg)."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from fansim.geometry.blade import (
    BladeParams,
    _hub_axial_range,
    build_impeller_parts,
    validate_blade_params,
)
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat

_HANG = json.loads((Path(__file__).parent / "data" / "hub_hang_designs.json").read_text())


def _hanging(**over) -> BladeParams:
    d = _HANG["S2_0176"]
    return dataclasses.replace(blade_from_flat(d["flat"], Features(**d["features"])), **over)


def test_reference_build_skips_only_the_hang_check():
    hanging = _hanging()
    with pytest.raises(ValueError, match="printed blade would hang"):
        validate_blade_params(hanging)
    validate_blade_params(dataclasses.replace(hanging, reference_build=True))


def test_reference_build_still_refuses_impossible_geometry():
    p = dataclasses.replace(_hanging(), reference_build=True, n_blades=1)
    with pytest.raises(ValueError, match="n_blades"):
        validate_blade_params(p)
    p2 = dataclasses.replace(_hanging(), reference_build=True, hub_radius=80.0, tip_radius=40.0)
    with pytest.raises(ValueError, match="must be < tip_radius"):
        validate_blade_params(p2)


def test_reference_build_still_clips_at_the_hub_face():
    p = dataclasses.replace(_hanging(), reference_build=True, n_blades=2)
    _hub, blades, _ring = build_impeller_parts(p)
    z_face = _hub_axial_range(p)[0]
    assert blades[0].BoundingBox().zmin >= z_face - 0.05


def test_lt120_params_are_wrapped_and_skip_hang_only():
    from fansim.validation.lt120 import lt120_params

    p = lt120_params()
    assert p.section_wrap == "cylinder"
    assert p.reference_build is True
    assert p.clip_below_hub is True
    assert p.n_blades == 7
    assert p.hub_radius == pytest.approx(25.0)
    assert p.tip_radius == pytest.approx(60.0)
    validate_blade_params(p)


def test_lt120_campaign_matches_prereg():
    from fansim.validation.lt120 import MESHES_MM, POINTS, table_stations, lt120_params

    p = lt120_params()
    dps = [pt["dp_pa"] for pt in POINTS]
    assert dps == [6.85, 13.71, 14.69, 17.14]
    assert MESHES_MM == (5.8, 6.2)
    assert POINTS[0]["role"] == "high-flow"
    assert POINTS[1]["role"] == "high-flow"
    assert POINTS[2]["role"] == "report-only"
    assert POINTS[3]["role"] == "report-only"
    assert 34.01 not in dps
    assert table_stations()[0]["r_mm"] == pytest.approx(23.0)
    assert table_stations()[0]["r_mm"] < p.hub_radius


def test_lt120_convergence_gate_and_cutoff():
    from datetime import datetime
    from fansim.validation.lt120 import past_cutoff, point_converged

    assert point_converged(2.0, 1.0) is True
    assert point_converged(2.01, 1.0) is False
    assert point_converged(1.0, 1.01) is False
    assert point_converged(1.0, None) is False
    assert past_cutoff(datetime(2026, 10, 27, 15, 29)) is False
    assert past_cutoff(datetime(2026, 10, 27, 15, 30)) is True


def test_validate_lt120_script_wires_freeze_resume_and_cutoff():
    text = Path("scripts/validate_lt120.py").read_text(encoding="utf-8")
    assert "--freeze" in text
    assert "summary.json" in text
    assert "progress.json" in text
    assert "past_cutoff" in text
    assert "point_converged" in text
    assert "6.85" in text or "POINTS" in text


def test_frozen_cut_check_marks_embedded_root_nm():
    path = Path("validation/reference/lt120/geometry_freeze.json")
    if not path.is_file():
        pytest.skip("geometry freeze not written yet")
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["section_wrap"] == "cylinder"
    assert doc["reference_build"] is True
    assert doc["clip_below_hub"] is True
    r23 = next(r for r in doc["cut_check"] if r["r_mm"] == 23.0)
    assert r23["verdict"] == "N/M"
    measurable = [r for r in doc["cut_check"] if r["verdict"] != "N/M"]
    assert len(measurable) == 9
    assert all(r["verdict"] == "PASS" for r in measurable)
    assert doc["direction"] == "CONCLUSIVE"


def test_night_queue_has_lt120_job():
    queue = json.loads(Path("night/queue.json").read_text(encoding="utf-8"))
    job = next(j for j in queue["jobs"] if j["id"] == "lt120-r11a")
    assert job["status"] == "queued"
    assert any("validate_lt120.py" in str(part) for part in job["cmd"])
    assert float(job["max_hours"]) >= 6
