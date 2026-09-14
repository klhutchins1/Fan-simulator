"""Gauge a print-ready impeller STL against FanSpec motor mount + frame envelope.

Used before the commercial hub arrives so exports are checked against the
**measured** A12x25 cup (2026-08-31) rather than guessed bore diameters.
"""

from __future__ import annotations

from dataclasses import dataclass

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

    Samples near the rear (−Z) face for the cup wall, and forward of the cup
    depth for the smaller through-bore (mid-hub still sits inside the cavity).
    """
    v = np.asarray(mesh.vertices, dtype=float)
    if len(v) < 50:
        return None, None, None
    z = v[:, 2]
    zmin, zmax = float(z.min()), float(z.max())
    span = max(zmax - zmin, 1e-6)
    rear = z <= (zmin + 0.08 * span)
    r = _radial_xy(v)

    rear_inner = rear & (r < expected_cavity_r * 1.15)
    if int(np.count_nonzero(rear_inner)) < 20:
        rear_inner = rear & (r < np.percentile(r, 40))
    cav_r = float(np.percentile(r[rear_inner], 95)) if np.any(rear_inner) else None

    cav_depth = None
    if cav_r is not None and cav_r > 1.0:
        band = (r > 0.85 * cav_r) & (r < 1.05 * cav_r)
        if np.any(band):
            cav_depth = float(np.percentile(z[band], 90) - zmin)

    # Through-bore lives forward of the cup; avoid the cavity band.
    depth_guess = float(expected_cavity_depth) if expected_cavity_depth > 0 else (cav_depth or 0.4 * span)
    forward = z >= (zmin + depth_guess + 0.5)
    forward &= z <= (zmax - 0.05 * span)
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


def gauge_print_stl(
    path: str,
    spec: FanSpec,
    *,
    tip_gap_mm: float = OPTIMIZER_TIP_GAP_MM,
    cavity_tol_mm: float = 0.6,
    depth_tol_mm: float = 1.0,
    bore_tol_mm: float = 1.0,
) -> MountGauge:
    """Compare an exported STL to ``spec.motor_mount`` and frame tip/depth limits."""
    mesh = trimesh.load(str(path), force="mesh")
    v = np.asarray(mesh.vertices, dtype=float)
    r = _radial_xy(v)
    tip_od = 2.0 * float(np.percentile(r, 99.5))
    hub_od = 2.0 * float(np.percentile(r, 8.0))
    axial = float(mesh.extents[2])
    notes: list[str] = []

    mount = spec.motor_mount
    cav_dia = cav_dep = bore_dia = None
    mount_ok = False
    hub_wall_ok = True
    if mount is None:
        notes.append("spec has no MotorMount — cannot verify cup")
    else:
        need_r = mount_min_hub_radius(spec)
        if need_r is not None and hub_od / 2.0 + 0.3 < need_r:
            hub_wall_ok = False
            notes.append(
                f"hub OD {hub_od:.1f} mm may be thin vs mount min radius {need_r:.2f} mm"
            )
        cav_dia, cav_dep, bore_dia = _estimate_cavity(
            mesh,
            expected_cavity_r=mount.cavity_dia_mm / 2.0,
            expected_cavity_depth=mount.cavity_depth_mm,
        )
        ok_parts = []
        if cav_dia is None:
            notes.append("could not estimate cavity diameter from mesh")
            ok_parts.append(False)
        else:
            d_cav = abs(cav_dia - mount.cavity_dia_mm)
            ok_parts.append(d_cav <= cavity_tol_mm)
            if d_cav > cavity_tol_mm:
                notes.append(
                    f"cavity dia ~{cav_dia:.2f} mm vs mount {mount.cavity_dia_mm:.2f} "
                    f"(Δ {d_cav:.2f} > tol {cavity_tol_mm})"
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
    frame_ok = tip_leftover + 1e-9 >= float(tip_gap_mm) and axial <= depth_max + 0.2
    if tip_leftover + 1e-9 < float(tip_gap_mm):
        notes.append(
            f"tip OD {tip_od:.2f} mm leaves {tip_leftover:.2f} mm to {frame_id:.0f} mm "
            f"frame (need ≥ {tip_gap_mm:.2f} mm)"
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
        f"- Hub OD (p8): **{gauge.hub_od_mm:.2f} mm**",
        f"- Axial depth: **{gauge.axial_depth_mm:.2f} mm**",
        f"- Watertight: {'YES' if gauge.watertight else 'NO'}",
        f"- Frame fit: {'PASS' if gauge.frame_ok else 'FAIL'}",
        f"- Mount cup: {'PASS' if gauge.mount_ok else 'FAIL'}",
    ]
    if mm is not None:
        lines += [
            "",
            "## Expected MotorMount (measured 2026-08-31)",
            f"- Cup cavity: **{mm.cavity_dia_mm:.2f} mm** dia × **{mm.cavity_depth_mm:.1f} mm** deep",
            f"- Rear bore: **{mm.rear_bore_dia_mm:.1f} mm**",
            f"- Shaft (motor): **{mm.shaft_dia_mm:.1f} mm** (not printed)",
            f"- Min hub wall: **{mm.min_wall_mm:.1f} mm** → min hub radius "
            f"**{(mm.cavity_dia_mm / 2.0 + mm.min_wall_mm):.2f} mm**",
            f"- Min hub height: **{mm.min_hub_height_mm:.1f} mm**",
            "",
            "## Mesh estimates",
            f"- Cavity dia ~ **{gauge.cavity_dia_mm}** mm",
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
