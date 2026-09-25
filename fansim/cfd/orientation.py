"""CFD orientation of the axial rotor (Audit #1, docs/validation/audits/2026-09-25-audit-01-flow-direction.md).

The A12x25 rotors are designed to turn ω_z = +1 (CCW seen from +Z) and pump −Z *as built*. The ducted
CFD flows +Z (inlet −Z → outlet +Z) with ``spin = −1``. Rotating the rotor 180° about X maps body
ω → −ω and delivery −Z → +Z, so the flipped rotor at ``spin = −1`` IS the designed rotation pumping
down the duct. Only the CFD copy is oriented. The printed/exported STL is unchanged.

The rig's impeller and MRF z-range are fitted to the oriented STL's real bounds. The recipe-based
estimate in ``rig_for_impeller`` under-sizes them (±3 mm vs the Stock STL's −8.1…+8.4 mm), which
left blade ends outside the MRF zone.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import trimesh

from fansim.cfd.domain import MM_TO_M, TestRig

AXIAL_CFD_ORIENTATION = "flipped"
ORIENTATIONS = ("as_built", "flipped")


def flip_about_x(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Proper 180° rotation about X (y → −y, z → −z): same rotor, turned over. Returns a copy."""
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1.0, 0.0, 0.0]))
    return m


def orient_impeller_for_cfd(src_stl_mm: Path, dst_stl_mm: Path,
                            orientation: str = AXIAL_CFD_ORIENTATION) -> tuple[float, float]:
    if orientation not in ORIENTATIONS:
        raise ValueError(f"orientation must be one of {ORIENTATIONS}, got {orientation!r}")
    mesh = trimesh.load(str(src_stl_mm), force="mesh")
    out = flip_about_x(mesh) if orientation == "flipped" else mesh
    Path(dst_stl_mm).parent.mkdir(parents=True, exist_ok=True)
    out.export(str(dst_stl_mm))
    return float(out.bounds[0, 2]), float(out.bounds[1, 2])


def fit_rig_to_stl(rig: TestRig, stl_mm: Path, *, mrf_margin_mm: float = 2.0) -> TestRig:
    mesh = trimesh.load(str(stl_mm), force="mesh")
    z0, z1 = float(mesh.bounds[0, 2]), float(mesh.bounds[1, 2])
    return replace(
        rig,
        impeller_z_min=z0 * MM_TO_M,
        impeller_z_max=z1 * MM_TO_M,
        mrf_z_min=(z0 - mrf_margin_mm) * MM_TO_M,
        mrf_z_max=(z1 + mrf_margin_mm) * MM_TO_M,
    )


def prepare_axial_cfd(stl_mm: Path, rig: TestRig, workdir: Path, *,
                      orientation: str = AXIAL_CFD_ORIENTATION,
                      mrf_margin_mm: float = 2.0) -> tuple[Path, TestRig]:
    """Orient the rotor for CFD and fit the rig to it. Use the returned STL and rig for everything
    downstream (frame, stator, casing export, and ``build_case``)."""
    dst = Path(workdir) / "impeller_cfd.stl"
    orient_impeller_for_cfd(Path(stl_mm), dst, orientation)
    return dst, fit_rig_to_stl(rig, dst, mrf_margin_mm=mrf_margin_mm)
