"""Trusted A12x25 reference STL: reorient, silhouette metrics, CFD domain sizing.

The source mesh in Downloads had spin along Y; OpenFOAM MRF in this repo expects Z.
Prepared assets live at ``validation/reference/a12x25_impeller.stl`` (Z-up, centered).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage
from scipy.signal import find_peaks

from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.geometry.blade import BladeParams

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_STL = ROOT / "validation" / "reference" / "a12x25_impeller.stl"


@dataclass(frozen=True)
class SilhouetteMetrics:
    tip_radius_mm: float
    hub_radius_mm: float
    n_blades: int
    axial_depth_mm: float
    watertight: bool
    n_faces: int
    volume_mm3: float


def prepare_reference_stl(
    src: str | Path,
    dst: str | Path = DEFAULT_REFERENCE_STL,
) -> Path:
    """Load a raw mesh, put spin/flow on +Z, center bounds, write binary STL."""
    src, dst = Path(src), Path(dst)
    mesh = trimesh.load(str(src), force="mesh")
    extents = np.asarray(mesh.extents, dtype=float)
    thin = int(np.argmin(extents))
    # Rotate thin axis onto +Z (identity if already Z-thin).
    if thin == 0:
        R = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])
        mesh.apply_transform(R)
    elif thin == 1:
        R = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
        mesh.apply_transform(R)
    mesh.apply_translation(-mesh.bounds.mean(axis=0))
    dst.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(dst))
    return dst


def _estimate_blade_count(vertices: np.ndarray, tip_r: float) -> int:
    r = np.sqrt(vertices[:, 0] ** 2 + vertices[:, 1] ** 2)
    mask = (r > 0.55 * tip_r) & (r < 0.75 * tip_r)
    if int(np.count_nonzero(mask)) < 50:
        return 0
    ang = np.arctan2(vertices[mask, 1], vertices[mask, 0])
    hist, _ = np.histogram(ang, bins=360, range=(-np.pi, np.pi))
    sm = ndimage.gaussian_filter1d(hist.astype(float), 2.0)
    peaks, _ = find_peaks(sm, distance=20, height=float(sm.mean()))
    return int(len(peaks))


def measure_silhouette(path: str | Path = DEFAULT_REFERENCE_STL) -> SilhouetteMetrics:
    """Tip/hub radii, blade count, and axial depth for a Z-up centered impeller STL."""
    mesh = trimesh.load(str(path), force="mesh")
    v = np.asarray(mesh.vertices, dtype=float)
    r = np.sqrt(v[:, 0] ** 2 + v[:, 1] ** 2)
    tip = float(np.percentile(r, 99.5))
    hub = float(np.percentile(r, 5.0))
    return SilhouetteMetrics(
        tip_radius_mm=tip,
        hub_radius_mm=hub,
        n_blades=_estimate_blade_count(v, tip),
        axial_depth_mm=float(mesh.extents[2]),
        watertight=bool(mesh.is_watertight),
        n_faces=int(len(mesh.faces)),
        volume_mm3=float(mesh.volume),
    )


def rig_for_reference_stl(
    stl_path: str | Path,
    *,
    rpm: float,
    tip_gap_mm: float = 0.5,
    inlet_diameters: float = 2.0,
    outlet_diameters: float = 4.0,
    mrf_margin_mm: float = 2.0,
    inlet_velocity: float = 2.0,
    params: BladeParams | None = None,
) -> TestRig:
    """Size the duct / MRF from the actual STL tip radius and Z bounds.

    ``params`` is optional; when given, ``rpm`` defaults can still be overridden by
    the explicit ``rpm`` argument (validation always passes the recipe RPM).
    """
    del params  # reserved for future spin/handedness from recipe
    mesh = trimesh.load(str(stl_path), force="mesh")
    v = np.asarray(mesh.vertices, dtype=float)
    tip_mm = float(np.percentile(np.sqrt(v[:, 0] ** 2 + v[:, 1] ** 2), 99.5))
    tip_gap_m = tip_gap_mm * MM_TO_M
    duct_r = tip_mm * MM_TO_M + tip_gap_m
    z_lo = float(mesh.bounds[0, 2]) * MM_TO_M
    z_hi = float(mesh.bounds[1, 2]) * MM_TO_M
    diameter = 2.0 * duct_r
    return TestRig(
        duct_radius=duct_r,
        tip_gap=tip_gap_m,
        inlet_length=inlet_diameters * diameter,
        outlet_length=outlet_diameters * diameter,
        impeller_z_min=z_lo,
        impeller_z_max=z_hi,
        mrf_z_min=z_lo - mrf_margin_mm * MM_TO_M,
        mrf_z_max=z_hi + mrf_margin_mm * MM_TO_M,
        rpm=float(rpm),
        inlet_velocity=inlet_velocity,
    )
