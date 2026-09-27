"""Cylindrical screening-duct wall for honest CFD (CadQuery solid in mm)."""

from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq

from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.cfd.openfoam_case import BOX_SCALE
from fansim.geometry.export import export_stl

CASING_WALL_MM = 2.4  # same as frame barrel; fluid radius stays duct_radius
STEP_DEPTH_MM = 1.2  # radial enlargement of the inlet bore (roadmap 2.6)
STEP_LEN_MM = 6.0  # axial length of the larger bore from domain_z_min (inlet)
FILL_MARGIN_MM = 5.0  # extra radius past the box-corner requirement, for meshing slop


def _sealed_fill_radius_mm(inner_r_mm: float, box_scale: float = BOX_SCALE) -> float:
    """Outer radius (mm) that fully covers a ``box_scale``-half-width hex's corners.

    The background box half-width is ``box_scale * inner_r_mm`` (mm); its far corner sits at
    ``half_width * sqrt(2)``. A casing outer radius below that leaves the corners open, and
    flow can bypass the fan bore around the tube (see ``check_casing_seals``).
    """
    return box_scale * inner_r_mm * math.sqrt(2) + FILL_MARGIN_MM


def build_casing_solid(
    rig: TestRig,
    stepped: bool = False,
    plenum_z_mm: float | None = None,
    fill_radius_mm: float | None = None,
) -> cq.Solid:
    """Full-length tube whose inner radius is the fluid duct radius.

    When ``stepped`` is True the inlet (−Z / ``domain_z_min``) has a short larger bore,
    then a sudden contraction back to ``duct_radius``. Outer radius is constant.

    ``plenum_z_mm`` truncates the outlet end at this z (mm) instead of ``domain_z_max``,
    for use with an outlet-chamber (plenum) domain downstream of the duct. It must lie
    downstream of the impeller.

    When ``plenum_z_mm`` is given, ``fill_radius_mm`` is required: the casing's outer
    radius becomes ``fill_radius_mm`` instead of the thin ``CASING_WALL_MM`` wall, so the
    solid fills the *entire* square box cross-section (pass at least
    ``box_half_width * sqrt(2) + margin`` so the box corners are covered). Without this,
    the open annulus between a thin tube and the outer box would let flow bypass the fan
    bore and go straight from the inlet face to the plenum under back-pressure. The inner
    radius stays ``duct_radius`` — the fan bore is the only path from inlet to plenum.
    """
    inner_r = rig.duct_radius / MM_TO_M
    zmin = rig.domain_z_min / MM_TO_M
    if plenum_z_mm is not None:
        if plenum_z_mm <= rig.impeller_z_max / MM_TO_M:
            raise ValueError(
                "plenum_z_mm must be downstream of the impeller "
                f"(impeller_z_max={rig.impeller_z_max / MM_TO_M:.2f} mm, got {plenum_z_mm:.2f} mm)")
        if fill_radius_mm is None:
            raise ValueError(
                "fill_radius_mm is required when plenum_z_mm is given, so the casing seals "
                "the full box cross-section and flow can't bypass the fan through the annulus")
        zmax = plenum_z_mm
    else:
        zmax = rig.domain_z_max / MM_TO_M
    height = zmax - zmin

    if not stepped:
        # Sealed by default: fill_radius_mm (explicit, e.g. a plenum) wins; otherwise the box
        # corners must be covered (BOX_SCALE * R * sqrt(2) + margin), not just the thin wall.
        outer_r = fill_radius_mm if fill_radius_mm is not None else _sealed_fill_radius_mm(inner_r)
        result = (
            cq.Workplane("XY")
            .workplane(offset=zmin)
            .circle(outer_r)
            .circle(inner_r)
            .extrude(height)
            .val()
        )
    else:
        step_r = inner_r + STEP_DEPTH_MM
        outer_r = fill_radius_mm if fill_radius_mm is not None else _sealed_fill_radius_mm(inner_r)
        z_step = zmin + STEP_LEN_MM
        outline = [
            (step_r, zmin),
            (outer_r, zmin),
            (outer_r, zmax),
            (inner_r, zmax),
            (inner_r, z_step),
            (step_r, z_step),
        ]
        result = (
            cq.Workplane("XZ")
            .polyline(outline)
            .close()
            .revolve(360, (0, 0, 0), (0, 1, 0))
            .val()
        )

    solids = result.Solids() if hasattr(result, "Solids") else [result]
    if len(solids) != 1:
        raise ValueError(f"Casing extrude produced {len(solids)} solids; expected 1")
    return solids[0]


def export_casing_stl(
    rig: TestRig,
    path: str | Path,
    *,
    stepped: bool = False,
    plenum_z_mm: float | None = None,
    fill_radius_mm: float | None = None,
) -> Path:
    """Build the casing tube and write an STL via the shared geometry exporter."""
    return export_stl(
        cq.Workplane(obj=build_casing_solid(
            rig, stepped=stepped, plenum_z_mm=plenum_z_mm, fill_radius_mm=fill_radius_mm)),
        path)
