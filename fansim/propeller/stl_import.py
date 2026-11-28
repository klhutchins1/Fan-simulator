"""Import external drone / radial-impeller STLs for open-air prop CFD.

Raw CAD dumps are often laid out off-origin (and CW copies may have inverted
normals). Prep centers the mesh on the spin axis (+Z), forces positive volume,
and writes binary STLs ready for :func:`fansim.propeller.cfd.build_prop_case`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh


@dataclass(frozen=True)
class PropStlMetrics:
    tip_radius_mm: float
    hub_radius_mm: float
    axial_depth_mm: float
    watertight: bool
    volume_mm3: float
    n_faces: int
    diameter_mm: float

    @property
    def tip_radius_m(self) -> float:
        return self.tip_radius_mm / 1000.0


def spin_hint_from_name(name: str) -> int | None:
    """Map CCW/CW in a filename to MRF spin (CCW → -1, CW → +1)."""
    upper = Path(name).stem.upper().replace("-", "_").replace(" ", "_")
    if re.search(r"(^|_)CCW(_|$)", upper):
        return -1
    if re.search(r"(^|_)CW(_|$)", upper):
        return 1
    return None


def prepare_prop_stl(
    src: str | Path,
    dst: str | Path | None = None,
    *,
    fix_normals: bool = True,
    reorient_thin_to_z: bool = True,
) -> Path:
    """Center a millimeter STL on +Z spin, optionally flip inverted normals, write binary.

    When ``dst`` is omitted, writes next to ``src`` as ``<stem>_prepared.stl``.
    """
    src = Path(src)
    if dst is None:
        dst = src.with_name(src.stem + "_prepared.stl")
    else:
        dst = Path(dst)

    mesh = trimesh.load(str(src), force="mesh")
    if reorient_thin_to_z:
        extents = np.asarray(mesh.extents, dtype=float)
        thin = int(np.argmin(extents))
        if thin == 0:
            mesh.apply_transform(
                trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])
            )
        elif thin == 1:
            mesh.apply_transform(
                trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
            )

    # XY center on vertex centroid (better than AABB for off-grid CAD dumps);
    # Z center on bounds mid so the MRF slab sits symmetrically.
    v = np.asarray(mesh.vertices, dtype=float)
    cx, cy = float(v[:, 0].mean()), float(v[:, 1].mean())
    z_mid = 0.5 * (float(mesh.bounds[0, 2]) + float(mesh.bounds[1, 2]))
    mesh.apply_translation([-cx, -cy, -z_mid])

    if fix_normals and float(mesh.volume) < 0.0:
        mesh.invert()

    dst.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(dst))
    return dst


def measure_prop_stl(path: str | Path) -> PropStlMetrics:
    """Tip/hub radii and axial depth for a Z-up, XY-centered prop/impeller STL."""
    mesh = trimesh.load(str(path), force="mesh")
    v = np.asarray(mesh.vertices, dtype=float)
    r = np.sqrt(v[:, 0] ** 2 + v[:, 1] ** 2)
    tip = float(np.percentile(r, 99.5))
    hub = float(np.percentile(r, 5.0))
    return PropStlMetrics(
        tip_radius_mm=tip,
        hub_radius_mm=hub,
        axial_depth_mm=float(mesh.extents[2]),
        watertight=bool(mesh.is_watertight),
        volume_mm3=float(mesh.volume),
        n_faces=len(mesh.faces),
        diameter_mm=2.0 * tip,
    )
