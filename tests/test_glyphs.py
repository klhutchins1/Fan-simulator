"""Unit tests for fansim.cfd.glyphs (no Docker / no real OpenFOAM case)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from fansim.cfd.glyphs import (
    M_TO_MM,
    VelocityGlyphs,
    build_velocity_cloud,
    ensure_velocity_glyphs,
    make_glyph_arrows,
)


def test_ensure_glyphs_unavailable_without_fields(tmp_path: Path):
    case = tmp_path / "empty"
    case.mkdir()
    (case / "impeller.stl").write_text("solid", encoding="utf-8")
    art = ensure_velocity_glyphs(case)
    assert not art.available
    assert art.cloud is None
    assert "not available" in art.caption.lower()


def test_ensure_glyphs_none_case():
    art = ensure_velocity_glyphs(None)
    assert not art.available
    assert art.n_points == 0


def test_build_velocity_cloud_scales_m_to_mm_and_subsamples():
    pv = pytest.importorskip("pyvista")
    # ~70 mm cube in meters, uniform +Z flow
    grid = pv.ImageData(
        dimensions=(10, 10, 10),
        spacing=(0.008, 0.008, 0.008),
        origin=(-0.036, -0.036, -0.036),
    )
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    u[:, 2] = 3.0
    grid.cell_data["U"] = u

    cloud = build_velocity_cloud(grid, max_points=40, z_half_span_m=0.05, scale_m_to_mm=True)
    assert cloud.n_points <= 40
    assert cloud.n_points > 0
    assert "U" in cloud.point_data
    assert "U_mag" in cloud.point_data
    # meters→mm: extents should be O(10–100), not O(0.01–0.1)
    b = cloud.bounds
    assert abs(b[0]) > 1.0 and abs(b[1]) > 1.0
    assert np.allclose(cloud["U_mag"], 3.0)
    # spot-check scale factor
    centers_m = grid.cell_centers().points
    assert np.max(np.abs(cloud.points)) == pytest.approx(
        np.max(np.abs(centers_m)) * M_TO_MM, rel=1e-6, abs=1e-3,
    )


def test_build_velocity_cloud_z_clip_prefers_near_impeller():
    pv = pytest.importorskip("pyvista")
    grid = pv.ImageData(
        dimensions=(4, 4, 20),
        spacing=(0.01, 0.01, 0.02),
        origin=(-0.015, -0.015, -0.2),
    )
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    u[:, 0] = 1.0
    grid.cell_data["U"] = u
    cloud = build_velocity_cloud(grid, max_points=500, z_half_span_m=0.05, scale_m_to_mm=True)
    z_mm = cloud.points[:, 2]
    assert np.all(np.abs(z_mm) <= 0.05 * M_TO_MM + 1e-6)


def test_make_glyph_arrows_respects_max_and_stride():
    pv = pytest.importorskip("pyvista")
    pts = np.random.default_rng(0).uniform(-20, 20, size=(200, 3))
    cloud = pv.PolyData(pts)
    u = np.zeros((200, 3), dtype=float)
    u[:, 2] = 2.0
    cloud["U"] = u
    cloud["U_mag"] = np.full(200, 2.0)

    arrows = make_glyph_arrows(cloud, stride=4, factor=1.5, max_arrows=30)
    assert arrows is not None
    assert arrows.n_points > 0
    # fewer seed points than full cloud
    seeds = make_glyph_arrows(cloud, stride=10, factor=1.0, max_arrows=15)
    assert seeds is not None


def test_ensure_velocity_glyphs_with_injected_mesh(tmp_path: Path):
    pv = pytest.importorskip("pyvista")
    case = tmp_path / "case"
    case.mkdir()
    grid = pv.ImageData(
        dimensions=(6, 6, 6),
        spacing=(0.01, 0.01, 0.01),
        origin=(-0.025, -0.025, -0.025),
    )
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    u[:, 2] = 1.25
    grid.cell_data["U"] = u

    art = ensure_velocity_glyphs(case, mesh=grid, max_points=50)
    assert isinstance(art, VelocityGlyphs)
    assert art.available
    assert art.cloud is not None
    assert art.n_points == art.cloud.n_points
    assert art.n_points <= 50
    arrows = make_glyph_arrows(art.cloud, factor=2.0, max_arrows=40)
    assert arrows is not None and arrows.n_cells > 0
