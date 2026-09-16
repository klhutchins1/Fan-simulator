"""Stationary outlet-guide vanes for honest CFD (CadQuery solids in mm).

Cambered NACA 4-digit OGVs plus a hub barrel, sitting in the same axial band as the four-bar
frame. When ``--stator`` is on they *replace* the frame so the two do not occupy one slice.
Positive camber turns toward axial (suction side +Y before stagger); stagger sign matches the
old flat-plate row. Stagger and vane offset are optional kwargs (NSGA searches them under
``--stator``); defaults stay 50° and ``n_blades + 2``.
"""

from __future__ import annotations

from pathlib import Path

import cadquery as cq

from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.cfd.frame import (
    BARREL_WALL_MM,
    STRUT_AFTER_MRF_MM,
    STRUT_DEPTH_MM,
    STRUT_WALL_INSET_MM,
)
from fansim.geometry.airfoil import naca4
from fansim.geometry.blade import BladeParams
from fansim.geometry.export import export_stl

AFTER_MRF_MM = STRUT_AFTER_MRF_MM
WALL_INSET_MM = STRUT_WALL_INSET_MM
CHORD_MM = STRUT_DEPTH_MM
STAGGER_DEG = 50.0
STATOR_N_EXTRA_DEFAULT = 2
STATOR_CAMBER = 0.04
STATOR_CAMBER_POS = 0.4
STATOR_THICKNESS = 0.12
_N_CHORD_PTS = 40


def n_stator_vanes(params: BladeParams, n_extra: int | None = None) -> int:
    """Rotor count plus an offset so stator BPF is not coincident (default +2)."""
    extra = STATOR_N_EXTRA_DEFAULT if n_extra is None else int(n_extra)
    return int(params.n_blades) + extra


def stationary_downstream(*, stator: bool = False, stator_stack: bool = False) -> str:
    """Which stationary STL(s) ``evaluate_candidate`` puts behind the rotor."""
    if stator and stator_stack:
        raise ValueError("cannot combine stator replace and stator_stack")
    if stator_stack:
        return "stack"
    return "stator" if stator else "frame"


def _vane_yz_profile(z_start: float) -> list[tuple[float, float]]:
    """Closed NACA loop in the YZ plane: chord along +Z from ``z_start``, thickness along Y."""
    loop = naca4(STATOR_CAMBER, STATOR_CAMBER_POS, STATOR_THICKNESS, n_points=_N_CHORD_PTS)
    scaled = loop * CHORD_MM
    # (y, z) for Workplane("YZ"); drop duplicate close point for polyline+close
    pts = [(float(p[1]), float(z_start + p[0])) for p in scaled[:-1]]
    return pts


def build_stator_solid(
    params: BladeParams,
    rig: TestRig,
    *,
    stagger_deg: float | None = None,
    n_vanes: int | None = None,
    n_extra: int | None = None,
) -> cq.Solid:
    """N cambered NACA vanes fused with a hub barrel, just downstream of the MRF zone."""
    stagger = float(STAGGER_DEG if stagger_deg is None else stagger_deg)
    z_start = rig.mrf_z_max / MM_TO_M + AFTER_MRF_MM
    outer_r = rig.duct_radius / MM_TO_M - WALL_INSET_MM
    hub_r = params.hub_radius
    bar_r0 = hub_r - BARREL_WALL_MM
    span = outer_r - bar_r0
    z_center = z_start + CHORD_MM / 2.0
    if n_vanes is not None:
        n = int(n_vanes)
    else:
        n = n_stator_vanes(params, n_extra=n_extra)
    yz = _vane_yz_profile(z_start)

    # Extrude radially (+X) from hub barrel OD to duct ID − inset, then stagger about radial axis.
    vane0 = (
        cq.Workplane("YZ")
        .workplane(offset=bar_r0)
        .polyline(yz)
        .close()
        .extrude(span)
        .rotate((0, 0, z_center), (1, 0, z_center), stagger)
    )

    hub_barrel = (
        cq.Workplane("XY")
        .workplane(offset=z_start)
        .circle(hub_r)
        .circle(hub_r - BARREL_WALL_MM)
        .extrude(CHORD_MM)
        .val()
    )

    solids: list[cq.Solid] = []
    for i in range(n):
        ang = 360.0 * i / n
        if ang == 0:
            solids.append(vane0.val())
        else:
            solids.append(vane0.rotate((0, 0, 0), (0, 0, 1), ang).val())

    result = solids[0].fuse(*solids[1:], hub_barrel).clean()
    result_solids = result.Solids()
    if len(result_solids) != 1:
        raise ValueError(f"Stator fuse produced {len(result_solids)} solids; expected 1")
    return result_solids[0]


def export_stator_stl(
    params: BladeParams,
    rig: TestRig,
    path: str | Path,
    *,
    stagger_deg: float | None = None,
    n_vanes: int | None = None,
    n_extra: int | None = None,
) -> Path:
    solid = build_stator_solid(
        params, rig, stagger_deg=stagger_deg, n_vanes=n_vanes, n_extra=n_extra)
    return export_stl(cq.Workplane(obj=solid), path)
