"""Counter-rotating (CROR) stacked rotors — geometry (roadmap §4.2).

Two axial rotors on one hub, opposite swirl, fixed axial gap. Export is one fused STL;
dual-MRF evaluate uses the axial extents below for front/rear cellZones.
"""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

import cadquery as cq

from fansim.geometry.blade import BladeParams, RadialStation, build_blade_solid
from fansim.geometry.export import export_stl


def _default_stations(*, stagger: float) -> list[RadialStation]:
    return [
        RadialStation(0.0, 18.0, stagger, thickness=0.10, max_camber=0.04),
        RadialStation(0.5, 18.0, stagger * 0.9, thickness=0.08, max_camber=0.04),
        RadialStation(1.0, 14.0, stagger * 0.8, thickness=0.06, max_camber=0.04),
    ]


@dataclass
class CrorParams:
    """Front + rear axial rotors sharing a hub; rear swirl opposite the front."""

    front: BladeParams = field(default_factory=lambda: BladeParams(
        n_blades=7, stations=_default_stations(stagger=40.0)))
    rear: BladeParams = field(default_factory=lambda: BladeParams(
        n_blades=9, stations=_default_stations(stagger=40.0)))
    axial_gap_mm: float = 8.0  # clear space between front TE band and rear LE band

    def __post_init__(self) -> None:
        # Opposite swirl: mirror rear stagger about the rotation plane.
        for s in self.rear.stations:
            s.stagger_deg = -abs(float(s.stagger_deg))
        for s in self.front.stations:
            s.stagger_deg = abs(float(s.stagger_deg))
        self.rear.hub_radius = float(self.front.hub_radius)
        self.rear.tip_radius = float(self.front.tip_radius)


def _half_depth_mm(params: BladeParams) -> float:
    tip = params.stations[-1]
    return 0.5 * tip.chord * abs(math.sin(math.radians(tip.stagger_deg))) + 2.0


def cror_axial_layout_mm(params: CrorParams | None = None) -> dict[str, float]:
    """Axial layout (mm) matching ``build_cror`` placement — for dual-MRF zones."""
    params = params or CrorParams()
    half_f = _half_depth_mm(params.front)
    half_r = _half_depth_mm(params.rear)
    gap = float(params.axial_gap_mm)
    z_rear = half_f + gap + half_r
    return {
        "half_front_mm": half_f,
        "half_rear_mm": half_r,
        "gap_mm": gap,
        "z_front_mm": 0.0,
        "z_rear_mm": z_rear,
        "front_z_min_mm": -half_f,
        "front_z_max_mm": half_f,
        "rear_z_min_mm": z_rear - half_r,
        "rear_z_max_mm": z_rear + half_r,
        "hub_z0_mm": -half_f - 1.0,
        "hub_z1_mm": z_rear + half_r + 1.0,
    }


def _hub_cylinder(params: BladeParams, z0: float, z1: float) -> cq.Solid:
    h = abs(z1 - z0)
    z_lo = min(z0, z1)
    return (
        cq.Workplane("XY")
        .workplane(offset=z_lo)
        .circle(params.hub_radius)
        .extrude(h)
        .val()
    )


def build_cror(params: CrorParams | None = None) -> cq.Workplane:
    """Fuse front rotor + rear rotor (opposite stagger) + shared hub into one solid."""
    params = params or CrorParams()
    layout = cror_axial_layout_mm(params)
    front = deepcopy(params.front)
    rear = deepcopy(params.rear)
    front_blade = build_blade_solid(front)
    rear_blade = build_blade_solid(rear)
    z_rear = layout["z_rear_mm"]
    front_pat = [
        front_blade.rotate((0, 0, 0), (0, 0, 1), k * 360.0 / front.n_blades)
        for k in range(front.n_blades)
    ]
    rear_pat = [
        rear_blade.rotate((0, 0, 0), (0, 0, 1), k * 360.0 / rear.n_blades)
        .translate((0, 0, z_rear))
        for k in range(rear.n_blades)
    ]
    hub = _hub_cylinder(front, layout["hub_z0_mm"], layout["hub_z1_mm"])
    fused = hub.fuse(*front_pat, *rear_pat).clean()
    solids = fused.Solids()
    if len(solids) != 1:
        raise ValueError(f"CROR fuse produced {len(solids)} solids; expected 1")
    return cq.Workplane(obj=solids[0])


def export_cror_stl(
    params: CrorParams | None = None,
    path: str | Path = "exports/cror.stl",
    *,
    mount=None,
) -> Path:
    """Write one fused CROR STL (aero solid; motor-cup carve is opt-in later)."""
    del mount  # reserved for print-ready path
    params = params or CrorParams()
    return export_stl(build_cror(params), path)
