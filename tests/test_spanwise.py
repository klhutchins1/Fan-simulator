"""Unit tests for fansim.cfd.spanwise (no Docker / no real OpenFOAM case)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from fansim.cfd.spanwise import (
    SpanwiseArtifacts,
    b2b_artifact_path,
    compute_blade_to_blade_cp,
    compute_spanwise_profile,
    cylindrical_velocity,
    ensure_spanwise_artifacts,
    find_cached_spanwise,
    load_case_radii_omega,
    load_metal_angles_deg,
    metal_angle_from_stagger_deg,
    relative_flow_angle_deg,
    render_spanwise_artifacts,
    spanwise_artifact_path,
    total_pressure_kin,
)


def _annulus_points(
    *,
    hub_r: float = 0.02,
    tip_r: float = 0.055,
    n_r: int = 12,
    n_th: int = 36,
    n_z: int = 10,
    z_span: float = 0.04,
) -> np.ndarray:
    """Structured (r, θ, z) → Cartesian points filling an annulus."""
    rs = np.linspace(hub_r + 0.001, tip_r - 0.001, n_r)
    ths = np.linspace(-np.pi, np.pi, n_th, endpoint=False)
    zs = np.linspace(-z_span, z_span, n_z)
    pts = []
    for r in rs:
        for th in ths:
            for z in zs:
                pts.append((r * np.cos(th), r * np.sin(th), z))
    return np.asarray(pts, dtype=float)


def test_metal_angle_from_stagger():
    assert metal_angle_from_stagger_deg(90.0) == pytest.approx(0.0)
    assert metal_angle_from_stagger_deg(0.0) == pytest.approx(90.0)
    assert metal_angle_from_stagger_deg(40.0) == pytest.approx(50.0)


def test_cylindrical_velocity_and_total_pressure():
    # Point on +X axis: ê_θ = (0, 1, 0); U = (0, 2, 3) → Uθ = 2, Uz = 3
    pts = np.array([[0.05, 0.0, 0.0]])
    u = np.array([[0.0, 2.0, 3.0]])
    r, uz, uth = cylindrical_velocity(pts, u)
    assert r[0] == pytest.approx(0.05)
    assert uz[0] == pytest.approx(3.0)
    assert uth[0] == pytest.approx(2.0)
    p0 = total_pressure_kin(np.array([1.0]), u)
    assert p0[0] == pytest.approx(1.0 + 0.5 * (0 + 4 + 9))


def test_relative_flow_angle_solid_body_swirl():
    # Absolute Uθ = ω r → relative Wθ = 0 → β = 0 for pure axial.
    r = np.array([0.04, 0.05])
    omega = 100.0
    uz = np.array([2.0, 2.0])
    uth = omega * r
    beta = relative_flow_angle_deg(uz, uth, r, omega)
    assert beta == pytest.approx(np.zeros(2), abs=1e-9)


def test_compute_spanwise_profile_tip_deficit():
    """Tip band with lower p0 / Uz must show up in the circumferential average."""
    hub, tip = 0.02, 0.055
    pts = _annulus_points(hub_r=hub, tip_r=tip, n_r=16, n_th=24, n_z=12, z_span=0.03)
    r = np.sqrt(pts[:, 0] ** 2 + pts[:, 1] ** 2)
    r_frac = (r - hub) / (tip - hub)
    u = np.zeros((pts.shape[0], 3), dtype=float)
    u[:, 2] = 3.0 - 2.0 * np.clip((r_frac - 0.7) / 0.3, 0.0, 1.0)  # tip stall
    # Solid-body swirl + omega so relative angle is mild.
    omega = 200.0
    u_th = 0.6 * omega * r
    # Reconstruct Cartesian swirl: U = Uθ ê_θ
    x, y = pts[:, 0], pts[:, 1]
    r_safe = np.maximum(r, 1e-12)
    u[:, 0] = -u_th * (y / r_safe)
    u[:, 1] = u_th * (x / r_safe)
    p = 5.0 - 4.0 * np.clip((r_frac - 0.7) / 0.3, 0.0, 1.0)

    metal = np.full(20, 50.0)
    prof = compute_spanwise_profile(
        pts, u, p, hub_r=hub, tip_r=tip, omega=omega, metal_deg=metal, n_radial=20,
    )
    assert prof.r_m.shape == prof.p0_kin.shape
    assert np.any(np.isfinite(prof.p0_kin))
    assert np.any(np.isfinite(prof.u_axial))
    # Tip bins (outer 20%) should average lower Uz than hub/mid.
    hub_mid = (prof.r_frac >= 0.2) & (prof.r_frac <= 0.5) & np.isfinite(prof.u_axial)
    tip_band = (prof.r_frac >= 0.8) & np.isfinite(prof.u_axial)
    assert np.any(hub_mid) and np.any(tip_band)
    assert float(np.nanmean(prof.u_axial[tip_band])) < float(np.nanmean(prof.u_axial[hub_mid]))
    assert prof.incidence_deg is not None
    assert prof.deviation_deg is not None


def test_blade_to_blade_cp_has_finite_cells():
    hub, tip = 0.02, 0.055
    pts = _annulus_points(hub_r=hub, tip_r=tip, n_r=10, n_th=48, n_z=16, z_span=0.025)
    th = np.arctan2(pts[:, 1], pts[:, 0])
    # Two-blade-ish pressure variation in θ.
    p = 2.0 * np.cos(2.0 * th) + 0.1 * pts[:, 2]
    u = np.zeros((pts.shape[0], 3))
    u[:, 2] = 2.5
    slc = compute_blade_to_blade_cp(
        pts, p, u, hub_r=hub, tip_r=tip, r_frac=0.55, n_theta=36, n_z=24,
    )
    assert slc.cp.shape == (24, 36)
    assert np.any(np.isfinite(slc.cp))
    # Peak-to-peak Cp should be nonzero (periodic loading).
    finite = slc.cp[np.isfinite(slc.cp)]
    assert float(np.nanmax(finite) - np.nanmin(finite)) > 0.1


def test_load_metal_angles_from_design_json(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    (case / "design.json").write_text(
        json.dumps({
            "params": {
                "stagger_root": 30.0,
                "stagger_mid": 40.0,
                "stagger_tip": 50.0,
                "hub_radius": 18.625,
                "tip_radius": 55.0,
            }
        }),
        encoding="utf-8",
    )
    rf = np.array([0.0, 0.5, 1.0])
    metal = load_metal_angles_deg(case, rf)
    assert metal is not None
    assert metal[0] == pytest.approx(60.0)  # 90 - 30
    assert metal[1] == pytest.approx(50.0)
    assert metal[2] == pytest.approx(40.0)
    hub, tip, _omega = load_case_radii_omega(case)
    assert hub == pytest.approx(0.018625)
    assert tip == pytest.approx(0.055)


def test_find_cached_and_ensure_without_fields(tmp_path: Path):
    case = tmp_path / "case"
    case.mkdir()
    assert find_cached_spanwise(case) is None
    art = ensure_spanwise_artifacts(case, force=False)
    assert not art.available
    assert art.spanwise_png is None

    png = spanwise_artifact_path(case)
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 20)
    cached = find_cached_spanwise(case)
    assert cached is not None and cached.available
    assert cached.spanwise_png == png
    art2 = ensure_spanwise_artifacts(case, force=False)
    assert art2.available and art2.spanwise_png == png


def test_ensure_spanwise_none_case():
    art = ensure_spanwise_artifacts(None)
    assert not art.available
    assert "not available" in art.caption.lower()


@pytest.mark.slow
def test_render_spanwise_artifacts_synthetic_mesh(tmp_path: Path):
    pv = pytest.importorskip("pyvista")
    case = tmp_path / "case"
    case.mkdir()
    (case / "constant").mkdir()
    (case / "constant" / "case_meta.json").write_text(
        json.dumps({
            "hub_radius_m": 0.02,
            "tip_radius_m": 0.055,
            "rpm": 2000,
            "spin": 1,
            "omega_signed": 2000 * 2 * np.pi / 60,
        }),
        encoding="utf-8",
    )
    (case / "design.json").write_text(
        json.dumps({
            "params": {
                "stagger_root": 35.0,
                "stagger_mid": 40.0,
                "stagger_tip": 48.0,
            }
        }),
        encoding="utf-8",
    )

    # Structured grid covering the annulus (cartesian ImageData is fine for sampling).
    grid = pv.ImageData(
        dimensions=(24, 24, 20),
        spacing=(0.006, 0.006, 0.004),
        origin=(-0.07, -0.07, -0.04),
    )
    n = grid.n_cells
    cc = grid.cell_centers().points
    r = np.sqrt(cc[:, 0] ** 2 + cc[:, 1] ** 2)
    u = np.zeros((n, 3), dtype=float)
    u[:, 2] = 2.5
    # Mild swirl
    r_safe = np.maximum(r, 1e-12)
    uth = 1.5 * (r / 0.055)
    u[:, 0] = -uth * (cc[:, 1] / r_safe)
    u[:, 1] = uth * (cc[:, 0] / r_safe)
    grid.cell_data["U"] = u
    grid.cell_data["p"] = 2.0 - 0.5 * (r / 0.055)

    art = render_spanwise_artifacts(case, mesh=grid)
    assert isinstance(art, SpanwiseArtifacts)
    assert art.available
    assert art.spanwise_png is not None and art.spanwise_png.is_file()
    assert art.b2b_png is not None and art.b2b_png.is_file()
    assert art.spanwise_png.stat().st_size > 500
    assert art.b2b_png.stat().st_size > 500
    assert art.spanwise_png.name == "spanwise_avg_v2.png"
    assert art.b2b_png.name == "b2b_cp_v1.png"
    assert art.profile is not None
    assert "spanwise" in art.caption.lower() or "blade" in art.caption.lower()

    # Cache hit path
    art2 = ensure_spanwise_artifacts(case, force=False)
    assert art2.available and art2.spanwise_png == art.spanwise_png
    assert b2b_artifact_path(case).is_file()
