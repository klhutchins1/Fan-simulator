"""Tests for mixed-flow impeller geometry + centrifugal archetype (no Docker)."""

from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq
import pytest

from fansim.centrifugal.geometry import (
    MixedFlowParams,
    build_mixed_flow,
    export_mixed_flow_stl,
)
from fansim.fan_spec import A12X25, mount_min_hub_radius


def _solid_contains_point(solid, x: float, y: float, z: float) -> bool:
    v = cq.Vector(x, y, z)
    if hasattr(solid, "isInside"):
        try:
            return bool(solid.isInside(v))
        except Exception:  # noqa: BLE001
            pass
    probe = cq.Solid.makeSphere(0.05, v)
    try:
        return solid.intersect(probe).Volume() > 1e-8
    except Exception:  # noqa: BLE001
        return False


def _solid(params: MixedFlowParams | None = None) -> cq.Solid:
    wp = build_mixed_flow(params or MixedFlowParams())
    solids = wp.val().Solids()
    assert len(solids) == 1
    return solids[0]


def test_r_back_below_mount_min_raises():
    need = mount_min_hub_radius(A12X25)
    assert need is not None
    with pytest.raises(ValueError, match="mount"):
        MixedFlowParams(r_back_mm=need - 0.5)


def test_r_eye_not_smaller_than_r_back_raises():
    with pytest.raises(ValueError, match="eye"):
        MixedFlowParams(r_eye_mm=28.0, r_back_mm=28.0)
    with pytest.raises(ValueError, match="eye"):
        MixedFlowParams(r_eye_mm=30.0, r_back_mm=28.0)


def test_mixed_flow_is_one_solid_in_a12_envelope():
    p = MixedFlowParams()
    solid = _solid(p)
    bb = solid.BoundingBox()
    assert 2.0 * max(abs(bb.xmax), abs(bb.xmin), abs(bb.ymax), abs(bb.ymin)) <= 110.0 + 0.2
    assert bb.zmax - bb.zmin <= 25.0 + 0.2

    zmin, zmax = bb.zmin, bb.zmax
    z_hub_min, z_hub_max = -0.5 * p.z_span_mm, 0.5 * p.z_span_mm
    assert _solid_contains_point(solid, p.r_back_mm - 1.0, 0.0, z_hub_min + 1.0) is True
    assert _solid_contains_point(solid, 0.5 * p.r_eye_mm, 0.0, z_hub_max - 1.0) is True
    z_mid = 0.5 * (zmin + zmax)
    assert _solid_contains_point(solid, 0.0, 0.0, z_mid) is True

    r_mid = 0.5 * (p.r_eye_mm + p.r_tip_mm)
    assert _solid_contains_point(solid, r_mid, 0.0, z_mid) is True
    half = math.radians(180.0 / p.n_blades)
    assert _solid_contains_point(
        solid, r_mid * math.cos(half), r_mid * math.sin(half), z_mid) is False


def test_export_mixed_flow_stl_writes_file(tmp_path):
    out = tmp_path / "mixed.stl"
    export_mixed_flow_stl(MixedFlowParams(), out)
    assert out.exists() and out.stat().st_size > 1000


def test_centrifugal_archetype_builds_and_evaluate_is_unimplemented(tmp_path):
    from fansim.centrifugal import MixedFlowArchetype
    from fansim.problem import get_archetype

    a = get_archetype("centrifugal")
    assert isinstance(a, MixedFlowArchetype)
    params = a.suggest_design(None)
    stl = a.build_geometry(params, tmp_path / "imp.stl")
    assert Path(stl).exists() and Path(stl).stat().st_size > 1000
    with pytest.raises(NotImplementedError, match="validate_stl"):
        a.evaluate(params, tmp_path / "eval")
    assert a.objective_names == ("cfm_free", "cfm_load", "efficiency")


def test_propeller_archetype_is_wired():
    from fansim.problem import get_archetype
    from fansim.propeller.archetype import PropellerArchetype

    a = get_archetype("propeller")
    assert isinstance(a, PropellerArchetype)
    assert a.suggest_design(None).tip_radius > 0


def test_load_mixed_flow_problem():
    from fansim.problem import load_problem

    problems = Path(__file__).resolve().parent.parent / "config" / "problems"
    p = load_problem(problems / "mixed_flow_a12x25.yaml")
    assert p.archetype == "centrifugal"


def test_export_mixed_flow_script_declares_parser():
    text = Path("scripts/export_mixed_flow.py").read_text(encoding="utf-8")
    assert "ArgumentParser" in text
    assert "--out" in text
    assert "★" not in text
