"""Short sealed frame ring (25 mm) becomes the CFD default (CFD_VERSION 5).

See ``.superpowers/sdd/ring-duct-brief.md``. The v4 full-length noSlip round duct meshed
pipe friction over the whole ~0.7 m domain; the real NF-A12x25 sits in a ~25 mm deep frame
ring with open air on both sides. ``duct="ring"`` is now the default; ``duct="round"`` (v4)
and ``duct="square"`` (legacy) remain for comparison.
"""

from __future__ import annotations

import json
import math

import pytest
import trimesh

from fansim.cfd.domain import MM_TO_M, TestRig as _Rig
from fansim.cfd.metrics import CFD_VERSION
from fansim.cfd.openfoam_case import (
    BOX_SCALE,
    RING_LENGTH_MM,
    build_case,
    check_ring_covers_impeller,
)
from fansim.cfd.sanity import PASS, WARN, run_sanity


def _rig(*, impeller_z_min=-0.0085, impeller_z_max=0.0085) -> _Rig:
    return _Rig(duct_radius=0.056, tip_gap=0.0005, inlet_length=0.224, outlet_length=0.448,
                impeller_z_min=impeller_z_min, impeller_z_max=impeller_z_max,
                mrf_z_min=impeller_z_min - 0.002, mrf_z_max=impeller_z_max + 0.002,
                rpm=2000.0, inlet_velocity=2.0)


def _impeller_stl(tmp_path, span_mm=10.0):
    stl = tmp_path / "r.stl"
    trimesh.creation.box(extents=(20.0, 20.0, span_mm)).export(str(stl))
    return stl


def _load_meta(case_dir):
    return json.loads((case_dir / "constant/case_meta.json").read_text(encoding="utf-8"))


def test_cfd_version_bumped_to_5():
    assert CFD_VERSION == 6


def test_default_duct_is_ring(tmp_path):
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0)
    meta = _load_meta(case)
    assert meta["duct_shape"] == "ring"
    assert meta["duct_source"] == "generated"
    assert meta["ring_length_mm"] == pytest.approx(RING_LENGTH_MM)


def test_ring_z_span_covers_impeller_and_is_25mm_for_small_impeller(tmp_path):
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0)
    m = trimesh.load(str(case / "constant/triSurface/casing.stl"), force="mesh")
    z0, z1 = float(m.bounds[0, 2]), float(m.bounds[1, 2])
    assert (z1 - z0) * 1e3 == pytest.approx(RING_LENGTH_MM, abs=1e-3)
    assert z0 <= rig.impeller_z_min + 1e-9
    assert z1 >= rig.impeller_z_max - 1e-9


def test_ring_outer_radius_seals_corners_and_blockmesh_half_width(tmp_path):
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0)
    m = trimesh.load(str(case / "constant/triSurface/casing.stl"), force="mesh")
    r = [math.hypot(v[0], v[1]) for v in m.vertices]
    inner_r, outer_r = min(r), max(r)
    assert inner_r == pytest.approx(rig.duct_radius, rel=0.05)
    H = BOX_SCALE * rig.duct_radius
    assert outer_r >= H * math.sqrt(2)

    bm = (case / "system/blockMeshDict").read_text(encoding="utf-8")
    xs = [float(v) for v in __import__("re").findall(
        r"\(\s*([-\d.eE+]+)\s+[-\d.eE+]+\s+[-\d.eE+]+\s*\)", bm.split("blocks")[0])[:8]]
    assert max(xs) == pytest.approx(H, rel=1e-6)


