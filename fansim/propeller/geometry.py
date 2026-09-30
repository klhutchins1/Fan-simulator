"""Propeller geometry from a PropSpec — proper prop twist, built on the shared blade/impeller core.

The key difference from a cooling-fan blade is TWIST FROM PITCH: a prop of geometric pitch P advances
P per revolution (ideal), so the blade angle at radius r is beta(r) = atan(P / (2*pi*r)) — steep near
the hub, shallow at the tip. That, plus few blades (2-3), thin cambered airfoils, and a small shaft-
mount hub, is what makes it a prop. Everything else (loft, watertight export, winglets) is reused.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

import cadquery as cq

from fansim.geometry import build_impeller, export_stl
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.prop_spec import PropSpec


def _pitch_angle_deg(pitch_mm: float, radius_mm: float) -> float:
    """Blade angle at a radius for a geometric pitch (the prop-twist relation)."""
    if radius_mm <= 0:
        return 85.0
    return math.degrees(math.atan(pitch_mm / (2.0 * math.pi * radius_mm)))


def _as_triplet(value, default: tuple[float, float, float]) -> tuple[float, float, float]:
    """Accept a scalar (broadcast) or length-3 sequence."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        v = float(value)
        return (v, v, v)
    seq = list(value)
    if len(seq) != 3:
        raise ValueError(f"expected 3 values, got {len(seq)}")
    return (float(seq[0]), float(seq[1]), float(seq[2]))


def prop_blade_params(
    spec: PropSpec,
    *,
    chord_frac=(0.20, 0.26, 0.10),
    thickness=(0.09, 0.06, 0.04),
    camber: float | Sequence[float] = 0.04,
    camber_pos: float = 0.4,
    sweep_mid: float = 0.0,
    sweep_tip: float = 3.0,
    lean_mid: float = 0.0,
    lean_tip: float = 0.0,
    le_sweep_mid: float = 0.0,
    le_sweep_tip: float = 0.0,
    le_skew_mid: float = 0.0,
    le_skew_tip: float = 0.0,
    cylindrical_tip: bool = True,
) -> BladeParams:
    """Prop-appropriate BladeParams from a spec: pitch-driven twist + Design knobs (§14.1).

    ``chord_frac`` / ``thickness`` / ``camber`` are (root, mid, tip); chord_frac is fraction of
    tip radius. ``camber`` may be a scalar (legacy) or a length-3 sequence.
    """
    R = spec.diameter_mm / 2.0
    hub_r = max(spec.shaft.hub_dia_mm / 2.0, 3.0)
    r_at = {0.0: hub_r, 0.5: 0.5 * (hub_r + R), 1.0: R}
    beta = {rf: _pitch_angle_deg(spec.pitch_mm, r) for rf, r in r_at.items()}
    ch = {0.0: chord_frac[0] * R, 0.5: chord_frac[1] * R, 1.0: chord_frac[2] * R}
    th = _as_triplet(thickness, (0.09, 0.06, 0.04))
    cam = _as_triplet(camber, (0.04, 0.04, 0.04))
    cpos = float(camber_pos)
    stations = [
        RadialStation(
            0.0, ch[0.0], beta[0.0], th[0], cam[0], cpos, 0.0, 0.0, 0.0,
            le_sweep=0.0, le_skew=0.0),
        RadialStation(
            0.5, ch[0.5], beta[0.5], th[1], cam[1], cpos,
            float(sweep_mid), 0.0, float(lean_mid),
            le_sweep=float(le_sweep_mid), le_skew=float(le_skew_mid)),
        RadialStation(
            1.0, ch[1.0], beta[1.0], th[2], cam[2], max(cpos, 0.5),
            float(sweep_tip), 0.0, float(lean_tip),
            le_sweep=float(le_sweep_tip), le_skew=float(le_skew_tip)),
    ]
    return BladeParams(
        n_blades=spec.n_blades, hub_radius=hub_r, tip_radius=R,
        root_embed=1.5, hub_axial_margin=1.0, stations=stations,
        cylindrical_tip=bool(cylindrical_tip),
    )


def build_prop(spec: PropSpec, out_path: str | Path, *, bore: bool = True,
               params: BladeParams | None = None, also_step: bool = True, **kw):
    """Build a printable prop STL for ``spec`` (optional center shaft bore). Returns the WatertightReport.

    When ``also_step`` is True (default), write a sibling ``.step`` B-rep (§20.1).
    """
    from fansim.geometry import watertight_report
    if params is None:
        params = prop_blade_params(spec, **kw)
    model = build_impeller(params)
    if bore and spec.shaft.shaft_dia_mm > 0:
        shape = model.val()
        bb = shape.BoundingBox()
        r = spec.shaft.shaft_dia_mm / 2.0
        cutter = cq.Solid.makeCylinder(r, (bb.zmax - bb.zmin) + 2.0,
                                       cq.Vector(0, 0, bb.zmin - 1.0), cq.Vector(0, 0, 1))
        model = cq.Workplane(obj=shape.cut(cutter))
    out_path = Path(out_path)
    export_stl(model, out_path, tolerance=0.02, angular_tolerance=0.1)
    if also_step:
        from fansim.geometry.export import export_step

        export_step(model, out_path.with_suffix(".step"))
    return watertight_report(out_path)


def build_prop_preview(
    spec: PropSpec,
    out_path: str | Path,
    *,
    params: BladeParams | None = None,
    **kw,
) -> Path:
    """Fast visual prop STL: non-fused impeller preview (no boolean fuse, no shaft bore).

    Cockpit Analyze 3-D uses this (§13.23). Printable Export still calls ``build_prop``
    (fused + bore). Writes ``<out>.meta.json`` with accurate solid volume sum.
    """
    import json

    from fansim.geometry.blade import build_impeller_preview

    if params is None:
        params = prop_blade_params(spec, **kw)
    mesh, volume_mm3 = build_impeller_preview(params)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(out_path))
    Path(str(out_path) + ".meta.json").write_text(
        json.dumps({"volume_mm3": volume_mm3}), encoding="utf-8",
    )
    return out_path
