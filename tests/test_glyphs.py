"""Unit tests for fansim.cfd.glyphs (no Docker / no real OpenFOAM case)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from fansim.cfd.glyphs import (
    M_TO_MM,
    VelocityGlyphs,
    build_velocity_cloud,
    cfd_cloud_to_as_built,
    ensure_velocity_glyphs,
    make_glyph_arrows,
    schematic_axial_flow_cloud,
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


def test_glyph_memory_cache_skips_rebuild(tmp_path: Path, monkeypatch):
    """Reselect of the same case must hit the process cache (§22.1)."""
    from fansim.cfd import glyphs as glyphs_mod

    glyphs_mod.clear_glyph_cache()
    pv = pytest.importorskip("pyvista")
    case = tmp_path / "cased"
    case.mkdir()
    tdir = case / "500"
    tdir.mkdir()
    (tdir / "U").write_text("placeholder", encoding="utf-8")

    grid = pv.ImageData(
        dimensions=(6, 6, 6),
        spacing=(0.01, 0.01, 0.01),
        origin=(-0.025, -0.025, -0.025),
    )
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    u[:, 2] = 2.0
    grid.cell_data["U"] = u

    reads = {"n": 0}

    def _fake_read(_case):
        reads["n"] += 1
        return grid

    monkeypatch.setattr("fansim.acoustics.case.read_case", _fake_read)
    monkeypatch.setattr(glyphs_mod, "case_has_flow_fields", lambda _c: True)
    monkeypatch.setattr(glyphs_mod, "ensure_reconstructed", lambda *_a, **_k: True)

    a1 = ensure_velocity_glyphs(case, max_points=30)
    a2 = ensure_velocity_glyphs(case, max_points=30)
    assert a1.available and a2.available
    assert reads["n"] == 1
    assert a2.cloud is a1.cloud
    peek = glyphs_mod.peek_cached_velocity_glyphs(case, max_points=30)
    assert peek is not None and peek.available
    glyphs_mod.clear_glyph_cache()
    # Disk cache (§22.9) still serves after memory clear — no second read_case.
    peek2 = glyphs_mod.peek_cached_velocity_glyphs(case, max_points=30)
    assert peek2 is not None and peek2.available
    assert reads["n"] == 1
    a3 = ensure_velocity_glyphs(case, max_points=30)
    assert a3.available and reads["n"] == 1
    vtp, meta = glyphs_mod.glyph_artifact_paths(case)
    assert vtp.is_file() and meta.is_file()
    glyphs_mod.clear_glyph_cache()


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


def test_schematic_axial_flow_cloud_is_minus_z_in_annulus():
    pv = pytest.importorskip("pyvista")
    cloud = schematic_axial_flow_cloud(
        hub_radius_mm=20.0,
        tip_radius_mm=55.0,
        z_span_mm=30.0,
        u_axial_ms=2.5,
        n_radial=3,
        n_theta=8,
        n_axial=4,
    )
    assert cloud.n_points == 3 * 8 * 4
    assert "U" in cloud.point_data and "U_mag" in cloud.point_data
    u = np.asarray(cloud["U"])
    assert np.allclose(u[:, 0], 0.0) and np.allclose(u[:, 1], 0.0)
    # As-built preview: open intake +Z, exhaust past the motor at −Z (user-confirmed real fan;
    # Audit #1). CFD field glyphs are in the duct frame and come from the solve, not this cloud.
    assert np.allclose(u[:, 2], -2.5)
    r = np.hypot(cloud.points[:, 0], cloud.points[:, 1])
    assert r.min() > 20.0 and r.max() < 55.0
    arrows = make_glyph_arrows(cloud, factor=1.0, max_arrows=50)
    assert arrows is not None and arrows.n_points > 0


def test_make_glyph_arrows_subsamples():
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


def test_cfd_cloud_to_as_built_flipped_negates_y_and_z():
    pv = pytest.importorskip("pyvista")
    cloud = pv.PolyData(np.array([[1.0, 5.0, 3.0]]))
    cloud["U"] = np.array([[0.0, 0.0, 2.5]])
    cloud["U_mag"] = np.array([2.5])

    out = cfd_cloud_to_as_built(cloud, "flipped")
    assert np.allclose(out.points, [[1.0, -5.0, -3.0]])
    assert np.allclose(np.asarray(out["U"]), [[0.0, 0.0, -2.5]])
    assert np.allclose(np.asarray(out["U_mag"]), [2.5])  # magnitude unchanged


def test_cfd_cloud_to_as_built_as_built_is_identity():
    pv = pytest.importorskip("pyvista")
    cloud = pv.PolyData(np.array([[1.0, 5.0, 3.0]]))
    cloud["U"] = np.array([[0.0, 0.0, 2.5]])
    cloud["U_mag"] = np.array([2.5])

    out = cfd_cloud_to_as_built(cloud, "as_built")
    assert out is cloud


def test_cfd_cloud_to_as_built_rejects_invalid_orientation():
    pv = pytest.importorskip("pyvista")
    cloud = pv.PolyData(np.array([[0.0, 0.0, 0.0]]))
    cloud["U"] = np.array([[0.0, 0.0, 1.0]])
    cloud["U_mag"] = np.array([1.0])
    with pytest.raises(ValueError, match="orientation"):
        cfd_cloud_to_as_built(cloud, "sideways")


def test_glyph_length_caps_tip_spikes_at_p95():
    """§15.3: a few tip spikes must not set the arrow length scale."""
    pv = pytest.importorskip("pyvista")
    n = 100
    pts = np.zeros((n, 3), dtype=float)
    pts[:, 0] = np.linspace(-10, 10, n)
    cloud = pv.PolyData(pts)
    u = np.zeros((n, 3), dtype=float)
    u[:, 2] = 3.0
    u[-1, 2] = 30.0  # tip spike
    cloud["U"] = u
    cloud["U_mag"] = np.linalg.norm(u, axis=1)

    # Build with and without clamp; capped glyphs use smaller max scale input.
    src = cloud.copy(deep=True)
    mag = np.asarray(src["U_mag"], dtype=float)
    cap = float(np.percentile(mag, 95))
    assert cap < 30.0
    assert cap == pytest.approx(3.0, abs=0.5)
    arrows = make_glyph_arrows(cloud, factor=1.0, max_arrows=200, mag_percentile=95)
    assert arrows is not None and arrows.n_points > 0
    # Unclamped would scale the spike to 30×; with p95 the effective max scale is ~3.
    arrows_uncapped = make_glyph_arrows(cloud, factor=1.0, max_arrows=200, mag_percentile=100)
    assert arrows_uncapped is not None
    # Bounds of capped arrows should be tighter along Z than uncapped (spike arrow tip).
    assert arrows.bounds[5] - arrows.bounds[4] < arrows_uncapped.bounds[5] - arrows_uncapped.bounds[4]