def test_long_impeller_lengthens_the_ring(tmp_path):
    # 30 mm impeller span > 25 mm nominal ring -> ring grows to span + 2 mm.
    rig = _rig(impeller_z_min=-0.015, impeller_z_max=0.015)
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path, span_mm=30.0), rig,
                      back_pressure_pa=0.0)
    meta = _load_meta(case)
    assert meta["ring_length_mm"] == pytest.approx(32.0)  # 30mm span + 2*1mm margin

    m = trimesh.load(str(case / "constant/triSurface/casing.stl"), force="mesh")
    z0, z1 = float(m.bounds[0, 2]), float(m.bounds[1, 2])
    assert (z1 - z0) * 1e3 == pytest.approx(32.0, abs=1e-3)
    assert z0 <= rig.impeller_z_min + 1e-9
    assert z1 >= rig.impeller_z_max - 1e-9


def test_check_ring_covers_impeller_raises_for_short_ring():
    rig = _rig()
    # 10 mm ring centred at 0 -- too short to cover the +-8.5mm impeller span.
    short_ring = trimesh.creation.annulus(r_min=rig.duct_radius / MM_TO_M,
                                          r_max=rig.duct_radius / MM_TO_M + 50.0,
                                          height=10.0, sections=32)
    with pytest.raises(ValueError, match="ring"):
        check_ring_covers_impeller(short_ring, rig)


def test_check_ring_covers_impeller_passes_for_full_ring():
    rig = _rig()
    ring = trimesh.creation.annulus(r_min=rig.duct_radius / MM_TO_M,
                                    r_max=rig.duct_radius / MM_TO_M + 50.0,
                                    height=RING_LENGTH_MM, sections=32)
    check_ring_covers_impeller(ring, rig)  # must not raise


def test_location_in_mesh_is_outside_ring_z_range(tmp_path):
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0)
    snappy = (case / "system/snappyHexMeshDict").read_text(encoding="utf-8")
    m = trimesh.load(str(case / "constant/triSurface/casing.stl"), force="mesh")
    ring_z0_m = float(m.bounds[0, 2]) * MM_TO_M
    ring_z1_m = float(m.bounds[1, 2]) * MM_TO_M

    import re
    match = re.search(r"locationInMesh\s*\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)",
                      snappy)
    assert match, "locationInMesh not found in snappyHexMeshDict"
    locz = float(match.group(3))
    assert not (ring_z0_m <= locz <= ring_z1_m), (
        f"location-in-mesh z={locz} falls inside ring z-range [{ring_z0_m}, {ring_z1_m}]")
    assert locz < ring_z0_m  # upstream of the ring, in the inlet duct


def test_ring_length_and_center_override(tmp_path):
    # FAN-01: 201 mm sleeve, centred +4mm downstream of the rotor mid-plane.
    rig = _rig()
    mid_z_mm = 0.5 * (rig.impeller_z_min + rig.impeller_z_max) / MM_TO_M
    center_mm = mid_z_mm + 4.0
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0,
                      ring_length_mm=201.0, ring_z_center_mm=center_mm)
    meta = _load_meta(case)
    assert meta["ring_length_mm"] == pytest.approx(201.0)

    m = trimesh.load(str(case / "constant/triSurface/casing.stl"), force="mesh")
    z0, z1 = float(m.bounds[0, 2]), float(m.bounds[1, 2])
    assert (z1 - z0) * 1e3 == pytest.approx(201.0, abs=1e-3)
    assert 0.5 * (z0 + z1) * 1e3 == pytest.approx(center_mm, abs=1e-3)
    # still covers the impeller (z0/z1 are meters, same as rig.impeller_z_*)
    assert z0 <= rig.impeller_z_min + 1e-9
    assert z1 >= rig.impeller_z_max - 1e-9


def test_ring_override_defaults_keep_old_behaviour(tmp_path):
    # No override args -> identical to test_default_duct_is_ring.
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0,
                      ring_length_mm=None, ring_z_center_mm=None)
    meta = _load_meta(case)
    assert meta["ring_length_mm"] == pytest.approx(RING_LENGTH_MM)


