"""Turn an optimized impeller into a print-ready deliverable: a fine-tessellation STL with an
optional parameterized motor-shaft bore, a per-material print-settings sheet, and a rotor-balance
report. Bridges the simulation to the physical showdown (plan Phase 5).

HONEST CAVEAT ON THE BORE: simple ``BoreSpec`` diameters are placeholders until measured.
For A12x25, prefer ``MotorMount`` from ``fansim.fan_spec`` (cup measured 2026-08-31) via
``export_print_ready(..., mount=spec.motor_mount)`` or ``scripts/export_a12x25_print_ready.py``.
Confirm with calipers when the commercial hub arrives; re-export if dimensions differ.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cadquery as cq
import numpy as np

from fansim.geometry import build_impeller, export_stl, watertight_report
from fansim.geometry.blade import BladeParams
from fansim.geometry.export import WatertightReport, export_step
from fansim.manufacturability.materials import DEFAULT_MATERIAL, MATERIALS
from fansim.manufacturability.printability_score import grade_printability
from fansim.structural.balance import required_counterweight, residual_force, static_unbalance

# Representative FDM print temperatures (°C) per material — nozzle / bed. Order-of-magnitude
# starting points for the print sheet, not a tuned profile; the user dials them in for their printer.
PRINT_TEMPS_C: dict[str, tuple[int, int]] = {
    "PLA": (210, 60), "PLA+": (215, 60), "PETG": (240, 80), "ABS": (250, 100), "TPU": (225, 40),
}

# A thin, curved, balance-critical aerodynamic part: fine layers, solid-ish walls, hub-down.
BLADE_PRINT_RULES = {
    "layer_height_mm": 0.12,      # fine — thin curved trailing edges and any surface features
    "wall_loops": 4,              # near-solid thin blades; strength + surface finish
    "infill_pct": 40,             # hub carries most volume; blades are near-solid from walls
    "orientation": "hub face down on the bed (blades sweeping up) — minimizes blade overhang",
    "supports": "only if a swept/winglet tip overhang exceeds ~50° from vertical; avoid on blades",
    "seam": "hide on the hub bore, never on a blade surface",
    "cooling": "max part cooling for PLA/PETG bridging thin edges; reduce for ABS to avoid warping",
    "brim": "5 mm brim (small hub footprint — helps adhesion and resists tip-heavy tipping)",
}


@dataclass
class BoreSpec:
    """Center shaft bore cut into the hub. dia is a PLACEHOLDER until the motor is measured."""
    bore_dia_mm: float
    through: bool = True                 # through-hole (default) vs blind to depth_mm
    depth_mm: float | None = None        # blind-bore depth from the back face (if not through)
    set_screw_dia_mm: float = 0.0        # >0 adds a radial set-screw hole into the bore
    placeholder: bool = True             # flagged in the readme until the user confirms the number


def bore_hub(model: cq.Workplane, bore: BoreSpec) -> cq.Workplane:
    """Cut a center shaft bore (and optional radial set-screw hole) into a built impeller."""
    shape = model.val()
    bb = shape.BoundingBox()
    r = float(bore.bore_dia_mm) / 2.0
    if r <= 0:
        return model
    if bore.through or bore.depth_mm is None:
        z0, h = bb.zmin - 1.0, (bb.zmax - bb.zmin) + 2.0   # full through-hole with margin
    else:
        z0, h = bb.zmin - 1.0, float(bore.depth_mm) + 1.0   # blind from the back face
    cutter = cq.Solid.makeCylinder(r, h, cq.Vector(0, 0, z0), cq.Vector(0, 0, 1))
    result = shape.cut(cutter)
    if bore.set_screw_dia_mm and bore.set_screw_dia_mm > 0:
        zc = 0.5 * (bb.zmin + bb.zmax)
        sr = float(bore.set_screw_dia_mm) / 2.0
        reach = max(bb.xmax, abs(bb.xmin)) + 1.0    # from outside the hub inward to the bore
        screw = cq.Solid.makeCylinder(sr, reach, cq.Vector(0, 0, zc), cq.Vector(1, 0, 0))
        result = result.cut(screw)
    return cq.Workplane(obj=result)


def carve_motor_mount(model: cq.Workplane, mount, hub_radius_mm: float):
    """Hollow the hub into a CUP that slips over the fan's motor: a cavity from the REAR (-Z) face + a
    central through-bore (bearing/shaft passage), optionally with axial grip cylinders.

    Returns (model, fits, msg). Does NOT widen the hub — if the hub is too narrow to house the motor
    with a wall, it returns fits=False and the model unchanged.

    Grip pads: cut an oversize smooth cup, then fuse cylinders whose centers sit near the cup wall
    (most of the pad in the wall; ``grip_protrude_mm`` sticks into the cavity). Bore is cut last.
    """
    import math

    n_grip = int(getattr(mount, "grip_count", 0) or 0)
    grip_d = float(getattr(mount, "grip_dia_mm", 0.0) or 0.0)
    # Radial oversize of the cup (slip fit); used with or without grip pads.
    clear = float(getattr(mount, "grip_clearance_mm", 0.0) or 0.0)
    from fansim.fan_spec import mount_grip_pad_layout

    need = mount.cavity_dia_mm / 2.0 + clear + mount.min_wall_mm
    layout = mount_grip_pad_layout(mount)
    if layout is not None:
        _cav, r_c, g_r = layout
        need = max(need, r_c + g_r + 0.05)
    if hub_radius_mm < need:
        return (model, False,
                f"hub radius {hub_radius_mm:.1f} mm too small to house the {mount.cavity_dia_mm:.0f} mm "
                f"motor (need >= {need:.1f} mm; widen the hub or this can't be mounted)")
    shape = model.val()
    bb = shape.BoundingBox()
    eps = 0.5
    cav_r = float(mount.cavity_dia_mm) / 2.0 + clear
    cav_h = float(mount.cavity_depth_mm) + eps
    z0 = bb.zmin - eps
    cutter = cq.Solid.makeCylinder(cav_r, cav_h, cq.Vector(0, 0, z0), cq.Vector(0, 0, 1))
    result = shape.cut(cutter)
    grip_msg = ""
    if layout is not None:
        _cav_r, r_center, grip_r = layout
        protrude = grip_r - (r_center - cav_r)
        bore_r = float(mount.rear_bore_dia_mm or 0.0) / 2.0
        if r_center - grip_r <= bore_r + 0.3:
            grip_msg = f"; grip skipped (would collide with {mount.rear_bore_dia_mm:.0f} mm bore)"
        elif r_center + grip_r > hub_radius_mm - 0.05:
            grip_msg = (
                f"; grip skipped (Ø{grip_d:.1f} mm pads need hub radius "
                f">= {r_center + grip_r + 0.05:.1f} mm)"
            )
        else:
            pads = None
            for k in range(n_grip):
                a = 2.0 * math.pi * k / n_grip
                x = r_center * math.cos(a)
                y = r_center * math.sin(a)
                # Start the FUSED pad flush at the rear face (bb.zmin), not at the cutter's
                # z0 = bb.zmin - eps: the cut may overshoot the face for a clean break, but a
                # fused pad inheriting that overshoot leaves a nub sticking out the back. Height
                # cav_h keeps the top embedded just past the cavity floor for a clean fuse.
                pad = cq.Solid.makeCylinder(
                    grip_r, cav_h,
                    cq.Vector(x, y, bb.zmin), cq.Vector(0, 0, 1),
                )
                pads = pad if pads is None else pads.fuse(pad)
            result = result.fuse(pads)
            grip_msg = (
                f" + {n_grip}×Ø{grip_d:.1f} mm grip pads "
                f"(+{protrude:.2f} mm into cup, +{clear:.2f} mm radial clearance)"
            )
    try:
        result = result.clean()
    except Exception:  # noqa: BLE001
        pass
    if mount.rear_bore_dia_mm and mount.rear_bore_dia_mm > 0:
        h = (bb.zmax - bb.zmin) + 2 * eps
        bore = cq.Solid.makeCylinder(
            mount.rear_bore_dia_mm / 2.0, h,
            cq.Vector(0, 0, bb.zmin - eps), cq.Vector(0, 0, 1),
        )
        result = result.cut(bore)

    msg = (f"cup cavity {mount.cavity_dia_mm:.0f} mm x {mount.cavity_depth_mm:.0f} mm deep"
           + (f" + {mount.rear_bore_dia_mm:.0f} mm center bore" if mount.rear_bore_dia_mm else "")
           + grip_msg)
    return cq.Workplane(obj=result), True, msg


def _blade_angles_rad(params: BladeParams) -> np.ndarray:
    """Circumferential blade angles [rad]: the design's uneven pattern, else equal spacing."""
    if params.blade_angles_deg is not None:
        return np.radians(np.asarray(params.blade_angles_deg, float))
    n = params.n_blades
    return np.array([k * 2.0 * np.pi / n for k in range(n)])


