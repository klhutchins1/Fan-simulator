"""Stationary exhaust-frame geometry for honest CFD (CadQuery solids in mm)."""

from __future__ import annotations

from pathlib import Path

import cadquery as cq

from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.geometry.blade import BladeParams
from fansim.geometry.export import export_stl

STRUT_THICK_MM = 2.4
STRUT_DEPTH_MM = 8.0
STRUT_WALL_INSET_MM = 0.1
STRUT_AFTER_MRF_MM = 0.5
BARREL_WALL_MM = 2.4
# Gap between stator TE and frame LE when ``--stator-stack`` (stator first, then frame).
STACK_GAP_MM = 2.0


def default_frame_z_start_mm(rig: TestRig) -> float:
    """Axial LE of the four-bar frame (mm): just downstream of the MRF zone (+Z outlet)."""
    return rig.mrf_z_max / MM_TO_M + STRUT_AFTER_MRF_MM


def stack_frame_z_start_mm(rig: TestRig) -> float:
    """Frame LE when stacked behind an 8 mm stator row + ``STACK_GAP_MM``."""
    return default_frame_z_start_mm(rig) + STRUT_DEPTH_MM + STACK_GAP_MM


def build_frame_solid(
    params: BladeParams,
    rig: TestRig,
    *,
    z_start_mm: float | None = None,
) -> cq.Solid:
    """Four radial struts fused into one solid.

    ``z_start_mm`` defaults to just downstream of the MRF (replace / frame-only mode).
    Pass ``stack_frame_z_start_mm(rig)`` for a stator-then-frame stack.
    """
    z_start = float(default_frame_z_start_mm(rig) if z_start_mm is None else z_start_mm)
    outer_r = rig.duct_radius / MM_TO_M - STRUT_WALL_INSET_MM
    hub_r = params.hub_radius

    bar_r0 = hub_r - BARREL_WALL_MM
    bar_len = outer_r - bar_r0
    x_center = (bar_r0 + outer_r) / 2.0
    z_center = z_start + STRUT_DEPTH_MM / 2.0

    base = (
        cq.Workplane("XY")
        .box(bar_len, STRUT_THICK_MM, STRUT_DEPTH_MM)
        .translate((x_center, 0, z_center))
    )

    # This short annulus ("hub barrel") is the join that ensures a true one-body solid.
    # It lives in the hub shadow (r < hub_r) and overlaps the inner end of each bar.
    hub_barrel = (
        cq.Workplane("XY")
        .workplane(offset=z_start)
        .circle(hub_r)
        .circle(hub_r - BARREL_WALL_MM)
        .extrude(STRUT_DEPTH_MM)
        .val()
    )

    solids: list[cq.Solid] = []
    for ang in (0, 90, 180, 270):
        if ang == 0:
            solids.append(base.val())
        else:
            solids.append(base.rotate((0, 0, 0), (0, 0, 1), ang).val())

    result = solids[0].fuse(*solids[1:], hub_barrel).clean()
    result_solids = result.Solids()
    if len(result_solids) != 1:
        raise ValueError(f"Frame fuse produced {len(result_solids)} solids; expected 1")

    # `fuse()` can return a Compound even when there's only one Solid; unwrap to a real cq.Solid.
    return result_solids[0]


def export_frame_stl(
    params: BladeParams,
    rig: TestRig,
    path: str | Path,
    *,
    z_start_mm: float | None = None,
) -> Path:
    """Build the frame solid and write an STL via the shared geometry exporter."""
    solid = build_frame_solid(params, rig, z_start_mm=z_start_mm)
    return export_stl(cq.Workplane(obj=solid), path)
