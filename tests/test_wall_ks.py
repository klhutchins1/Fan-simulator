"""Opt-in OpenFOAM wall ks + thickness-aware print η (roadmap §7.6 stage 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.cfd.wall_roughness import (
    FDM_WALL_KS_MM,
    ROUGH_CS,
    nut_wall_bc,
    wall_ks_m,
)
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.optimize.print_penalty import (
    PRINT_K_CFM,
    PRINT_K_ETA,
    PRINT_K_ETA_THICK,
    apply_print_penalty,
    print_k_eta_for_thickness,
    tip_section_thickness,
)


def _tiny_stl(path: Path):
    import numpy as np
    import trimesh

    m = trimesh.Trimesh(
        vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float),
        faces=np.array([[0, 1, 2]], dtype=int),
        process=False,
    )
    m.export(str(path))
    return path


def test_wall_ks_m_converts_mm():
    assert wall_ks_m(None) == 0.0
    assert wall_ks_m(0) == 0.0
    assert wall_ks_m(FDM_WALL_KS_MM) == pytest.approx(1e-4)


def test_nut_wall_bc_smooth_default():
    text = nut_wall_bc("impeller")
    assert "nutkWallFunction" in text
    assert "nutkRoughWallFunction" not in text


def test_nut_wall_bc_rough_writes_ks_cs():
    text = nut_wall_bc("impeller", wall_ks_m=1e-4)
    assert "nutkRoughWallFunction" in text
    assert "Ks              uniform 0.0001" in text
    assert f"Cs              uniform {ROUGH_CS}" in text
    assert "impeller" in text


def test_build_case_wall_ks_writes_rough_impeller_smooth_casing(tmp_path):
    from fansim.cfd.domain import rig_for_impeller
    from fansim.cfd.openfoam_case import MeshResolution, build_case

    import trimesh

    stl = _tiny_stl(tmp_path / "imp.stl")
    fr = _tiny_stl(tmp_path / "frame.stl")
    rig = rig_for_impeller(BladeParams(), tip_gap_mm=0.5)
    # A casing must seal the hex corners (check_casing_seals), so use a real sealed annulus
    # rather than a 1 mm stub triangle.
    cas = tmp_path / "casing.stl"
    trimesh.creation.annulus(r_min=rig.duct_radius * 1000.0, r_max=120.0, height=20.0,
                             sections=64).export(str(cas))
    case = build_case(
        tmp_path / "c_ks",
        stl,
        rig,
        mesh=MeshResolution(),
        n_iters=10,
        frame_stl_mm=fr,
        casing_stl_mm=cas,
        wall_ks_mm=FDM_WALL_KS_MM,
    )
    nut = (case / "0/nut").read_text(encoding="utf-8")
    assert nut.count("nutkRoughWallFunction") == 2  # impeller + frame; casing smooth
    casing_idx = nut.index("casing")
    casing_block = nut[casing_idx:casing_idx + 200]
    assert "nutkWallFunction" in casing_block
    assert "nutkRoughWallFunction" not in casing_block


def test_build_case_default_stays_smooth(tmp_path):
    from fansim.cfd.domain import rig_for_impeller
    from fansim.cfd.openfoam_case import MeshResolution, build_case

    stl = _tiny_stl(tmp_path / "imp.stl")
    rig = rig_for_impeller(BladeParams(), tip_gap_mm=0.5)
    case = build_case(tmp_path / "c0", stl, rig, mesh=MeshResolution(), n_iters=10)
    nut = (case / "0/nut").read_text(encoding="utf-8")
    assert "nutkRoughWallFunction" not in nut
    assert "nutkWallFunction" in nut


def test_print_k_eta_thickness_lerp():
    assert print_k_eta_for_thickness(None) == pytest.approx(PRINT_K_ETA)
    assert print_k_eta_for_thickness(0.03) == pytest.approx(PRINT_K_ETA)
    assert print_k_eta_for_thickness(0.10) == pytest.approx(PRINT_K_ETA_THICK)
    mid = print_k_eta_for_thickness(0.07)
    assert PRINT_K_ETA < mid < PRINT_K_ETA_THICK


def test_apply_print_penalty_thick_tip_eases_eta():
    _, _, eta, stamps = apply_print_penalty(100.0, 80.0, 40.0, tip_thickness=0.10)
    assert eta == pytest.approx(40.0 * PRINT_K_ETA_THICK)
    assert stamps["print_k_cfm"] == pytest.approx(PRINT_K_CFM)
    assert stamps["print_k_eta"] == pytest.approx(PRINT_K_ETA_THICK)
    assert stamps["print_tip_thickness"] == pytest.approx(0.10)


def test_tip_section_thickness_reads_tip_station():
    p = BladeParams(stations=[
        RadialStation(0.0, 30.0, 25.0, thickness=0.08),
        RadialStation(1.0, 35.0, 20.0, thickness=0.11),
    ])
    assert tip_section_thickness(p) == pytest.approx(0.11)