def balance_summary(params: BladeParams, rpm: float) -> dict:
    """Static rotor balance from the blade angular pattern (identical unit blades).

    Equal-spaced or balanced-uneven patterns null out; only a broken/asymmetric pattern leaves a
    residual, for which we report the counterweight and the centrifugal force it would otherwise
    throw at the given RPM (radii normalized, so force is a relative red-flag, not an absolute N)."""
    ang = _blade_angles_rad(params)
    u = static_unbalance(ang)
    mr, cw_angle = required_counterweight(ang)
    omega = rpm * 2.0 * np.pi / 60.0
    return {
        "n_blades": int(params.n_blades),
        "even_spacing": params.blade_angles_deg is None,
        "normalized_unbalance": round(float(u.normalized), 6),
        "balanced": bool(u.normalized <= 1e-6),
        "counterweight_mr": round(float(mr), 6),
        "counterweight_angle_deg": round(float(np.degrees(cw_angle)), 1),
        "residual_force_rel": round(float(residual_force(u.normalized, omega)), 4),
    }


def recommend_print_settings(material: str = DEFAULT_MATERIAL) -> dict:
    """Print-settings recommendation for a fan blade in the given material."""
    material = material if material in MATERIALS else DEFAULT_MATERIAL
    mat = MATERIALS[material]
    nozzle_c, bed_c = PRINT_TEMPS_C.get(material, PRINT_TEMPS_C[DEFAULT_MATERIAL])
    return {
        "material": material,
        "nozzle_c": nozzle_c,
        "bed_c": bed_c,
        "heat_deflection_c": mat.heat_deflection_c,
        "material_note": mat.note,
        "blade_suitable": mat.blade_suitable,
        **BLADE_PRINT_RULES,
    }


