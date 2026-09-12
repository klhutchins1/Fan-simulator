# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Propeller geometry from a PropSpec — proper prop twist, built on the shared blade/impeller core.

The key difference from a cooling-fan blade is TWIST FROM PITCH: a prop of geometric pitch P advances
P per revolution (ideal), so the blade angle at radius r is beta(r) = atan(P / (2*pi*r)) — steep near
the hub, shallow at the tip. That, plus few blades (2-3), thin cambered airfoils, and a small shaft-
mount hub, is what makes it a prop. Everything else (loft, watertight export, winglets) is reused.
"""

from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq

from fansim.geometry import build_impeller, export_stl
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.prop_spec import PropSpec


def _pitch_angle_deg(pitch_mm: float, radius_mm: float) -> float:
    """Blade angle at a radius for a geometric pitch (the prop-twist relation)."""
    if radius_mm <= 0:
        return 85.0
    return math.degrees(math.atan(pitch_mm / (2.0 * math.pi * radius_mm)))


def prop_blade_params(spec: PropSpec, *, chord_frac=(0.20, 0.26, 0.10), thickness=(0.09, 0.06, 0.04),
                      camber: float = 0.04, sweep_tip: float = 3.0) -> BladeParams:
    """Prop-appropriate BladeParams from a spec: pitch-driven twist, few blades, thin cambered airfoils,
    small shaft-mount hub. chord_frac/thickness are (root, mid, tip); chord_frac is fraction of tip radius."""
    R = spec.diameter_mm / 2.0                     # tip radius
    hub_r = max(spec.shaft.hub_dia_mm / 2.0, 3.0)  # small shaft-mount hub
    r_at = {0.0: hub_r, 0.5: 0.5 * (hub_r + R), 1.0: R}
    beta = {rf: _pitch_angle_deg(spec.pitch_mm, r) for rf, r in r_at.items()}
    ch = {0.0: chord_frac[0] * R, 0.5: chord_frac[1] * R, 1.0: chord_frac[2] * R}
    stations = [
        RadialStation(0.0, ch[0.0], beta[0.0], thickness[0], camber, 0.4, 0.0, 0.0, 0.0),
        RadialStation(0.5, ch[0.5], beta[0.5], thickness[1], camber, 0.4, 0.0, 0.0, 0.0),
        RadialStation(1.0, ch[1.0], beta[1.0], thickness[2], camber, 0.5, sweep_tip, 0.0, 0.0),
    ]
    # small axial hub margin (props have a thin hub, not a deep fan cup)
    return BladeParams(n_blades=spec.n_blades, hub_radius=hub_r, tip_radius=R,
                       root_embed=1.5, hub_axial_margin=1.0, stations=stations)


def build_prop(spec: PropSpec, out_path: str | Path, *, bore: bool = True, **kw):
    """Build a printable prop STL for ``spec`` (optional center shaft bore). Returns the WatertightReport."""
    from fansim.geometry import watertight_report
    params = prop_blade_params(spec, **kw)
    model = build_impeller(params)
    if bore and spec.shaft.shaft_dia_mm > 0:      # center bore for the motor shaft (through the hub)
        shape = model.val()
        bb = shape.BoundingBox()
        r = spec.shaft.shaft_dia_mm / 2.0
        cutter = cq.Solid.makeCylinder(r, (bb.zmax - bb.zmin) + 2.0,
                                       cq.Vector(0, 0, bb.zmin - 1.0), cq.Vector(0, 0, 1))
        model = cq.Workplane(obj=shape.cut(cutter))
    out_path = Path(out_path)
    export_stl(model, out_path, tolerance=0.02, angular_tolerance=0.1)
    return watertight_report(out_path)
