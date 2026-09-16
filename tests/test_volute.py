"""Tests for volute / 90° radial geometry + sealed-enclosure CFD (no Docker)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from fansim.volute.geometry import (
    VOLUTE_HONESTY,
    VoluteParams,
    build_radial_impeller,
    build_volute_casing,
    export_volute_stls,
    scroll_outer_radius_mm,
    volute_enclosure_extents_mm,
    volute_radii_mm,
)


def test_hub_not_smaller_than_tip_raises():
    with pytest.raises(ValueError, match="hub"):
        VoluteParams(r_hub_mm=50.0, r_tip_mm=40.0)


def test_n_blades_too_few_raises():
    with pytest.raises(ValueError, match="n_blades"):
        VoluteParams(n_blades=2)


def test_volute_clearance_floor():
    with pytest.raises(ValueError, match="clearance"):
        VoluteParams(volute_clearance_mm=0.1)


def test_tongue_angle_bounds():
    with pytest.raises(ValueError, match="tongue_angle"):
        VoluteParams(tongue_angle_deg=0.5)
    with pytest.raises(ValueError, match="tongue_tip"):
        VoluteParams(tongue_tip_clearance_mm=0.1)


def test_tongue_fillet_bounds():
    with pytest.raises(ValueError, match="tongue_fillet"):
        VoluteParams(tongue_fillet_mm=-0.1)
    with pytest.raises(ValueError, match="tongue_fillet"):
        VoluteParams(tongue_fillet_mm=9.0)


def test_default_scroll_sample_density():
    p = VoluteParams()
    assert p.n_volute_seg >= 64
    assert p.tongue_fillet_mm > 0.0
    assert VOLUTE_HONESTY == "stage3_smooth_scroll"


def test_volute_radii_clear_tip():
    p = VoluteParams()
    r = volute_radii_mm(p)
    assert r["r_in_mm"] > p.r_tip_mm
    assert r["r_out_exit_mm"] > r["r_out_tongue_mm"]


def test_scroll_outer_radius_archimedean():
    p = VoluteParams()
    rad = volute_radii_mm(p)
    assert scroll_outer_radius_mm(p, 0.0) == pytest.approx(rad["r_out_tongue_mm"])
    assert scroll_outer_radius_mm(p, 2.0 * math.pi) == pytest.approx(
        rad["r_out_tongue_mm"])  # wraps
    mid = scroll_outer_radius_mm(p, math.pi)
    assert rad["r_out_tongue_mm"] < mid < rad["r_out_exit_mm"]
    assert mid == pytest.approx(
        0.5 * (rad["r_out_tongue_mm"] + rad["r_out_exit_mm"]))
    # Monotonic over (0, 2π)
    samples = [scroll_outer_radius_mm(p, 2.0 * math.pi * i / 24) for i in range(25)]
    assert all(samples[i] <= samples[i + 1] + 1e-9 for i in range(23))


def test_enclosure_extents_seal_floor_and_stub():
    p = VoluteParams()
    r = volute_radii_mm(p)
    ext = volute_enclosure_extents_mm(p)
    assert ext["zmin"] < r["z0_mm"]  # floor fill below impeller
    assert ext["zmax_casing"] < ext["zmax_domain"]  # plenum above casing
    assert ext["xmax"] > r["r_out_tongue_mm"] + p.outlet_length_mm
    assert ext["xmin"] < 0 < ext["xmax"]
    # Geometry bounds: shell clears tip + spiral growth
    assert ext["r_shell_mm"] > p.r_tip_mm + p.volute_clearance_mm + p.spiral_growth_mm


@pytest.mark.slow
def test_radial_impeller_one_solid():
    wp = build_radial_impeller(VoluteParams())
    assert len(wp.val().Solids()) == 1
    bb = wp.val().BoundingBox()
    assert 2.0 * max(abs(bb.xmax), abs(bb.xmin), abs(bb.ymax), abs(bb.ymin)) <= 100.0 + 0.5
    assert bb.zmax - bb.zmin > 0


@pytest.mark.slow
def test_volute_casing_one_solid_clears_tip():
    p = VoluteParams()
    wp = build_volute_casing(p)
    assert len(wp.val().Solids()) == 1
    bb = wp.val().BoundingBox()
    # Sealed fill should reach past tip and cover under-floor margin.
    assert max(abs(bb.xmax), abs(bb.xmin), abs(bb.ymax), abs(bb.ymin)) > p.r_tip_mm + 2.0
    ext = volute_enclosure_extents_mm(p)
    assert bb.zmin <= ext["zmin"] + 0.5
    assert bb.zmax >= ext["zmax_casing"] - 0.5


@pytest.mark.slow
def test_export_volute_stls_watertight_ish(tmp_path):
    from fansim.geometry import watertight_report

    imp, cas = export_volute_stls(VoluteParams(), tmp_path / "out")
    assert imp.exists() and imp.stat().st_size > 1000
    assert cas.exists() and cas.stat().st_size > 1000
    for path in (imp, cas):
        rep = watertight_report(path)
        assert rep.ok, f"{path.name} not watertight: {rep}"


@pytest.mark.slow
def test_volute_archetype_builds_and_evaluates(tmp_path, monkeypatch):
    from fansim.optimize.objectives import ObjectiveResult
    from fansim.problem import get_archetype
    from fansim.volute.archetype import VoluteArchetype

    a = get_archetype("volute")
    assert isinstance(a, VoluteArchetype)
    params = a.suggest_design(None)
    stl = a.build_geometry(params, tmp_path / "imp.stl")
    assert Path(stl).exists() and Path(stl).stat().st_size > 1000

    called = {}

    def fake_eval(p, workdir, **kwargs):
        called["ok"] = True
        return ObjectiveResult(True, cfm_free=10.0, cfm_load=5.0, efficiency=20.0)

    monkeypatch.setattr("fansim.volute.evaluate.evaluate_volute", fake_eval)
    out = a.evaluate(params, tmp_path / "eval")
    assert called.get("ok")
    assert out.feasible is True


def test_domain_for_volute_extents():
    from fansim.cfd.domain import MM_TO_M
    from fansim.volute.domain import domain_for_volute

    p = VoluteParams()
    d = domain_for_volute(p)
    ext = volute_enclosure_extents_mm(p)
    assert abs(d.xmin - ext["xmin"] * MM_TO_M) < 1e-12
    assert abs(d.xmax - ext["xmax"] * MM_TO_M) < 1e-12
    assert abs(d.zmin - ext["zmin"] * MM_TO_M) < 1e-12
    assert abs(d.zmax - ext["zmax_domain"] * MM_TO_M) < 1e-12
    assert d.mrf_radius > 0
    assert d.location_in_mesh[0] < 0  # sample in scroll opposite tongue
    assert d.outlet_area_m2 > 0


def test_build_volute_case_writes_dicts(tmp_path, monkeypatch):
    from fansim.volute.case import build_volute_case
    from fansim.volute.domain import domain_for_volute

    # Skip CadQuery: write tiny placeholder STLs.
    imp = tmp_path / "impeller.stl"
    cas = tmp_path / "casing.stl"
    # Minimal ASCII STL with one triangle (trimesh can load).
    stl_body = (
        "solid t\n"
        " facet normal 0 0 1\n"
        "  outer loop\n"
        "   vertex 0 0 0\n"
        "   vertex 1 0 0\n"
        "   vertex 0 1 0\n"
        "  endloop\n"
        " endfacet\n"
        "endsolid t\n"
    )
    imp.write_text(stl_body, encoding="utf-8")
    cas.write_text(stl_body, encoding="utf-8")

    case_dir = tmp_path / "case"
    domain = domain_for_volute(VoluteParams())
    build_volute_case(case_dir, imp, cas, domain, back_pressure_pa=0.0, n_iters=100)
    assert (case_dir / "system/blockMeshDict").exists()
    bm = (case_dir / "system/blockMeshDict").read_text(encoding="utf-8")
    assert "inlet" in bm and "outlet" in bm
    assert (case_dir / "constant/MRFProperties").exists()
    assert (case_dir / "0/U").exists()
    assert (case_dir / "constant/triSurface/impeller.stl").exists()
    assert (case_dir / "constant/triSurface/casing.stl").exists()
    meta = (case_dir / "constant/volute_domain.json").read_text(encoding="utf-8")
    assert "volute_radial" in meta
    assert VOLUTE_HONESTY in meta
    assert "stage3_smooth_scroll" in meta
    assert "stage1_tight_box_bypass_risk" not in meta
    assert "stage2_sealed_enclosure_segmented_tongue" not in meta


def test_evaluate_volute_mocked_cfd(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from fansim.volute import evaluate as ev
    from fansim.volute.evaluate import evaluate_volute

    free_m = SimpleNamespace(
        cfm=40.0, efficiency=0.35, thrust_n=0.2, torque_nm=0.0005,
        static_pressure_rise_pa=2.0,
        converged=True, flow_drift_pct=0.2,
        to_dict=lambda: {"cfm": 40.0},
    )
    load_m = SimpleNamespace(
        cfm=25.0, efficiency=0.28, thrust_n=0.15, torque_nm=0.0006,
        static_pressure_rise_pa=50.0,
        converged=True, flow_drift_pct=0.3,
        to_dict=lambda: {"cfm": 25.0},
    )
    seq = iter([free_m, load_m])

    def fake_export(params, out_dir):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        imp = out_dir / "impeller.stl"
        cas = out_dir / "casing.stl"
        imp.write_text("solid", encoding="utf-8")
        cas.write_text("solid", encoding="utf-8")
        return imp, cas

    monkeypatch.setattr(ev, "export_volute_stls", fake_export)
    monkeypatch.setattr(ev, "watertight_report",
                        lambda stl: SimpleNamespace(ok=True, n_bodies=1))
    monkeypatch.setattr(ev, "build_volute_case", lambda *a, **k: Path(tmp_path))
    monkeypatch.setattr(ev, "run_mesh", lambda *a, **k: None)
    monkeypatch.setattr(ev, "run_solve", lambda *a, **k: None)
    monkeypatch.setattr(ev, "parse_fan_metrics", lambda *a, **k: next(seq))
    monkeypatch.setattr(ev, "OpenFOAMRunner", lambda workdir: SimpleNamespace())

    res = evaluate_volute(VoluteParams(), tmp_path / "run")
    assert res.feasible is True
    assert res.raw.get("topology") == "volute_radial"
    assert res.raw.get("archetype") == "volute"
    assert res.raw.get("honesty") == VOLUTE_HONESTY
    assert res.raw.get("honesty") == "stage3_smooth_scroll"
    assert res.cfm_free > 0
    assert res.raw.get("cfm_free_cfd") == pytest.approx(40.0)
    assert "print_k_cfm" in res.raw
    assert res.cfm_free == pytest.approx(40.0 * float(res.raw["print_k_cfm"]))
    assert res.raw.get("derate") == pytest.approx(1.0)
    assert res.actual_rpm == pytest.approx(float(res.raw["cfd_rpm"]))
    assert "motor_kv_rpm_per_v" in res.raw


def test_evaluate_volute_motor_derates_when_torque_exceeds_budget(tmp_path, monkeypatch):
    """§9.8 — heavy CFD torque must affinity-scale CFM below the raw solve."""
    from types import SimpleNamespace

    from fansim.volute import evaluate as ev
    from fansim.volute.domain import DEFAULT_VOLUTE_RPM
    from fansim.volute.evaluate import evaluate_volute

    free_m = SimpleNamespace(
        cfm=40.0, efficiency=0.35, thrust_n=0.2, torque_nm=5.0,
        static_pressure_rise_pa=2.0,
        converged=True, flow_drift_pct=0.2,
        to_dict=lambda: {"cfm": 40.0, "torque_nm": 5.0},
    )
    load_m = SimpleNamespace(
        cfm=25.0, efficiency=0.28, thrust_n=0.15, torque_nm=5.0,
        static_pressure_rise_pa=50.0,
        converged=True, flow_drift_pct=0.3,
        to_dict=lambda: {"cfm": 25.0, "torque_nm": 5.0},
    )
    seq = iter([free_m, load_m])

    def fake_export(params, out_dir):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        imp = out_dir / "impeller.stl"
        cas = out_dir / "casing.stl"
        imp.write_text("solid", encoding="utf-8")
        cas.write_text("solid", encoding="utf-8")
        return imp, cas

    monkeypatch.setattr(ev, "export_volute_stls", fake_export)
    monkeypatch.setattr(ev, "watertight_report",
                        lambda stl: SimpleNamespace(ok=True, n_bodies=1))
    monkeypatch.setattr(ev, "build_volute_case", lambda *a, **k: Path(tmp_path))
    monkeypatch.setattr(ev, "run_mesh", lambda *a, **k: None)
    monkeypatch.setattr(ev, "run_solve", lambda *a, **k: None)
    monkeypatch.setattr(ev, "parse_fan_metrics", lambda *a, **k: next(seq))
    monkeypatch.setattr(ev, "OpenFOAMRunner", lambda workdir: SimpleNamespace())

    res = evaluate_volute(VoluteParams(), tmp_path / "heavy")
    assert res.feasible is True
    assert res.raw["derate"] < 0.995
    assert res.actual_rpm < DEFAULT_VOLUTE_RPM
    # Derated CFD free CFM is stamped; reported CFM also carries the print knockdown.
    assert res.raw.get("cfm_free_cfd") == pytest.approx(40.0 * res.raw["derate"])
    assert res.cfm_free == pytest.approx(
        float(res.raw["cfm_free_cfd"]) * float(res.raw["print_k_cfm"]))
    assert "motor-limited" in res.reason


def test_evaluate_volute_mesh_only(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from fansim.volute import evaluate as ev
    from fansim.volute.evaluate import evaluate_volute

    def fake_export(params, out_dir):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        imp = out_dir / "impeller.stl"
        cas = out_dir / "casing.stl"
        imp.write_bytes(b"x")
        cas.write_bytes(b"x")
        return imp, cas

    monkeypatch.setattr(ev, "export_volute_stls", fake_export)
    monkeypatch.setattr(ev, "watertight_report",
                        lambda stl: SimpleNamespace(ok=True, n_bodies=1))
    monkeypatch.setattr(ev, "build_volute_case", lambda *a, **k: Path(tmp_path))
    monkeypatch.setattr(ev, "run_mesh", lambda *a, **k: None)
    monkeypatch.setattr(ev, "OpenFOAMRunner", lambda workdir: SimpleNamespace())

    res = evaluate_volute(VoluteParams(), tmp_path / "mesh", mesh_only=True)
    assert res.feasible is False
    assert "mesh_only" in res.reason
    assert res.raw.get("meshed") is True
    assert res.raw.get("grid_converged") is False  # §11.1 GCI honesty stamp


def test_evaluate_volute_script_declares_parser():
    text = Path("scripts/evaluate_volute.py").read_text(encoding="utf-8")
    assert "ArgumentParser" in text
    assert "volute" in text.lower()
    assert "--mesh-only" in text
    assert "★" not in text


def test_load_volute_problem():
    from fansim.problem import load_problem

    problems = Path(__file__).resolve().parent.parent / "config" / "problems"
    p = load_problem(problems / "volute_radial.yaml")
    assert p.archetype == "volute"


def test_export_volute_script_declares_parser():
    text = Path("scripts/export_volute.py").read_text(encoding="utf-8")
    assert "ArgumentParser" in text
    assert "--out-dir" in text
    assert "★" not in text


def test_volute_params_from_flat_roundtrip():
    from fansim.volute.params_io import volute_params_from_flat, volute_params_to_flat

    p = VoluteParams(
        n_blades=9, r_tip_mm=48.0, tongue_angle_deg=6.0, tongue_fillet_mm=2.0)
    flat = volute_params_to_flat(p)
    q = volute_params_from_flat(flat)
    assert q.n_blades == 9 and q.r_tip_mm == 48.0
    assert q.tongue_angle_deg == 6.0
    assert q.tongue_fillet_mm == 2.0


def test_volute_cockpit_declares_dormant_design_knobs():
    text = Path("fansim/cockpit/volute_tab.py").read_text(encoding="utf-8")
    assert "volute_blade_thick" in text
    assert "volute_tongue_angle" in text
    assert "volute_out_w" in text
    assert "Scroll & tongue" in text
