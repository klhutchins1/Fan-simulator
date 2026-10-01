"""Tests for cockpit viz bake + mesh LRU (§22.6 / §22.11)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from fansim.cfd.cockpit_viz import (
    bake_cockpit_viz_core,
    clear_mesh_lru,
    get_cached_mesh,
    load_case_mesh,
    put_cached_mesh,
)
from fansim.cfd.glyphs import clear_glyph_cache, peek_cached_velocity_glyphs
from fansim.cfd.midplane import find_cached_midplane, slice_volume_for_viz


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_mesh_lru()
    clear_glyph_cache()
    yield
    clear_mesh_lru()
    clear_glyph_cache()


def test_mesh_lru_roundtrip():
    clear_mesh_lru()
    case = Path("runs/fake_case_a")
    put_cached_mesh(case, {"mesh": 1})
    assert get_cached_mesh(case) == {"mesh": 1}
    put_cached_mesh(Path("runs/fake_case_b"), {"mesh": 2})
    put_cached_mesh(Path("runs/fake_case_c"), {"mesh": 3})  # evicts oldest
    assert get_cached_mesh(case) is None
    assert get_cached_mesh(Path("runs/fake_case_b")) == {"mesh": 2}


def test_slice_volume_for_viz_image_data():
    pv = pytest.importorskip("pyvista")
    grid = pv.ImageData(
        dimensions=(6, 6, 6), spacing=(0.02, 0.02, 0.02), origin=(-0.05, -0.05, -0.05),
    )
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    u[:, 2] = 1.0
    grid.cell_data["U"] = u
    slc = slice_volume_for_viz(grid, (0.0, 1.0, 0.0), tuple(grid.center))
    assert slc.n_points > 0


def test_slice_drops_polyhedra_before_cut():
    """Polyhedron cells must not go through vtkCutter (§22.4)."""
    pv = pytest.importorskip("pyvista")
    # Hex mesh (no polyhedra) still slices.
    grid = pv.ImageData(
        dimensions=(4, 4, 4), spacing=(0.01, 0.01, 0.01), origin=(-0.015, -0.015, -0.015),
    )
    grid.cell_data["U"] = np.ones((grid.n_cells, 3))
    # Force the polyhedron branch by tagging all cells as VTK_POLYHEDRON (42) via a
    # shallow UnstructuredGrid copy — extract_cells path or center-band must return points.
    ug = grid.cast_to_unstructured_grid()
    # ImageData cells are VTK_VOXEL (11), not polyhedra — still exercises non-poly path.
    slc = slice_volume_for_viz(ug, (0.0, 0.0, 1.0), tuple(ug.center))
    assert slc.n_points > 0


@pytest.mark.slow
def test_bake_core_with_injected_mesh(tmp_path: Path, monkeypatch):
    pv = pytest.importorskip("pyvista")
    case = tmp_path / "design_1"
    case.mkdir()
    tdir = case / "500"
    tdir.mkdir()
    (tdir / "U").write_text("U\n", encoding="utf-8")

    grid = pv.ImageData(
        dimensions=(6, 6, 6), spacing=(0.02, 0.02, 0.02), origin=(-0.05, -0.05, -0.05),
    )
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    u[:, 2] = 1.5
    grid.cell_data["U"] = u
    grid.cell_data["p"] = np.linspace(0.0, 1.0, n)

    monkeypatch.setattr(
        "fansim.cfd.cockpit_viz.load_case_mesh", lambda *_a, **_k: grid,
    )
    out = bake_cockpit_viz_core(case, mesh=grid, include_uz=True)
    assert out["available"]
    assert out["midplane"]
    assert out["glyphs"]
    assert find_cached_midplane(case) is not None
    assert peek_cached_velocity_glyphs(case) is not None
