"""Unit tests for fansim.validation.fan01: fan01_rig, fan01_direction, characteristic helpers.

No CFD/Docker -- geometry-only and pure-data checks (.superpowers/sdd/fan01-runner-brief.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import trimesh

from fansim.cfd.domain import MM_TO_M
from fansim.validation.fan01 import (
    DEFAULT_CHARACTERISTIC_CSV,
    CharacteristicPoint,
    fan01_direction,
    fan01_rig,
    interpolate_measured_q,
    load_characteristic,
    measured_q_all_crossings,
    measured_q_report,
)

_REAL_STL = (Path(__file__).resolve().parents[1]
            / "validation" / "reference" / "fan01" / "fan01_rotor.stl")


# --- fan01_rig -----------------------------------------------------------------

def _annulus_stl(tmp_path, r_hub=123.5, r_tip=247.9, half_span=57.8) -> Path:
    mesh = trimesh.creation.annulus(r_min=r_hub, r_max=r_tip, height=2.0 * half_span, sections=64)
    p = tmp_path / "rotor.stl"
    mesh.export(str(p))
    return p


@pytest.mark.skipif(not _REAL_STL.exists(), reason="reference STL not present")
def test_fan01_rig_radii_and_gap_on_real_stl():
    rig = fan01_rig(_REAL_STL)
    assert rig.duct_radius == pytest.approx(0.250)
    # tip radius ~247.9 mm -> tip_gap ~ 250 - 247.9 = ~2.1 mm
    assert rig.tip_gap == pytest.approx(0.250 - 247.890 * MM_TO_M, abs=1e-4)
    assert rig.tip_gap > 0.0
    assert rig.hub_radius == pytest.approx(123.17 * MM_TO_M, abs=2e-4)
    assert rig.rpm == pytest.approx(1486.0)


def test_fan01_rig_radii_and_gap_on_synthetic_annulus(tmp_path):
    stl = _annulus_stl(tmp_path, r_hub=120.0, r_tip=245.0, half_span=50.0)
    rig = fan01_rig(stl)
    assert rig.duct_radius == pytest.approx(0.250)
    assert rig.tip_gap == pytest.approx(0.250 - 0.245, abs=1e-3)
    assert rig.hub_radius == pytest.approx(0.120, abs=2e-3)
    assert rig.impeller_z_min == pytest.approx(-0.050, abs=1e-3)
    assert rig.impeller_z_max == pytest.approx(0.050, abs=1e-3)
    # MRF zone is +-5mm past the impeller bounds by default.
    assert rig.mrf_z_min == pytest.approx(rig.impeller_z_min - 0.005, abs=1e-6)
    assert rig.mrf_z_max == pytest.approx(rig.impeller_z_max + 0.005, abs=1e-6)


def test_fan01_rig_inlet_outlet_lengths_scale_with_duct_diameter(tmp_path):
    stl = _annulus_stl(tmp_path)
    rig = fan01_rig(stl, inlet_diameters=2.0, outlet_diameters=4.0)
    diameter = 2.0 * rig.duct_radius
    assert rig.inlet_length == pytest.approx(2.0 * diameter)
    assert rig.outlet_length == pytest.approx(4.0 * diameter)


# --- fan01_direction -------------------------------------------------------------

@pytest.mark.skipif(not _REAL_STL.exists(), reason="reference STL not present")
def test_fan01_direction_real_stl_is_as_built_plus_one():
    assert fan01_direction(_REAL_STL) == ("as_built", 1)


def test_fan01_direction_raises_on_inconclusive(tmp_path):
    # A plain cylinder has no blades at all -- prove_direction must be INCONCLUSIVE.
    mesh = trimesh.creation.cylinder(radius=50.0, height=20.0, sections=64)
    p = tmp_path / "cyl.stl"
    mesh.export(str(p))
    with pytest.raises(ValueError, match="CONCLUSIVE"):
        fan01_direction(p)


# --- measured characteristic -----------------------------------------------------

def test_load_characteristic_sorted_and_count():
    rows = load_characteristic()
    assert len(rows) == 20
    qs = [r.q_m3s for r in rows]
    assert qs == sorted(qs)
    assert rows[0].q_m3s == pytest.approx(0.19944)
    assert rows[-1].q_m3s == pytest.approx(2.07866)


def test_characteristic_csv_default_path_exists():
    assert DEFAULT_CHARACTERISTIC_CSV.exists()


@pytest.mark.parametrize("back_pa, expected_q", [
    (253.0, 0.1994),
    (205.0, 0.6061),
    (126.0, 1.4032),
    (64.0, 1.8039),
    (7.0, 2.0787),
])
def test_interpolate_measured_q_default_points(back_pa, expected_q):
    rows = load_characteristic()
    q = interpolate_measured_q(rows, back_pa)
    assert q == pytest.approx(expected_q, abs=0.03)


def test_interpolate_measured_q_outside_range_is_none():
    rows = load_characteristic()
    assert interpolate_measured_q(rows, 1000.0) is None
    assert interpolate_measured_q(rows, -50.0) is None


def test_interpolate_measured_q_exact_endpoint():
    rows = load_characteristic()
    assert interpolate_measured_q(rows, rows[0].p_chamber_pa) == pytest.approx(rows[0].q_m3s)
    assert interpolate_measured_q(rows, rows[-1].p_chamber_pa) == pytest.approx(rows[-1].q_m3s)


def test_stall_region_back_pressure_has_multiple_crossings():
    # 135 Pa sits in the stall-hump gap the monotone branch drops (brief's example point).
    rows = load_characteristic()
    crossings = measured_q_all_crossings(rows, 135.0)
    assert len(crossings) >= 2
    assert all(0.8 < q < 1.3 for q in crossings)


def test_measured_q_report_flags_stall_branches():
    rows = load_characteristic()
    report = measured_q_report(rows, 135.0)
    assert report["measured_q_m3s"] is not None
    assert "measured_q_m3s_branches" in report
    assert len(report["measured_q_m3s_branches"]) >= 2


def test_measured_q_report_single_branch_has_no_alternates():
    rows = load_characteristic()
    report = measured_q_report(rows, 126.0)
    assert report["measured_q_m3s"] == pytest.approx(1.4032, abs=0.01)
    assert "measured_q_m3s_branches" not in report


def test_characteristic_point_is_frozen_dataclass():
    p = CharacteristicPoint(q_m3s=1.0, p_chamber_pa=100.0, shaft_power_w=300.0)
    with pytest.raises(AttributeError):
        p.q_m3s = 2.0  # type: ignore[misc]
