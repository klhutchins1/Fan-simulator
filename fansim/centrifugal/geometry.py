"""Mixed-flow impeller for the A12x25 through-flow envelope (CadQuery solids in mm).

Conical hub, blades lofted on a diagonal meridional line (eye → tip). Not a volute
squirrel-cage and not the axial ``BladeParams`` cylinder-hub loft.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

from fansim.fan_spec import A12X25, mount_min_hub_radius
from fansim.geometry.blade import _section_points_3d
from fansim.geometry.export import export_stl
from fansim.geometry.features import Features
from fansim.manufacturability.print_export import carve_motor_mount

FRAME_HALF_MM = 55.0
TIP_CLEARANCE_MM = 0.5
ROOT_EMBED_MM = 1.5
ENVELOPE_DEPTH_MM = 25.0


@dataclass
class MixedFlowParams:
    """Diagonal mixed-flow rotor. Defaults fit the measured A12x25 cup + 110 mm frame."""

    n_blades: int = 9
    r_eye_mm: float = 16.0
    r_back_mm: float = 28.0
    r_tip_mm: float = 54.5
    z_span_mm: float = 18.0
    chord_mm: float = 22.0
    stagger_deg: float = 35.0
    thickness: float = 0.08
    max_camber: float = 0.04
    camber_pos: float = 0.4
    n_span: int = 12
    n_chord: int = 48

    def __post_init__(self) -> None:
        if self.r_eye_mm >= self.r_back_mm:
            raise ValueError(
                f"eye radius {self.r_eye_mm:.1f} mm must be < back hub {self.r_back_mm:.1f} mm")
        need = mount_min_hub_radius(A12X25)
        if need is not None and self.r_back_mm < need:
            raise ValueError(
                f"back hub {self.r_back_mm:.1f} mm below A12x25 mount minimum {need:.1f} mm")


def _hub_z_range(params: MixedFlowParams) -> tuple[float, float]:
    half = 0.5 * params.z_span_mm
    return -half, half


def _section_hang_mm(params: MixedFlowParams) -> float:
    """Half axial extent of one staggered section beyond its mid-chord."""
    beta = math.radians(params.stagger_deg)
    return 0.5 * params.chord_mm * abs(math.sin(beta)) + params.thickness * params.chord_mm


def _loft_z_range(params: MixedFlowParams) -> tuple[float, float]:
    """Mid-chord z at root/tip, inset so stagger overhang stays inside the 25 mm frame."""
    z_min, z_max = _hub_z_range(params)
    hang = _section_hang_mm(params)
    budget = 0.5 * ENVELOPE_DEPTH_MM
    z_root = min(z_max, budget - hang)
    z_tip = max(z_min, -budget + hang)
    if z_root <= z_tip:
        z_root, z_tip = 0.25 * params.z_span_mm, -0.25 * params.z_span_mm
    return z_root, z_tip


def _loft_tip_radius_mm(params: MixedFlowParams) -> float:
    """Section radius at the tip so the built hypot clears the 110 mm frame by 0.5 mm."""
    beta = math.radians(params.stagger_deg)
    t_max = 0.5 * params.chord_mm * abs(math.cos(beta)) + params.thickness * params.chord_mm
    cap = FRAME_HALF_MM - TIP_CLEARANCE_MM
    inner = cap * cap - t_max * t_max
    if inner <= 0:
        return min(params.r_tip_mm, 0.5 * cap)
    return min(params.r_tip_mm, math.sqrt(inner))


def _hub_solid(params: MixedFlowParams) -> cq.Solid:
    z_min, z_max = _hub_z_range(params)
    eps = 0.05
    outline = [
        (eps, z_min),
        (params.r_back_mm, z_min),
        (params.r_eye_mm, z_max),
        (eps, z_max),
    ]
    wp = cq.Workplane("XZ").polyline(outline).close().revolve(360, (0, 0, 0), (0, 1, 0))
    hub = wp.val()
    # Revolve leaves a pinhole on the axis; fill it so the hub is a true solid (cup carve later).
    core = cq.Solid.makeCylinder(1.0, z_max - z_min, cq.Vector(0, 0, z_min), cq.Vector(0, 0, 1))
    filled = hub.fuse(core).clean()
    solids = filled.Solids()
    return solids[0] if solids else filled


def _blade_solid(params: MixedFlowParams) -> cq.Solid:
    z_root, z_tip = _loft_z_range(params)
    r_root = params.r_eye_mm - ROOT_EMBED_MM
    r_tip = _loft_tip_radius_mm(params)
    n_span = max(3, int(params.n_span))
    wires: list[cq.Wire] = []
    blank = Features()
    for i in range(n_span):
        rf = i / (n_span - 1)
        r = r_root + rf * (r_tip - r_root)
        z = z_root + rf * (z_tip - z_root)
        pts = _section_points_3d(
            r=r,
            r_frac=rf,
            chord=params.chord_mm,
            stagger_deg=params.stagger_deg,
            thickness=params.thickness,
            max_camber=params.max_camber,
            camber_pos=params.camber_pos,
            sweep=z,
            skew=0.0,
            le_sweep=0.0,
            lean_deg=0.0,
            n_chord=params.n_chord,
            features=blank,
        )
        wires.append(cq.Wire.makePolygon(pts, close=True))
    return cq.Solid.makeLoft(wires, True)


def build_mixed_flow(params: MixedFlowParams | None = None) -> cq.Workplane:
    """One fused mixed-flow impeller (conical hub + patterned diagonal blades)."""
    params = params or MixedFlowParams()
    hub = _hub_solid(params)
    blade = _blade_solid(params)
    blades = [
        blade.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), k * 360.0 / params.n_blades)
        for k in range(params.n_blades)
    ]
    fused = hub.fuse(*blades).clean()
    solids = fused.Solids()
    if len(solids) != 1:
        raise ValueError(f"Mixed-flow fuse produced {len(solids)} solids; expected 1")
    return cq.Workplane(obj=solids[0])


def export_mixed_flow_stl(
    params: MixedFlowParams,
    path: str | Path,
    *,
    mount=None,
) -> Path:
    """Build, carve the A12x25 motor cup when it fits, and write an STL."""
    if mount is None:
        mount = A12X25.motor_mount
    model = build_mixed_flow(params)
    if mount is not None:
        model, _fits, _msg = carve_motor_mount(model, mount, params.r_back_mm)
    return export_stl(model, path)
