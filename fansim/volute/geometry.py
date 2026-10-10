"""Radial (90°) impeller + sealed volute casing (roadmap §4.1).

Axial inlet, radial discharge into an Archimedean-scroll collector.
Casing is a filled exterior enclosure (no hex-box bypass) with a discrete
tongue cutwater. Scroll channel is a dense Archimedean polyline extrusion
(stage 3). CFD lives in ``fansim.volute.evaluate``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

from fansim.geometry.export import export_stl

# Honesty stamp for stage-3 smooth scroll (sealed fill + dense Archimedean wall).
VOLUTE_HONESTY = "stage3_smooth_scroll"


@dataclass
class VoluteParams:
    """Radial blower params (mm). Not an A12x25 through-flow drop-in."""

    n_blades: int = 7
    r_hub_mm: float = 18.0
    r_tip_mm: float = 50.0
    blade_height_mm: float = 20.0
    blade_thick_mm: float = 1.2
    backplate_thick_mm: float = 2.0
    volute_clearance_mm: float = 3.0
    volute_wall_mm: float = 2.0
    spiral_growth_mm: float = 25.0  # outer-radius growth over 360° past tongue
    n_volute_seg: int = 96  # Archimedean polyline sample count
    outlet_width_mm: float = 32.0
    outlet_length_mm: float = 40.0
    outlet_height_mm: float = 24.0
    tongue_angle_deg: float = 5.0  # angular thickness of cutwater septum
    tongue_tip_clearance_mm: float = 1.0  # tip sits this far outside r_in
    tongue_fillet_mm: float = 1.5  # cylindrical tip radius on cutwater

    def __post_init__(self) -> None:
        if self.n_blades < 3:
            raise ValueError(f"n_blades {self.n_blades} must be >= 3")
        if self.r_hub_mm <= 0 or self.r_tip_mm <= self.r_hub_mm:
            raise ValueError(
                f"hub {self.r_hub_mm:.1f} mm must be < tip {self.r_tip_mm:.1f} mm")
        if self.blade_height_mm <= 0 or self.blade_thick_mm <= 0:
            raise ValueError("blade height and thickness must be > 0")
        if self.volute_clearance_mm < 0.5:
            raise ValueError("volute clearance must be >= 0.5 mm")
        if self.n_volute_seg < 8:
            raise ValueError("n_volute_seg must be >= 8")
        if self.tongue_angle_deg < 1.0 or self.tongue_angle_deg > 20.0:
            raise ValueError("tongue_angle_deg must be in [1, 20]")
        if self.tongue_tip_clearance_mm < 0.3:
            raise ValueError("tongue_tip_clearance_mm must be >= 0.3 mm")
        if self.tongue_fillet_mm < 0.0 or self.tongue_fillet_mm > 8.0:
            raise ValueError("tongue_fillet_mm must be in [0, 8]")


def _impeller_z_range(params: VoluteParams) -> tuple[float, float]:
    """Backplate on −Z, blades toward +Z (axial inlet from +Z)."""
    z0 = 0.0
    z1 = params.backplate_thick_mm + params.blade_height_mm
    return z0, z1


def build_radial_impeller(params: VoluteParams | None = None) -> cq.Workplane:
    """Backplate + hub barrel + radial flat blades → one solid."""
    params = params or VoluteParams()
    z0, z1 = _impeller_z_range(params)
    bp = (
        cq.Workplane("XY")
        .circle(params.r_tip_mm)
        .extrude(params.backplate_thick_mm)
        .val()
    )
    hub = (
        cq.Workplane("XY")
        .circle(params.r_hub_mm)
        .extrude(z1)
        .val()
    )
    # Slight overlaps into hub/backplate so tessellated STL stays manifold.
    overlap = 0.25
    span = (params.r_tip_mm - params.r_hub_mm) + overlap
    r_mid = 0.5 * ((params.r_hub_mm - overlap) + params.r_tip_mm)
    blade0 = (
        cq.Workplane("XY")
        .workplane(offset=params.backplate_thick_mm - overlap)
        .center(r_mid, 0.0)
        .rect(span, params.blade_thick_mm)
        .extrude(params.blade_height_mm + overlap)
        .val()
    )
    blades = [
        blade0.rotate((0, 0, 0), (0, 0, 1), k * 360.0 / params.n_blades)
        for k in range(params.n_blades)
    ]
    from fansim.geometry.blade import fuse_many

    fused = fuse_many(bp, (hub, *blades))  # memory-tiered (fansim.resources)
    solids = fused.Solids()
    if len(solids) != 1:
        raise ValueError(f"radial impeller fuse produced {len(solids)} solids; expected 1")
    return cq.Workplane(obj=solids[0])


def volute_radii_mm(params: VoluteParams) -> dict[str, float]:
    """Inner (tip clearance) and outer scroll radii at tongue (θ=0) and exit (θ=2π)."""
    r_in = params.r_tip_mm + params.volute_clearance_mm
    r_out0 = r_in + 8.0  # tongue channel depth
    r_out1 = r_out0 + params.spiral_growth_mm
    return {
        "r_in_mm": r_in,
        "r_out_tongue_mm": r_out0,
        "r_out_exit_mm": r_out1,
        "z0_mm": 0.0,
        "z1_mm": params.backplate_thick_mm + params.blade_height_mm,
    }


def scroll_outer_radius_mm(params: VoluteParams, theta_rad: float) -> float:
    """Archimedean outer-wall radius at angle θ (rad), θ=0 at tongue / +X."""
    rad = volute_radii_mm(params)
    twopi = 2.0 * math.pi
    t = (theta_rad % twopi) / twopi
    r0 = rad["r_out_tongue_mm"]
    r1 = rad["r_out_exit_mm"]
    return r0 + (r1 - r0) * t


def volute_enclosure_extents_mm(
    params: VoluteParams,
    *,
    margin_mm: float = 8.0,
    inlet_plenum_mm: float = 28.0,
    outlet_clearance_mm: float = 12.0,
) -> dict[str, float]:
    """Axis-aligned mm box for the sealed casing fill and matching CFD domain.

    Casing solid fills ``zmin..zmax_casing`` (sealed floor + scroll). Inlet plenum
    fluid lives in ``zmax_casing..zmax_domain`` so the +Z inlet still feeds the eye.
    """
    rad = volute_radii_mm(params)
    r_shell = rad["r_out_exit_mm"] + params.volute_wall_mm
    stub_x_end = rad["r_out_tongue_mm"] + params.outlet_length_mm
    half_y_stub = 0.5 * params.outlet_width_mm
    y_ext = max(r_shell, half_y_stub) + margin_mm
    z_casing_top = rad["z1_mm"] + params.volute_wall_mm
    return {
        "xmin": -(r_shell + margin_mm),
        "xmax": max(r_shell, stub_x_end) + outlet_clearance_mm,
        "ymin": -y_ext,
        "ymax": y_ext,
        "zmin": rad["z0_mm"] - params.volute_wall_mm - margin_mm,
        "zmax_casing": z_casing_top,
        "zmax_domain": z_casing_top + inlet_plenum_mm,
        "r_shell_mm": r_shell,
        "stub_x_end_mm": stub_x_end,
    }


def _annular_sector(
    r_in: float,
    r_out: float,
    z0: float,
    z1: float,
    a0_deg: float,
    a1_deg: float,
) -> cq.Solid:
    """Solid annular wedge between two radii over [a0, a1] degrees."""
    h = z1 - z0
    outer = (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .moveTo(0, 0)
        .circle(r_out)
        .extrude(h)
        .val()
    )
    inner = (
        cq.Workplane("XY")
        .workplane(offset=z0 - 0.05)
        .circle(r_in)
        .extrude(h + 0.1)
        .val()
    )
    ring = outer.cut(inner)
    span = (a1_deg - a0_deg) % 360.0
    if span <= 0:
        span = 360.0
    n = max(4, int(span / 15.0) + 2)
    pts = [(0.0, 0.0)]
    for i in range(n + 1):
        a = math.radians(a0_deg + span * i / n)
        pts.append((r_out * 2.5 * math.cos(a), r_out * 2.5 * math.sin(a)))
    pie = (
        cq.Workplane("XY")
        .workplane(offset=z0 - 0.1)
        .polyline(pts)
        .close()
        .extrude(h + 0.2)
        .val()
    )
    return ring.intersect(pie)


def _archimedean_scroll_void(
    r_in: float,
    r_out0: float,
    r_out1: float,
    z0: float,
    z1: float,
    n_seg: int,
) -> cq.Solid:
    """Single extruded channel: inner circle + Archimedean outer wall.

    Outer radius grows linearly with θ from ``r_out0`` (tongue, θ=0) to
    ``r_out1`` (exit, θ=2π). The polygon closes on the +X radial cut at the
    tongue so the outlet stub can punch through.
    """
    if r_out0 <= r_in + 0.5:
        raise ValueError("scroll outer radius must clear inner bore")
    n = max(int(n_seg), 8)
    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        t = i / n
        th = 2.0 * math.pi * t
        r = r_out0 + (r_out1 - r_out0) * t
        pts.append((r * math.cos(th), r * math.sin(th)))
    # Inner wall reverse from θ=2π → 0 (skip duplicate at θ=2π).
    for i in range(1, n + 1):
        t = i / n
        th = 2.0 * math.pi * (1.0 - t)
        pts.append((r_in * math.cos(th), r_in * math.sin(th)))
    h = z1 - z0
    return (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .polyline(pts)
        .close()
        .extrude(h)
        .val()
    )


def _tongue_cutwater(
    params: VoluteParams,
    *,
    r_in: float,
    r0: float,
    z0: float,
    z1: float,
) -> cq.Solid:
    """Angular septum plus optional cylindrical tip fillet at the cutwater."""
    r_tip = r_in + params.tongue_tip_clearance_mm
    if r_tip >= r0 - 0.5:
        r_tip = max(r_in + 0.3, r0 - 1.0)
    half_a = 0.5 * params.tongue_angle_deg
    tongue = _annular_sector(r_tip, r0, z0, z1, -half_a, half_a)
    fillet = float(params.tongue_fillet_mm)
    if fillet <= 0.0:
        return tongue
    # Keep the rounded nose outside the eye: cylinder sits in the septum body,
    # tangent to r=r_tip from the outside.
    max_fillet = max(0.0, 0.5 * (r0 - r_tip) - 0.2)
    fillet = min(fillet, max_fillet)
    if fillet <= 0.0:
        return tongue
    cx = r_tip + fillet
    tip = (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .center(cx, 0.0)
        .circle(fillet)
        .extrude(z1 - z0)
        .val()
    )
    return tongue.fuse(tip).clean()


def build_volute_casing(params: VoluteParams | None = None) -> cq.Workplane:
    """Sealed exterior fill + scroll voids + tongue cutwater → one solid.

    Fills the CFD box around the scroll (including under-floor) so snappy cannot
    leave an exterior leak path. Dense Archimedean scroll + filleted tongue at θ≈0.
    """
    params = params or VoluteParams()
    rad = volute_radii_mm(params)
    ext = volute_enclosure_extents_mm(params)
    z0, z1 = rad["z0_mm"], rad["z1_mm"]
    r_in = rad["r_in_mm"]
    r0 = rad["r_out_tongue_mm"]
    r1 = rad["r_out_exit_mm"]

    # Oversize slightly past domain walls so castellated cells at the boundary
    # still land inside the solid (no razor-thin exterior fluid film).
    pad = 1.5
    xmin, xmax = ext["xmin"] - pad, ext["xmax"] + pad
    ymin, ymax = ext["ymin"] - pad, ext["ymax"] + pad
    zmin, zmax_c = ext["zmin"] - pad, ext["zmax_casing"]
    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    dx, dy, dz = xmax - xmin, ymax - ymin, zmax_c - zmin

    outer = (
        cq.Workplane("XY")
        .workplane(offset=zmin)
        .center(cx, cy)
        .box(dx, dy, dz, centered=(True, True, False))
        .val()
    )

    # Eye open from impeller floor to casing top (plenum above feeds +Z inlet).
    # Solid floor zmin..z0 seals under-casing bypass.
    eye = (
        cq.Workplane("XY")
        .workplane(offset=z0 - 0.05)
        .circle(r_in)
        .extrude(zmax_c - z0 + 0.1)
        .val()
    )

    scroll_void = _archimedean_scroll_void(
        r_in, r0, r1, z0, z1, params.n_volute_seg)

    stub_h = max(params.outlet_height_mm - 2.0 * params.volute_wall_mm, 1.0)
    stub_w = max(params.outlet_width_mm - 2.0 * params.volute_wall_mm, 1.0)
    stub_x0 = r0
    # Punch through +X so the void meets the domain outlet face.
    stub_len = (xmax - stub_x0) + 1.0
    z_mid = 0.5 * (z0 + z1)
    stub_void = (
        cq.Workplane("XY")
        .workplane(offset=z_mid - 0.5 * stub_h)
        .center(stub_x0 + 0.5 * stub_len, 0.0)
        .box(stub_len, stub_w, stub_h)
        .val()
    )

    body = outer.cut(eye).cut(scroll_void).cut(stub_void)
    tongue = _tongue_cutwater(params, r_in=r_in, r0=r0, z0=z0, z1=z1)
    fused = body.fuse(tongue).clean()
    solids = fused.Solids()
    if len(solids) != 1:
        solids = sorted(solids, key=lambda s: s.Volume(), reverse=True)
        if len(solids) > 1:
            fused = solids[0].fuse(*solids[1:]).clean()
            solids = fused.Solids()
        if len(solids) != 1:
            raise ValueError(f"volute casing fuse produced {len(solids)} solids; expected 1")
    return cq.Workplane(obj=solids[0])


def build_volute_assembly(params: VoluteParams | None = None) -> cq.Workplane:
    """Impeller + casing compound for preview (two bodies OK)."""
    params = params or VoluteParams()
    imp = build_radial_impeller(params).val()
    cas = build_volute_casing(params).val()
    # Compound without forcing a single solid — clearance keeps them non-intersecting.
    compound = cq.Compound.makeCompound([imp, cas])
    return cq.Workplane(obj=compound)


def export_volute_stls(
    params: VoluteParams | None = None,
    out_dir: str | Path = "exports/volute",
) -> tuple[Path, Path]:
    """Write ``impeller.stl`` and ``casing.stl`` under ``out_dir``."""
    params = params or VoluteParams()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    imp_path = export_stl(build_radial_impeller(params), out_dir / "impeller.stl")
    cas_path = export_stl(build_volute_casing(params), out_dir / "casing.stl")
    return Path(imp_path), Path(cas_path)


def export_volute_preview_stl(
    params: VoluteParams | None = None,
    path: str | Path = "exports/volute_preview.stl",
) -> Path:
    """Write a multi-body preview STL (impeller + casing)."""
    params = params or VoluteParams()
    return export_stl(build_volute_assembly(params), path)


def export_volute_impeller_stl(
    params: VoluteParams | None = None,
    path: str | Path = "exports/volute_impeller.stl",
) -> Path:
    """Write impeller-only STL (archetype ``build_geometry``)."""
    params = params or VoluteParams()
    return export_stl(build_radial_impeller(params), path)
