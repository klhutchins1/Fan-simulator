"""Geometry-golden helpers for ``blade.py`` sign-off (roadmap §15.2).

Stock a12x25 is a parametric approximation of the close-ref STL (not OEM CAD), so
absolute volume will not match the mesh tightly. The golden freezes *parametric*
volume / bounds / tip-section samples for regression, and soft-envelopes tip /
axial depth against ``validation/reference/a12x25_impeller.stl``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from fansim.geometry.blade import BladeParams, build_impeller_preview, tip_section_points
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat
from fansim.validation.reference_stl import DEFAULT_REFERENCE_STL, measure_silhouette

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = ROOT / "validation" / "reference" / "a12x25_blade_golden.json"

# Tip | axial soft envelope vs close-ref (parametric stock is approximate).
CLOSE_REF_TIP_TOL_MM = 1.5
CLOSE_REF_AXIAL_TOL_MM = 1.5

# Self-golden tolerances (OCCT / tessellation jitter).
VOLUME_RTOL = 0.02
BOUNDS_ATOL_MM = 0.75
SECTION_ATOL_MM = 0.25
SECTION_STRIDE = 8


def stock_a12x25_params() -> BladeParams:
    return blade_from_flat(stock_blade_flat("a12x25"), Features())


def tip_section_xyz(params: BladeParams) -> np.ndarray:
    return np.asarray([[p.x, p.y, p.z] for p in tip_section_points(params)], dtype=float)


def measure_stock_golden(params: BladeParams | None = None) -> dict[str, Any]:
    """Build stock (or given) impeller preview and return golden-comparable metrics."""
    params = params or stock_a12x25_params()
    mesh, volume_mm3 = build_impeller_preview(params)
    bounds = np.asarray(mesh.bounds, dtype=float)
    tip_xyz = tip_section_xyz(params)
    r = np.sqrt(mesh.vertices[:, 0] ** 2 + mesh.vertices[:, 1] ** 2)
    return {
        "schema": 1,
        "fan_model": "a12x25",
        "n_blades": int(params.n_blades),
        "volume_mm3": float(volume_mm3),
        "bounds_mm": bounds.tolist(),
        "mesh_tip_radius_mm": float(np.percentile(r, 99.5)),
        "mesh_axial_depth_mm": float(mesh.extents[2]),
        "tip_section_sample_mm": tip_xyz[::SECTION_STRIDE].round(3).tolist(),
        "hub_radius_mm": float(params.hub_radius),
        "tip_radius_mm": float(params.tip_radius),
        "hub_height_mm": float(getattr(params, "hub_height_mm", 0.0) or 0.0),
    }


def load_golden(path: Path | None = None) -> dict[str, Any]:
    p = path or GOLDEN_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def write_golden(path: Path | None = None, metrics: dict[str, Any] | None = None) -> Path:
    p = path or GOLDEN_PATH
    data = metrics or measure_stock_golden()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return p


def assert_matches_golden(
    measured: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    assert measured["n_blades"] == expected["n_blades"]
    vol_e = float(expected["volume_mm3"])
    vol_m = float(measured["volume_mm3"])
    if vol_e <= 0.0 or abs(vol_m - vol_e) / vol_e > VOLUME_RTOL:
        raise AssertionError(
            f"volume drifted: measured={vol_m:.1f} expected={vol_e:.1f} "
            f"(rtol={VOLUME_RTOL})"
        )
    m_b = np.asarray(measured["bounds_mm"], dtype=float)
    e_b = np.asarray(expected["bounds_mm"], dtype=float)
    assert m_b.shape == e_b.shape
    assert np.allclose(m_b, e_b, atol=BOUNDS_ATOL_MM), (
        f"bounds drifted: max |Δ|={float(np.max(np.abs(m_b - e_b))):.3f} mm"
    )
    m_s = np.asarray(measured["tip_section_sample_mm"], dtype=float)
    e_s = np.asarray(expected["tip_section_sample_mm"], dtype=float)
    assert m_s.shape == e_s.shape
    assert np.allclose(m_s, e_s, atol=SECTION_ATOL_MM), (
        f"tip section drifted: max |Δ|={float(np.max(np.abs(m_s - e_s))):.3f} mm"
    )


def assert_close_ref_envelope(
    measured: dict[str, Any],
    stl_path: Path | None = None,
) -> None:
    """Soft tip / axial gate vs close-ref STL (not a volume match)."""
    path = stl_path or DEFAULT_REFERENCE_STL
    if not path.is_file():
        return
    ref = measure_silhouette(path)
    assert abs(measured["mesh_tip_radius_mm"] - ref.tip_radius_mm) <= CLOSE_REF_TIP_TOL_MM
    assert abs(measured["mesh_axial_depth_mm"] - ref.axial_depth_mm) <= CLOSE_REF_AXIAL_TOL_MM
    assert measured["n_blades"] == ref.n_blades