def build_impeller_with_mount(params: BladeParams, mount) -> tuple[cq.Workplane, bool, str]:
    """Build the aero impeller solid and carve the motor cup (+ grips) into the hub.

    CFD/Assess keep using ``build_impeller`` alone (solid hub). Print + optional preview
    use this so the STL includes the hub opening that matches the commercial motor.
    """
    model = build_impeller(params)
    return carve_motor_mount(model, mount, params.hub_radius)


def export_print_ready(
    params: BladeParams,
    out_stl: str | Path,
    *,
    bore: BoreSpec | None = None,
    mount=None,                       # a MotorMount to carve a real cup cavity (supersedes `bore`)
    tolerance: float = 0.02,          # finer than CFD export (0.05) — smooth printed surfaces
    angular_tolerance: float = 0.1,
    also_step: bool = True,
) -> WatertightReport:
    """Build the impeller, carve the motor mount (or a simple bore), export a fine STL, return the
    watertight report (with mount_fits/mount_msg when a MotorMount is given).

    When ``also_step`` is True (default), write a sibling ``.step`` B-rep next to the STL (§20.1).
    """
    out_stl = Path(out_stl)
    mount_fits, mount_msg = None, ""
    if mount is not None:
        model, mount_fits, mount_msg = build_impeller_with_mount(params, mount)
    else:
        model = build_impeller(params)
        if bore is not None:
            model = bore_hub(model, bore)
    export_stl(model, out_stl, tolerance=tolerance, angular_tolerance=angular_tolerance)
    if also_step:
        export_step(model, out_stl.with_suffix(".step"))
    rep = watertight_report(out_stl)
    rep.mount_fits, rep.mount_msg = mount_fits, mount_msg
    return rep


def export_handedness_pair(
    params: BladeParams,
    out_dir: str | Path,
    *,
    stem: str = "impeller",
    bore: BoreSpec | None = None,
    mount=None,
    designed_omega: int = +1,
    tolerance: float = 0.02,
    angular_tolerance: float = 0.1,
) -> dict[str, Path]:
    """Export as-designed + mirrored STLs with paired ``*.handedness.json`` spin metadata (§19.4).

    Returns paths keyed ``as_designed_stl``, ``as_designed_meta``, ``mirrored_stl``, ``mirrored_meta``.
    """
    from fansim.geometry.handedness import handedness_variants, write_handedness_meta

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for variant in handedness_variants(params, designed_omega=designed_omega):
        stl = out_dir / f"{stem}_{variant.label}.stl"
        meta = out_dir / f"{stem}_{variant.label}.handedness.json"
        export_print_ready(
            variant.params, stl, bore=bore, mount=mount,
            tolerance=tolerance, angular_tolerance=angular_tolerance,
        )
        write_handedness_meta(variant, meta)
        paths[f"{variant.label}_stl"] = stl
        paths[f"{variant.label}_meta"] = meta
    return paths


