"""Sealed round duct by default (CFD_VERSION 4): see .superpowers/sdd/round-duct-brief.md.

Without a casing the legacy square hex tunnel (half-width = duct_radius) leaves its corners
(~21% of the cross-section) open around the blade tips -- the nominal tip gap exists at only
4 points, and the existing thin casing left the same box corners open. ``build_case`` now
generates a sealed round duct by default; ``duct="square"`` keeps the old tunnel for
comparison.
"""

from __future__ import annotations

import math

import pytest
import trimesh

from fansim.cfd.casing import export_casing_stl
from fansim.cfd.domain import MM_TO_M, TestRig as _Rig
from fansim.cfd.openfoam_case import (
    BOX_SCALE,
    build_case,
    check_casing_seals,
)


def _rig() -> _Rig:
    return _Rig(duct_radius=0.056, tip_gap=0.0005, inlet_length=0.224, outlet_length=0.448,
                impeller_z_min=-0.0085, impeller_z_max=0.0085, mrf_z_min=-0.0105, mrf_z_max=0.0105,
                rpm=2000.0, inlet_velocity=2.0)


def _impeller_stl(tmp_path):
    stl = tmp_path / "r.stl"
    trimesh.creation.box(extents=(20.0, 20.0, 10.0)).export(str(stl))
    return stl


def _load_meta(case_dir):
    import json
    return json.loads((case_dir / "constant/case_meta.json").read_text(encoding="utf-8"))


def test_round_duct_writes_sealed_round_casing(tmp_path):
    """duct="round" (CFD_VERSION 4 default, kept for comparison) is no longer the default."""
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0,
                      duct="round")

    casing_path = case / "constant/triSurface/casing.stl"
    assert casing_path.exists()
    m = trimesh.load(str(casing_path), force="mesh")

    r = [math.hypot(v[0], v[1]) for v in m.vertices]
    inner_r = min(r)
    outer_r = max(r)
    assert inner_r == pytest.approx(rig.duct_radius, rel=0.05)
    H = BOX_SCALE * rig.duct_radius
    assert outer_r >= H * math.sqrt(2)

    bm = (case / "system/blockMeshDict").read_text(encoding="utf-8")
    assert f"{H:.6g}" in bm or _extract_half_width(bm) == pytest.approx(H, rel=1e-6)


def _extract_half_width(blockmesh_text: str) -> float:
    import re
    xs = [float(v) for v in re.findall(r"\(\s*([-\d.eE+]+)\s+[-\d.eE+]+\s+[-\d.eE+]+\s*\)",
                                        blockmesh_text.split("blocks")[0])[:8]]
    return max(xs)


def test_duct_square_writes_no_casing_legacy_half_width(tmp_path):
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0,
                      duct="square")
    assert not (case / "constant/triSurface/casing.stl").exists()
    bm = (case / "system/blockMeshDict").read_text(encoding="utf-8")
    assert _extract_half_width(bm) == pytest.approx(rig.duct_radius, rel=1e-6)


def test_invalid_duct_value_raises(tmp_path):
    rig = _rig()
    with pytest.raises(ValueError, match="duct"):
        build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0,
                  duct="hexagon")


def test_check_casing_seals_raises_for_thin_casing(tmp_path):
    rig = _rig()
    # Thin default casing (outer = R + 2.4mm) in a 1.12*R box -- corners open.
    thin = export_casing_stl(rig, tmp_path / "thin.stl", fill_radius_mm=(
        rig.duct_radius / MM_TO_M) + 2.4)
    m = trimesh.load(str(thin), force="mesh")
    H = BOX_SCALE * rig.duct_radius
    with pytest.raises(ValueError, match="seal|corner|radial"):
        check_casing_seals(m, H)


def test_check_casing_seals_passes_for_sealed_casing(tmp_path):
    rig = _rig()
    sealed = export_casing_stl(rig, tmp_path / "sealed.stl")  # new sealed default
    m = trimesh.load(str(sealed), force="mesh")
    H = BOX_SCALE * rig.duct_radius
    check_casing_seals(m, H)  # must not raise


def test_default_export_casing_stl_is_sealed_for_default_box(tmp_path):
    rig = _rig()
    for stepped in (False, True):
        casing = export_casing_stl(rig, tmp_path / f"c_{stepped}.stl", stepped=stepped)
        m = trimesh.load(str(casing), force="mesh")
        H = BOX_SCALE * rig.duct_radius
        check_casing_seals(m, H)  # must not raise


def test_case_meta_round_has_generated_source(tmp_path):
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0,
                      duct="round")
    meta = _load_meta(case)
    assert meta["duct_shape"] == "round"
    assert meta["duct_source"] == "generated"
