"""Unit tests for fansim.cfd.midplane (no Docker / no real OpenFOAM case)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from fansim.cfd.midplane import (
    AxialSliceArtifact,
    MidplaneArtifacts,
    artifact_paths,
    axial_artifact_path,
    case_has_flow_fields,
    ensure_axial_uz_artifact,
    ensure_midplane_artifacts,
    ensure_reconstructed,
    find_cached_midplane,
    has_decomposed_fields,
    has_reconstructed_fields,
    render_axial_uz_png,
    render_midplane_pngs,
    throughflow_umag_clim,
    render_streamlines_png,
    streamline_artifact_path,
)
from fansim.cfd.midplane import (
    StreamlineArtifact,
    ensure_streamlines_artifact,
)


def _touch_u(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("U\n", encoding="utf-8")


def test_has_reconstructed_and_decomposed(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    assert not has_reconstructed_fields(case)
    assert not has_decomposed_fields(case)
    assert not case_has_flow_fields(case)

    _touch_u(case / "0" / "U")
    assert not has_reconstructed_fields(case)  # t=0 ignored

    _touch_u(case / "1000" / "U")
    (case / "1000" / "p").write_text("p\n", encoding="utf-8")
    assert has_reconstructed_fields(case)
    assert case_has_flow_fields(case)

    case2 = tmp_path / "decomp"
    case2.mkdir()
    _touch_u(case2 / "processor3" / "500" / "U")
    assert has_decomposed_fields(case2)
    assert not has_reconstructed_fields(case2)
    assert case_has_flow_fields(case2)


def test_find_cached_midplane(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    assert find_cached_midplane(case) is None
    u_png, p_png = artifact_paths(case)
    u_png.parent.mkdir(parents=True)
    u_png.write_bytes(b"fake")
    cached = find_cached_midplane(case)
    assert cached is not None
    assert cached.available
    assert "Umag" in cached.caption
    assert cached.p_png is None
    assert "FRONT" in cached.caption


def test_ensure_reconstructed_skips_when_already_done(tmp_path: Path):
    case = tmp_path / "case"
    _touch_u(case / "1000" / "U")
    calls: list[str] = []

    class FakeRunner:
        def __init__(self, _case):
            pass

        def run(self, cmd, check=False):
            calls.append(cmd)
            raise AssertionError("should not reconstruct")

    assert ensure_reconstructed(case, runner_factory=FakeRunner, image_ok=lambda: True)
    assert calls == []


def test_ensure_reconstructed_runs_when_decomposed(tmp_path: Path):
    case = tmp_path / "case"
    _touch_u(case / "processor0" / "1000" / "U")
    calls: list[str] = []

    class FakeResult:
        ok = True

    class FakeRunner:
        def __init__(self, _case):
            pass

        def run(self, cmd, check=False):
            calls.append(cmd)
            # Simulate reconstruct writing root time dir
            _touch_u(case / "1000" / "U")
            return FakeResult()

    assert ensure_reconstructed(case, runner_factory=FakeRunner, image_ok=lambda: True)
    assert calls == ["reconstructPar -latestTime"]
    assert has_reconstructed_fields(case)


def test_ensure_reconstructed_false_when_docker_down(tmp_path: Path):
    case = tmp_path / "case"
    _touch_u(case / "processor0" / "1000" / "U")
    assert not ensure_reconstructed(case, image_ok=lambda: False)


def test_throughflow_umag_clim_ignores_the_tip_spike():
    values = np.array([1.0] * 95 + [200.0] * 5)
    lo, hi = throughflow_umag_clim(values)
    assert lo == 0.0
    assert hi < 50.0
    assert throughflow_umag_clim([]) == (0.0, 0.5)


def test_ensure_midplane_unavailable_without_fields(tmp_path: Path):
    case = tmp_path / "empty"
    case.mkdir()
    (case / "impeller.stl").write_text("solid", encoding="utf-8")
    art = ensure_midplane_artifacts(case)
    assert not art.available
    assert art.caption == "Airflow not available for this design"


def test_ensure_midplane_none_case():
    art = ensure_midplane_artifacts(None)
    assert not art.available
    assert "not available" in art.caption.lower()


@pytest.mark.slow
def test_render_midplane_pngs_synthetic_mesh(tmp_path: Path):
    pv = pytest.importorskip("pyvista")
    case = tmp_path / "case"
    case.mkdir()
    # Unit cube with a uniform +Z velocity and linear pressure
    grid = pv.ImageData(dimensions=(6, 6, 6), spacing=(0.02, 0.02, 0.02), origin=(-0.05, -0.05, -0.05))
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    u[:, 2] = 1.5
    grid.cell_data["U"] = u
    grid.cell_data["p"] = np.linspace(0.0, 10.0, n)

    art = render_midplane_pngs(case, mesh=grid)
    assert art.available
    assert art.u_png is not None and art.u_png.is_file()
    assert art.p_png is not None and art.p_png.is_file()
    assert art.u_png.stat().st_size > 100
    assert "Umag" in art.caption
    assert "FRONT" in art.caption
    assert "LEFT" in art.caption
    assert art.u_png.name == "U_midplane_v9.png"


@pytest.mark.slow
def test_render_midplane_scroll_layout_keeps_full_extent(tmp_path: Path):
    """Scroll layout must not tip-crop: outlet stub lives beyond r_tip at +X."""
    pv = pytest.importorskip("pyvista")
    case = tmp_path / "case"
    case.mkdir()
    # Wide in X (scroll + outlet) and short in Z — axial crop would clip to ~r_tip.
    grid = pv.ImageData(
        dimensions=(20, 6, 8),
        spacing=(0.02, 0.02, 0.02),
        origin=(-0.05, -0.05, -0.05),
    )
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    u[:, 0] = 1.2  # radial discharge toward +X
    grid.cell_data["U"] = u
    grid.cell_data["p"] = np.linspace(0.0, 5.0, n)

    art = render_midplane_pngs(case, mesh=grid, layout="scroll")
    assert art.available
    assert art.u_png is not None and art.u_png.is_file()
    assert art.u_png.name == "U_midplane_scroll_v2.png"
    assert "scroll" in art.caption.lower()
    assert "OUTLET" in art.caption


def test_find_cached_midplane_scroll_uses_separate_names(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    assert find_cached_midplane(case, layout="scroll") is None
    u_png, _p = artifact_paths(case, layout="scroll")
    u_png.parent.mkdir(parents=True)
    u_png.write_bytes(b"fake")
    cached = find_cached_midplane(case, layout="scroll")
    assert cached is not None and cached.available
    assert "scroll" in cached.caption.lower()
    # Axial cache must stay independent.
    assert find_cached_midplane(case, layout="axial") is None


@pytest.mark.slow
def test_render_axial_uz_png_synthetic_mesh(tmp_path: Path):
    pv = pytest.importorskip("pyvista")
    case = tmp_path / "case"
    case.mkdir()
    # Cube spanning z=0 with mixed axial flow: forward (+Z) on one half, reverse (−Z) on the
    # other, so the diverging slice has both signs.
    grid = pv.ImageData(dimensions=(8, 8, 8), spacing=(0.02, 0.02, 0.02),
                        origin=(-0.07, -0.07, -0.07))
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    cc = grid.cell_centers().points
    u[:, 2] = np.where(cc[:, 0] >= 0.0, 2.0, -1.5)  # +Z one side, reverse the other
    grid.cell_data["U"] = u

    art = render_axial_uz_png(case, mesh=grid)
    assert art.available
    assert art.png is not None and art.png.is_file()
    assert art.png.stat().st_size > 100
    assert art.png.name == "U_axial_slice_v2.png"
    assert "reverse" in art.caption


def test_ensure_axial_uz_uses_cache(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    png = axial_artifact_path(case)
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 20)
    art = ensure_axial_uz_artifact(case, force=False)
    assert isinstance(art, AxialSliceArtifact)
    assert art.available
    assert art.png == png


def test_ensure_axial_uz_unavailable_without_fields(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    art = ensure_axial_uz_artifact(case, force=False)
    assert not art.available
    assert art.png is None


@pytest.mark.slow
def test_render_streamlines_png_synthetic_mesh(tmp_path: Path):
    pv = pytest.importorskip("pyvista")
    case = tmp_path / "case"
    case.mkdir()
    # Uniform +Z flow in a domain with a long wake (the renderer seeds downstream of the rotor
    # and integrates into the wake, so it needs Z room past the seed plane).
    grid = pv.ImageData(dimensions=(10, 10, 40), spacing=(0.01, 0.01, 0.01),
                        origin=(-0.045, -0.045, -0.2))
    n = grid.n_cells
    u = np.zeros((n, 3), dtype=float)
    u[:, 2] = 2.0
    grid.cell_data["U"] = u

    art = render_streamlines_png(case, mesh=grid, n_seed=48)
    assert art.available
    assert art.png is not None and art.png.is_file()
    assert art.png.stat().st_size > 100
    assert art.png.name == "streamlines_v2.png"
    assert "streamlines" in art.caption


def test_ensure_streamlines_uses_cache(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    png = streamline_artifact_path(case)
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 20)
    art = ensure_streamlines_artifact(case, force=False)
    assert isinstance(art, StreamlineArtifact)
    assert art.available and art.png == png


def test_ensure_streamlines_unavailable_without_fields(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    art = ensure_streamlines_artifact(case, force=False)
    assert not art.available and art.png is None


def test_ensure_midplane_uses_cache(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    u_png, _ = artifact_paths(case)
    u_png.parent.mkdir(parents=True)
    u_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 20)
    art = ensure_midplane_artifacts(case, force=False)
    assert isinstance(art, MidplaneArtifacts)
    assert art.available
    assert art.u_png == u_png


def test_robust_clim_ignores_spikes():
    from fansim.cfd.midplane import robust_clim
    v = np.r_[np.linspace(0, 5, 1000), [400.0, 500.0]]
    lo, hi = robust_clim(v)
    assert lo == pytest.approx(0.1, abs=0.05) and hi < 6.0
    slo, shi = robust_clim(np.r_[v, -v], symmetric=True)
    assert slo == -shi


def test_pressure_pa_scales_by_rho():
    from fansim.cfd.midplane import pressure_pa
    assert pressure_pa(np.array([10.0]))[0] == pytest.approx(12.0)


def test_rotor_outline_none_without_stl(tmp_path):
    from fansim.cfd.midplane import rotor_outline
    assert rotor_outline(tmp_path, (0, 1, 0), (0, 0, 0)) is None


def test_rotor_outline_slices_stl(tmp_path):
    import pyvista as pv
    from fansim.cfd.midplane import rotor_outline
    tri = tmp_path / "constant" / "triSurface"
    tri.mkdir(parents=True)
    pv.Cylinder(radius=0.05, height=0.01, direction=(0, 0, 1)).triangulate().save(tri / "impeller.stl")
    out = rotor_outline(tmp_path, (0, 1, 0), (0, 0, 0))
    assert out is not None and out.n_points > 0


def test_streamline_seeds_upstream_rings():
    from fansim.cfd.midplane import streamline_seed_points
    s = streamline_seed_points(0.05, 0.0, n_per_ring=12)
    pts = np.asarray(s.points)
    assert pts.shape == (36, 3)
    assert np.allclose(pts[:, 2], -0.05)
    radii = sorted(set(np.round(np.hypot(pts[:, 0], pts[:, 1]), 6)))
    assert radii == pytest.approx([0.02, 0.0325, 0.045])


def test_duct_clim_ignores_rotor_zone_spikes():
    """Pressure colours follow the duct, not the dense, extreme blade-tip points (§24)."""
    from fansim.cfd.midplane import duct_clim
    z = np.r_[np.linspace(-0.2, -0.05, 200), np.zeros(800), np.linspace(0.05, 0.3, 200)]
    v = np.r_[np.linspace(0.0, 1.0, 200), np.r_[np.full(400, -40.0), np.full(400, 40.0)],
              np.linspace(8.0, 9.0, 200)]
    lo, hi = duct_clim(z, v, z_fan=0.0, tip_r=0.05)
    assert lo >= -0.1 and hi <= 9.1