def print_readme(name: str, params: BladeParams, material: str, report: WatertightReport,
                 balance: dict, settings: dict, bore: BoreSpec | None,
                 objectives: dict | None = None) -> str:
    """Human-readable print sheet (Markdown) accompanying an exported finalist STL."""
    (lo, hi) = report.bounds_mm
    dia = 2.0 * max(abs(lo[0]), abs(hi[0]), abs(lo[1]), abs(hi[1]))
    depth = hi[2] - lo[2]
    L = [f"# Print sheet — {name}", ""]
    if objectives:
        L.append("**Predicted performance (sim):** "
                 + ", ".join(f"{k} {v:.1f}" for k, v in objectives.items()))
        L.append("")
    L += [
        "## Geometry",
        f"- Blades: {params.n_blades}   hub radius: {params.hub_radius:.1f} mm",
        f"- Bounding: dia {dia:.1f} mm × depth {depth:.1f} mm",
        f"- Watertight: {'YES' if report.ok else 'NO — DO NOT PRINT (non-manifold)'} "
        f"({report.n_bodies} body, {report.n_faces} faces, {report.volume_mm3/1000:.1f} cm³)",
        "",
        "## Motor mount",
    ]
    if report.mount_fits is True:
        L.append(f"- ✓ Motor cup carved: {report.mount_msg}. Slips over the motor.")
    elif report.mount_fits is False:
        L.append(f"- ⚠ **NOT MOUNTABLE as-is**: {report.mount_msg}. (Aero-optimal small hubs can't "
                 "house a big motor — widen the hub radius to fit, at some flow/eff cost.)")
    elif bore is None:
        L.append("- Solid hub, NO motor interface modeled. Add a cavity/bore before mounting.")
    if bore is not None and report.mount_fits is None:
        kind = "through-hole" if (bore.through or bore.depth_mm is None) else f"{bore.depth_mm:.1f} mm blind"
        L.append(f"- Center bore: **{bore.bore_dia_mm:.2f} mm dia** ({kind})"
                 + (f", radial set-screw {bore.set_screw_dia_mm:.1f} mm" if bore.set_screw_dia_mm else ""))
        if bore.placeholder:
            L.append("- ⚠ **PLACEHOLDER diameter** — measure your motor's shaft/boss and re-export "
                     "with the real value before printing. This number is a guess.")
    L += [
        "",
        "## Material & print settings",
        f"- Material: **{settings['material']}** (nozzle {settings['nozzle_c']} °C, bed {settings['bed_c']} °C, "
        f"softens ~{settings['heat_deflection_c']:.0f} °C — {settings['material_note']})",
        f"- Layer height: {settings['layer_height_mm']} mm   walls: {settings['wall_loops']}   "
        f"infill: {settings['infill_pct']}%",
        f"- Orientation: {settings['orientation']}",
        f"- Supports: {settings['supports']}",
        f"- Seam: {settings['seam']}   brim: {settings['brim']}",
        f"- Cooling: {settings['cooling']}",
        "",
        "## Printability",
    ]
    grade = grade_printability(params)
    L.append(f"- **{grade.summary}**")
    for f in grade.factors[:3]:
        if f.severity > 0.15:
            L.append(f"  - {f.name} ({f.severity*100:.0f}%): {f.note}")
    L += [
        "",
        "## Balance",
    ]
    if balance["balanced"]:
        L.append(f"- ✓ Statically balanced ({'even' if balance['even_spacing'] else 'balanced-uneven'} "
                 f"spacing, residual {balance['normalized_unbalance']:.2e}).")
    else:
        L.append(f"- ⚠ Residual static unbalance {balance['normalized_unbalance']:.3f}. Add a "
                 f"counterweight (m·r {balance['counterweight_mr']:.3f}) at "
                 f"{balance['counterweight_angle_deg']:.0f}°, or test-spin and trim the heavy blade.")
    L += ["", "*Print at your own risk — printed blades are a relative-comparison baseline, not a "
          "Noctua replacement. Tip clearance and balance matter; spin up gently the first time.*"]
    return "\n".join(L)
