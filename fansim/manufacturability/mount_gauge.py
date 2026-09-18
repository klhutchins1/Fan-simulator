"""Gauge a print-ready impeller STL against FanSpec motor mount + frame envelope.

Used before the commercial hub arrives so exports are checked against the
**measured** A12x25 cup (2026-08-31) rather than guessed bore diameters.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh

from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM
from fansim.fan_spec import FanSpec, MotorMount, mount_min_hub_radius


@dataclass(frozen=True)
class MountGauge:
    tip_od_mm: float
    hub_od_mm: float
    axial_depth_mm: float
    cavity_dia_mm: float | None
    cavity_depth_mm: float | None
    rear_bore_dia_mm: float | None
    watertight: bool
    mount_ok: bool
    frame_ok: bool
    hub_wall_ok: bool
    notes: tuple[str, ...]


def _radial_xy(vertices: np.ndarray) -> np.ndarray:
    return np.sqrt(vertices[:, 0] ** 2 + vertices[:, 1] ** 2)


def _estimate_cavity(
    mesh: trimesh.Trimesh,
    *,
    expected_cavity_r: float,
    expected_cavity_depth: float,
) -> tuple[float | None, float | None, float | None]:
    """Estimate cup cavity dia/depth and rear bore from a Z-up mesh.

    ``expected_cavity_r`` should be the *cut* radius (nominal + radial clearance).
    Samples near the rear (−Z) face for the cup wall, and forward of the cup
    depth for the smaller through-bore (mid-hub still sits inside the cavity).
    Anchors on the expected cut radius so grip pads do not pull the estimate inward.
    """
    v = np.asarray(mesh.vertices, dtype=float)
    if len(v) < 50:
        return None, None, None
    z = v[:, 2]
    zmin, zmax = float(z.min()), float(z.max())
    span = max(zmax - zmin, 1e-6)
    rear = z <= (zmin + 0.08 * span)
    r = _radial_xy(v)

    # Prefer vertices near the *expected* cut wall (grips sit well inside; hub OD sits outside).
    # Keep the band tight — ±1.8 mm reaches the hub outer shell on A12x25 and over-reads.
    cav_r = None
    for half_w in (0.55, 0.90, 1.25):
        near = rear & (np.abs(r - expected_cavity_r) <= half_w)
        if int(np.count_nonzero(near)) >= 25:
            cav_r = float(np.median(r[near]))
            break
    if cav_r is None:
        wall = rear & (r > expected_cavity_r * 0.94) & (r < expected_cavity_r * 1.06)
        if int(np.count_nonzero(wall)) >= 20:
            cav_r = float(np.percentile(r[wall], 40))
        else:
            rear_inner = rear & (r < expected_cavity_r * 1.08)
            if int(np.count_nonzero(rear_inner)) < 20:
                rear_inner = rear & (r < np.percentile(r, 35))
            cav_r = float(np.percentile(r[rear_inner], 75)) if np.any(rear_inner) else None

    cav_depth = None
    if cav_r is not None and cav_r > 1.0:
        band = (r > 0.85 * cav_r) & (r < 1.05 * cav_r)
        if np.any(band):
            cav_depth = float(np.percentile(z[band], 90) - zmin)

    # The through-bore lives forward of the cup. Its wall is an extruded cylinder,
    # so the mesh tessellates it only at the two ends — the cavity-floor ring
    # (z ≈ zmin + cavity_depth) and the front face (z ≈ zmax) — never along its
    # length. Sample from the cavity floor through the front face so at least one
    # of those r≈bore rings is captured; the r < cap filter below keeps the wider
    # cup wall out. (A narrow mid-hub band would fall between both rings and miss
    # the bore entirely.)
    depth_guess = float(expected_cavity_depth) if expected_cavity_depth > 0 else (cav_depth or 0.4 * span)
    forward = z >= (zmin + depth_guess - 0.5)
    forward &= z <= (zmax + 1e-6)
    bore_r = None
    if np.any(forward):
        # Bore wall = small-r cluster inside the cup radius.
        cap = (cav_r if cav_r is not None else expected_cavity_r) * 0.75
        bore_band = forward & (r < cap)
        if int(np.count_nonzero(bore_band)) >= 15:
            bore_r = float(np.percentile(r[bore_band], 90))
        else:
            bore_r = float(np.percentile(r[forward], 2))
    return (
        None if cav_r is None else 2.0 * cav_r,
        cav_depth,
        None if bore_r is None else 2.0 * bore_r,
    )


def _estimate_hub_od_mm(mesh: trimesh.Trimesh, *, outside_r: float) -> float:
    """Hub outer diameter from vertices *outside* the motor cup (cavity verts skew low percentiles)."""
    v = np.asarray(mesh.vertices, dtype=float)
    r = _radial_xy(v)
    outer = r > (outside_r + 0.4)
    # Hub shell is the low-r band of the exterior; blades sit farther out.
    if int(np.count_nonzero(outer)) < 30:
        return 2.0 * float(np.percentile(r, 12.0))
    tip_r = float(np.percentile(r[outer], 99.0))
    hub_band = outer & (r < max(outside_r + 10.0, 0.48 * tip_r))
    if int(np.count_nonzero(hub_band)) < 30:
        hub_band = outer & (r < 0.55 * tip_r)
    # 10th percentile under-read grip-aware hubs; mid-low of the shell is more stable.
    return 2.0 * float(np.percentile(r[hub_band], 30.0))


def gauge_print_stl(
    path: str,
    spec: FanSpec,
    *,
    tip_gap_mm: float = OPTIMIZER_TIP_GAP_MM,
    cavity_tol_mm: float = 0.85,
    depth_tol_mm: float = 1.25,
    bore_tol_mm: float = 1.25,
    tip_fp_tol_mm: float = 0.20,
) -> MountGauge:
    """Compare an exported STL to ``spec.motor_mount`` and frame tip/depth limits.

    Mesh percentiles on a carved cup (grips, tessellation) are noisy — cavity/depth/bore
    tolerances and ``tip_fp_tol_mm`` absorb that without loosening Fit/CFD gates.
    """
    mesh = trimesh.load(str(path), force="mesh")
    v = np.asarray(mesh.vertices, dtype=float)
    r = _radial_xy(v)
    tip_od = 2.0 * float(np.percentile(r, 99.5))
    axial = float(mesh.extents[2])
    notes: list[str] = []

    mount = spec.motor_mount
    cav_dia = cav_dep = bore_dia = None
    mount_ok = False
    hub_wall_ok = True
    clear = float(getattr(mount, "grip_clearance_mm", 0.0) or 0.0) if mount else 0.0
    cut_r = (mount.cavity_dia_mm / 2.0 + clear) if mount else 0.0
    hub_od = _estimate_hub_od_mm(mesh, outside_r=cut_r if cut_r > 0 else float(np.percentile(r, 8.0)))
    if mount is None:
        notes.append("spec has no MotorMount — cannot verify cup")
    else:
        need_r = mount_min_hub_radius(spec)
        if need_r is not None and hub_od / 2.0 + 0.6 < need_r:
            hub_wall_ok = False
            notes.append(
                f"hub OD {hub_od:.1f} mm may be thin vs mount min radius {need_r:.2f} mm"
            )
        # Gauge the *cut* cup (nominal + radial clearance); grips sit inside that wall.
        expected_cut_dia = mount.cavity_dia_mm + 2.0 * clear
        cav_dia, cav_dep, bore_dia = _estimate_cavity(
            mesh,
            expected_cavity_r=cut_r,
            expected_cavity_depth=mount.cavity_depth_mm,
        )
        ok_parts = []
        if cav_dia is None:
            notes.append("could not estimate cavity diameter from mesh")
            ok_parts.append(False)
        else:
            d_cav = abs(cav_dia - expected_cut_dia)
            ok_parts.append(d_cav <= cavity_tol_mm)
            if d_cav > cavity_tol_mm:
                notes.append(
                    f"cavity dia ~{cav_dia:.2f} mm vs cut {expected_cut_dia:.2f} "
                    f"(nominal {mount.cavity_dia_mm:.2f} + {2.0 * clear:.2f} clear; "
                    f"Δ {d_cav:.2f} > tol {cavity_tol_mm})"
                )
        if cav_dep is None:
            notes.append("could not estimate cavity depth from mesh")
            ok_parts.append(False)
        else:
            d_dep = abs(cav_dep - mount.cavity_depth_mm)
            ok_parts.append(d_dep <= depth_tol_mm)
            if d_dep > depth_tol_mm:
                notes.append(
                    f"cavity depth ~{cav_dep:.2f} mm vs mount {mount.cavity_depth_mm:.2f} "
                    f"(Δ {d_dep:.2f} > tol {depth_tol_mm})"
                )
        if mount.rear_bore_dia_mm > 0 and bore_dia is not None:
            d_bore = abs(bore_dia - mount.rear_bore_dia_mm)
            ok_parts.append(d_bore <= bore_tol_mm)
            if d_bore > bore_tol_mm:
                notes.append(
                    f"rear bore ~{bore_dia:.2f} mm vs mount {mount.rear_bore_dia_mm:.2f} "
                    f"(Δ {d_bore:.2f} > tol {bore_tol_mm})"
                )
        mount_ok = bool(ok_parts) and all(ok_parts) and hub_wall_ok

    frame_id = float(spec.tip_dia_mm[1])
    tip_leftover = frame_id / 2.0 - tip_od / 2.0
    depth_max = float(spec.depth_mm[1])
    tip_ok = tip_leftover + float(tip_fp_tol_mm) + 1e-9 >= float(tip_gap_mm)
    frame_ok = tip_ok and axial <= depth_max + 0.2
    if not tip_ok:
        notes.append(
            f"tip OD {tip_od:.2f} mm leaves {tip_leftover:.2f} mm to {frame_id:.0f} mm "
            f"frame (need ≥ {tip_gap_mm:.2f} mm; mesh FP tol {tip_fp_tol_mm:.2f} mm)"
        )
    if axial > depth_max + 0.2:
        notes.append(f"axial depth {axial:.2f} mm exceeds frame {depth_max:.1f} mm")

    if not mesh.is_watertight:
        notes.append("mesh is not watertight — do not print")

    if mount_ok and frame_ok and mesh.is_watertight and not notes:
        notes.append("gauge OK vs MotorMount + frame envelope")

    return MountGauge(
        tip_od_mm=tip_od,
        hub_od_mm=hub_od,
        axial_depth_mm=axial,
        cavity_dia_mm=cav_dia,
        cavity_depth_mm=cav_dep,
        rear_bore_dia_mm=bore_dia,
        watertight=bool(mesh.is_watertight),
        mount_ok=mount_ok,
        frame_ok=frame_ok,
        hub_wall_ok=hub_wall_ok,
        notes=tuple(notes),
    )


def mount_checklist_md(gauge: MountGauge, spec: FanSpec, *, stl_name: str) -> str:
    """Markdown checklist for pre-hub print readiness."""
    mm: MotorMount | None = spec.motor_mount
    lines = [
        f"# Print-fit checklist — {stl_name}",
        "",
        f"**Target hub/frame:** {spec.name} (semi-official measured mount in `FanSpec`, "
        "confirm with calipers when the commercial hub arrives).",
        "",
        "## Gauge (from exported STL)",
        f"- Tip OD: **{gauge.tip_od_mm:.2f} mm**",
        f"- Hub OD (exterior): **{gauge.hub_od_mm:.2f} mm**",
        f"- Axial depth: **{gauge.axial_depth_mm:.2f} mm**",
        f"- Watertight: {'YES' if gauge.watertight else 'NO'}",
        f"- Frame fit: {'PASS' if gauge.frame_ok else 'FAIL'}",
        f"- Mount cup: {'PASS' if gauge.mount_ok else 'FAIL'}",
    ]
    if mm is not None:
        clear = float(mm.grip_clearance_mm or 0.0)
        lines += [
            "",
            "## Expected MotorMount (measured 2026-08-31)",
            f"- Cup cavity: **{mm.cavity_dia_mm:.2f} mm** dia × **{mm.cavity_depth_mm:.1f} mm** deep",
            f"- Rear bore: **{mm.rear_bore_dia_mm:.1f} mm**",
            f"- Shaft (motor): **{mm.shaft_dia_mm:.1f} mm** (not printed)",
            f"- Min hub wall: **{mm.min_wall_mm:.1f} mm** → min hub radius "
            f"**{(mm.cavity_dia_mm / 2.0 + clear + mm.min_wall_mm):.2f} mm**",
            f"- Min hub height: **{mm.min_hub_height_mm:.1f} mm**",
            f"- Grip pads: **{int(mm.grip_count)}** × Ø**{mm.grip_dia_mm:.1f} mm** "
            f"(cup +**{clear:.2f} mm** radial clearance)",
            "",
            "## Mesh estimates",
            f"- Cavity dia (cut) ~ **{gauge.cavity_dia_mm}** mm",
            f"- Cavity depth ~ **{gauge.cavity_depth_mm}** mm",
            f"- Rear bore ~ **{gauge.rear_bore_dia_mm}** mm",
        ]
    lines += ["", "## Notes"]
    for n in gauge.notes:
        lines.append(f"- {n}")
    lines += [
        "",
        "## When the commercial hub arrives",
        "1. Caliper motor boss OD, cup depth, rear bore, and shaft.",
        "2. If any differ from MotorMount by >0.2 mm, update `fansim/fan_spec.py` and re-export.",
        "3. Dry-fit before first spin; sand/ream cavity only if the print is tight.",
        "",
        "**Do not print** `validation/reference/a12x25_impeller.stl` for mounting — that file is "
        "CFD-oriented and is not a carved print-ready cup.",
    ]
    return "\n".join(lines)


def write_print_fit_sidecars(
    stl_path: str | Path,
    spec: FanSpec,
    *,
    report_mount_fits: bool | None = None,
    report_mount_msg: str = "",
    params_summary: dict | None = None,
) -> MountGauge:
    """Write ``*_mount_checklist.md`` and ``*_print_fit.json`` next to an exported STL."""
    stl_path = Path(stl_path)
    gauge = gauge_print_stl(str(stl_path), spec)
    checklist = mount_checklist_md(gauge, spec, stl_name=stl_path.name)
    stl_path.with_name(stl_path.stem + "_mount_checklist.md").write_text(
        checklist, encoding="utf-8"
    )
    payload = {
        "stl": stl_path.as_posix(),
        "spec": spec.name,
        "mount_fits_carve": report_mount_fits,
        "mount_msg": report_mount_msg,
        "params": params_summary or {},
        "gauge": {
            "tip_od_mm": gauge.tip_od_mm,
            "hub_od_mm": gauge.hub_od_mm,
            "axial_depth_mm": gauge.axial_depth_mm,
            "cavity_dia_mm": gauge.cavity_dia_mm,
            "cavity_depth_mm": gauge.cavity_depth_mm,
            "rear_bore_dia_mm": gauge.rear_bore_dia_mm,
            "watertight": gauge.watertight,
            "mount_ok": gauge.mount_ok,
            "frame_ok": gauge.frame_ok,
            "hub_wall_ok": gauge.hub_wall_ok,
            "notes": list(gauge.notes),
        },
        "motor_mount": None
        if spec.motor_mount is None
        else {
            "cavity_dia_mm": spec.motor_mount.cavity_dia_mm,
            "cavity_depth_mm": spec.motor_mount.cavity_depth_mm,
            "rear_bore_dia_mm": spec.motor_mount.rear_bore_dia_mm,
            "shaft_dia_mm": spec.motor_mount.shaft_dia_mm,
            "min_wall_mm": spec.motor_mount.min_wall_mm,
            "min_hub_height_mm": spec.motor_mount.min_hub_height_mm,
            "grip_count": int(spec.motor_mount.grip_count),
            "grip_dia_mm": float(spec.motor_mount.grip_dia_mm),
            "grip_clearance_mm": float(spec.motor_mount.grip_clearance_mm),
            "grip_protrude_mm": float(spec.motor_mount.grip_protrude_mm),
            "provenance": "measured cup 2026-08-31; confirm when commercial hub arrives",
        },
    }
    stl_path.with_name(stl_path.stem + "_print_fit.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return gauge