def test_duct_round_still_produces_v4_full_length_duct(tmp_path):
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0,
                      duct="round")
    meta = _load_meta(case)
    assert meta["duct_shape"] == "round"
    m = trimesh.load(str(case / "constant/triSurface/casing.stl"), force="mesh")
    z0, z1 = float(m.bounds[0, 2]), float(m.bounds[1, 2])
    # Full-length duct spans (approximately) the whole domain, not just 25mm.
    assert (z1 - z0) * 1e3 > RING_LENGTH_MM * 2


def test_duct_square_still_legacy(tmp_path):
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0,
                      duct="square")
    meta = _load_meta(case)
    assert meta["duct_shape"] == "square"
    assert not (case / "constant/triSurface/casing.stl").exists()


def test_invalid_duct_still_raises(tmp_path):
    rig = _rig()
    with pytest.raises(ValueError, match="duct"):
        build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0,
                  duct="hexagon")


# --- sanity: ring PASS, round PASS + friction note, square WARN ---

def _write_pp(case, fo, filename, rows):
    d = case / "postProcessing" / fo / "0"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text("# header\n" + rows, encoding="utf-8")


def _minimal_case_for_sanity(tmp_path, duct_shape):
    case = tmp_path / "case"
    case.mkdir()
    meta = {
        "duct_shape": duct_shape,
        "box_half_width_m": 0.1,
        "inlet_area_m2": 0.01,
        "outlet_area_m2": 0.01,
        "casing": duct_shape != "square",
        "plenum": False,
        "duct_radius_m": 0.06,
        "tip_radius_m": 0.05,
        "hub_radius_m": 0.02,
        "rpm": 2000.0,
        "spin": -1,
        "cfd_version": CFD_VERSION,
    }
    (case / "constant").mkdir(parents=True, exist_ok=True)
    (case / "constant/case_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return case


def test_sanity_duct_shape_ring_is_pass(tmp_path):
    case = _minimal_case_for_sanity(tmp_path, "ring")
    checks = run_sanity(case, omega_signed=-200.0)
    c = next(c for c in checks if c.name == "duct_shape")
    assert c.status == PASS


def test_sanity_duct_shape_round_is_pass_with_friction_note(tmp_path):
    case = _minimal_case_for_sanity(tmp_path, "round")
    checks = run_sanity(case, omega_signed=-200.0)
    c = next(c for c in checks if c.name == "duct_shape")
    assert c.status == PASS
    assert "pipe friction" in c.note
    assert "not free-air" in c.note


def test_sanity_duct_shape_square_is_warn(tmp_path):
    case = _minimal_case_for_sanity(tmp_path, "square")
    checks = run_sanity(case, omega_signed=-200.0)
    c = next(c for c in checks if c.name == "duct_shape")
    assert c.status == WARN


def test_ring_case_meta_inlet_is_full_box_face_and_not_plenum(tmp_path):
    """A short ring doesn't reach the inlet face: inlet area is (2H)^2 and it isn't a plenum."""
    import json

    import trimesh as _tm

    from fansim.cfd.domain import TestRig as _R
    from fansim.cfd.openfoam_case import BOX_SCALE, build_case

    rig = _R(duct_radius=0.055, tip_gap=0.0005, inlet_length=0.22, outlet_length=0.44,
             impeller_z_min=-0.008, impeller_z_max=0.008, mrf_z_min=-0.01, mrf_z_max=0.01,
             rpm=2000.0, inlet_velocity=2.0)
    stl = tmp_path / "r.stl"
    _tm.creation.box(extents=(20.0, 20.0, 10.0)).export(str(stl))
    case = build_case(tmp_path / "case", stl, rig, back_pressure_pa=0.0)
    meta = json.loads((case / "constant/case_meta.json").read_text(encoding="utf-8"))
    h = BOX_SCALE * rig.duct_radius
    assert meta["duct_shape"] == "ring"
    assert meta["plenum"] is False
    assert abs(meta["inlet_area_m2"] - (2 * h) ** 2) < 1e-9
