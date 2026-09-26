"""Cylindrical screening-duct wall for honest CFD (CadQuery solid in mm)."""

from __future__ import annotations

from pathlib import Path

import cadquery as cq

from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.geometry.export import export_stl

CASING_WALL_MM = 2.4  # same as frame barrel; fluid radius stays duct_radius
STEP_DEPTH_MM = 1.2  # radial enlargement of the inlet bore (roadmap 2.6)
STEP_LEN_MM = 6.0  # axial length of the larger bore from domain_z_min (inlet)


def build_casing_solid(rig: TestRig, stepped: bool = False, plenum_z_mm: float | None = None) -> cq.Solid:
    """Full-length tube whose inner radius is the fluid duct radius.

    When ``stepped`` is True the inlet (−Z / ``domain_z_min``) has a short larger bore,
    then a sudden contraction back to ``duct_radius``. Outer radius is constant.

    ``plenum_z_mm`` truncates the outlet end at this z (mm) instead of ``domain_z_max``,
    for use with an outlet-chamber (plenum) domain downstream of the duct. It must lie
    downstream of the impeller.
    """
    inner_r = rig.duct_radius / MM_TO_M
    zmin = rig.domain_z_min / MM_TO_M
    if plenum_z_mm is not None:
        if plenum_z_mm <= rig.impeller_z_max / MM_TO_M:
            raise ValueError(
                "plenum_z_mm must be downstream of the impeller "
                f"(impeller_z_max={rig.impeller_z_max / MM_TO_M:.2f} mm, got {plenum_z_mm:.2f} mm)")
        zmax = plenum_z_mm
    else:
        zmax = rig.domain_z_max / MM_TO_M
    height = zmax - zmin

    if not stepped:
        outer_r = inner_r + CASING_WALL_MM
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
        outer_r = inner_r + CASING_WALL_MM + STEP_DEPTH_MM
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
    rig: TestRig, path: str | Path, *, stepped: bool = False, plenum_z_mm: float | None = None,
) -> Path:
    """Build the casing tube and write an STL via the shared geometry exporter."""
    return export_stl(
        cq.Workplane(obj=build_casing_solid(rig, stepped=stepped, plenum_z_mm=plenum_z_mm)), path)
