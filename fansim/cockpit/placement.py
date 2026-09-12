# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM
from fansim.fan_spec import FanSpec, check_build, mount_min_hub_radius


@dataclass(frozen=True)
class PlaceChange:
    field: str
    before: float
    after: float
    unit: str = "mm"


@dataclass(frozen=True)
class PlaceResult:
    flat: dict
    changes: list[PlaceChange]
    fit_status: str
    leftover: str


def blade_z_extent(params) -> float:
    """Axial (Z) extent of the blade from its section points -- FAST (no CAD-kernel solid)."""
    from fansim.geometry.blade import _interp_stations, _section_points_3d

    it = _interp_stations(params, params.n_span)
    r0 = params.hub_radius - params.root_embed
    zs = []
    for i in range(params.n_span):
        rf = float(it["r_frac"][i])
        r = r0 + (params.tip_radius - r0) * rf
        pts = _section_points_3d(
            r=r,
            r_frac=rf,
            chord=float(it["chord"][i]),
            stagger_deg=float(it["stagger_deg"][i]),
            thickness=float(it["thickness"][i]),
            max_camber=float(it["max_camber"][i]),
            camber_pos=float(it["camber_pos"][i]),
            sweep=float(it["sweep"][i]),
            skew=float(it["skew"][i]),
            le_sweep=float(it["le_sweep"][i]),
            lean_deg=float(it["lean_deg"][i]),
            n_chord=params.n_chord,
            features=params.features,
        )
        zs += [v.z for v in pts]
    return max(zs) - min(zs)


def blade_max_dia(params) -> float:
    """Max impeller DIAMETER (mm) from section points + optional tip ring.

    Open tips bulge past 2*tip_radius. A shroud sits on that built envelope and
    adds 2 * shroud_thick_mm to the diameter.
    """
    from fansim.geometry.blade import open_tip_rmax_mm

    dia = 2.0 * open_tip_rmax_mm(params)
    thick = float(getattr(params, "shroud_thick_mm", 0.0) or 0.0)
    if thick > 0.0:
        dia += 2.0 * thick
    return dia


def frame_gap_mm(built_tip_dia_mm: float, spec: FanSpec) -> float:
    """Radial leftover from the built tip to the frame ID -- the SAME quantity the CFD
    ``evaluate_candidate`` gap gate checks (``casing/2 - built_r``). ``built_tip_dia_mm`` from
    ``blade_max_dia`` already includes any tip ring."""
    return float(spec.tip_dia_mm[1]) / 2.0 - float(built_tip_dia_mm) / 2.0


def frame_gap_ok(built_tip_dia_mm: float, spec: FanSpec) -> bool:
    """True when the built tip clears the frame by at least the CFD gate's radial floor."""
    return frame_gap_mm(built_tip_dia_mm, spec) >= OPTIMIZER_TIP_GAP_MM


def frame_gap_note(built_tip_dia_mm: float, spec: FanSpec) -> str:
    """Preview/warning text when the tip is too close to the frame for CFD (else '')."""
    gap = frame_gap_mm(built_tip_dia_mm, spec)
    if gap >= OPTIMIZER_TIP_GAP_MM:
        return ""
    return (f"frame gap {gap:.2f} mm < {OPTIMIZER_TIP_GAP_MM:.2f} mm clearance to the "
            f"{float(spec.tip_dia_mm[1]):.0f} mm frame")


def preview_changes(changes: list[PlaceChange]) -> str:
    if not changes:
        return "No geometry changes. CFD will be stale."
    lines = [f"{c.field}: {c.before:.2f} → {c.after:.2f} {c.unit}" for c in changes]
    lines.append("CFD will be stale")
    return "\n".join(lines)


def measure_flat(flat: dict) -> tuple[float, float, float] | None:
    """Measure (built_tip_dia_mm, built_depth_mm, hub_radius_mm) from the built geometry.

    Returns None on failure (missing params, invalid types, geometry rebuild errors, etc).
    """
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat

    try:
        p = blade_from_flat(flat, Features())
        built_tip_dia = float(blade_max_dia(p))
        built_depth = float(blade_z_extent(p))
        hub_radius = float(getattr(p, "hub_radius", flat.get("hub_radius")))
        return built_tip_dia, built_depth, hub_radius
    except Exception:  # noqa: BLE001
        return None


def nominal_fits_spec(flat: dict, spec: FanSpec, measured: tuple[float, float, float] | None = None) -> bool:
    """Fit gate that matches the built geometry (no CadQuery solid)."""
    m = measured or measure_flat(flat)
    if m is None:
        return False
    tip_dia, depth, hub_radius = m

    need = mount_min_hub_radius(spec)
    if need is not None and hub_radius < need:
        return False

    hub_dia = 2.0 * hub_radius
    if not (spec.hub_dia_mm[0] <= hub_dia <= spec.hub_dia_mm[1]):
        return False

    return tip_dia <= spec.tip_dia_mm[1] and depth <= spec.depth_mm[1]


def fit_envelope(flat: dict, spec: FanSpec) -> PlaceResult:
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat

    work = deepcopy(flat)
    changes: list[PlaceChange] = []

    def set_mm(field: str, after: float) -> None:
        before = work.get(field)
        if before is None:
            b = 0.0
        else:
            try:
                b = float(before)
            except Exception:  # noqa: BLE001
                b = 0.0
        if abs(after - b) > 1e-9:
            work[field] = after
            changes.append(PlaceChange(field=field, before=b, after=float(after)))

    # 1) hub radius: raise to mount minimum (if any)
    cur_hub = float(work.get("hub_radius", 0.0))
    need = mount_min_hub_radius(spec)
    if need is not None and cur_hub < need:
        set_mm("hub_radius", float(need))

    # 2) tip: shrink until the built tip diameter leaves the CFD frame-gap clearance. The gate rejects
    #    (before any CFD) anything closer than OPTIMIZER_TIP_GAP_MM radially, so target that same
    #    clearance (diametral = 2x) plus a hair -- else a "fitted" design is rejected instantly at Assess.
    max_dia = float(spec.tip_dia_mm[1])
    target_dia = max_dia - 2.0 * OPTIMIZER_TIP_GAP_MM - 0.1
    tr0 = float(work.get("tip_radius", 0.0))
    tr = tr0
    for _ in range(12):
        work["tip_radius"] = tr
        try:
            dia = blade_max_dia(blade_from_flat(work, Features()))
        except Exception:  # noqa: BLE001
            break
        if dia <= target_dia:
            break
        tr -= (dia - target_dia) / 2.0 + 0.05
        if tr < 20.0:
            break
    work["tip_radius"] = round(tr, 2)
    if abs(work["tip_radius"] - tr0) > 1e-9:
        changes.append(PlaceChange("tip_radius", before=tr0, after=float(work["tip_radius"])))

    # 3) depth: flatten sweep + LE; if still over, gently reduce stagger
    max_d = float(spec.depth_mm[1])

    def depth() -> float:
        return blade_z_extent(blade_from_flat(work, Features()))

    rake = ("sweep_mid", "sweep_tip", "le_sweep_mid", "le_sweep_tip")
    base_rake = {k: float(work.get(k, 0.0)) for k in rake}
    for f in (1.0, 0.8, 0.6, 0.4, 0.2, 0.0):
        for k in rake:
            work[k] = base_rake[k] * f
        try:
            if depth() <= max_d - 0.1:
                break
        except Exception:  # noqa: BLE001
            break
    for k in rake:
        if abs(work.get(k, 0.0) - base_rake[k]) > 1e-9:
            changes.append(PlaceChange(k, before=base_rake[k], after=float(work[k])))

    try:
        over = depth() > max_d
    except Exception:  # noqa: BLE001
        over = False

    if over:
        stag = ("stagger_root", "stagger_mid", "stagger_tip")
        base_stag = {k: float(work.get(k, 0.0)) for k in stag}
        for g in (0.97, 0.94, 0.91, 0.88, 0.85, 0.82, 0.78, 0.74, 0.70):
            for k in stag:
                work[k] = base_stag[k] * g
            try:
                if depth() <= max_d - 0.1:
                    break
            except Exception:  # noqa: BLE001
                break
        for k in stag:
            if abs(work.get(k, 0.0) - base_stag[k]) > 1e-9:
                changes.append(PlaceChange(k, before=base_stag[k], after=float(work[k]), unit="deg"))

    # 4) hub height: enforce motor mount minimum
    min_h = float(getattr(getattr(spec, "motor_mount", None), "min_hub_height_mm", 0.0) or 0.0)
    if min_h > 0.0:
        cur_h = float(work.get("hub_height", 0.0))
        if cur_h < min_h:
            set_mm("hub_height", min_h)

    # final fit status via check_build
    try:
        p = blade_from_flat(work, Features())
        built_tip_dia = float(blade_max_dia(p))
        z_depth = float(blade_z_extent(p))
    except Exception as exc:  # noqa: BLE001
        return PlaceResult(
            flat=work,
            changes=changes,
            fit_status="over_spec",
            leftover=f"geometry failed: {type(exc).__name__}: {exc}",
        )

    hub_dia = 2.0 * float(work.get("hub_radius", 0.0))
    ok, reason = check_build(spec, built_tip_dia, hub_dia, z_depth)
    if ok:  # check_build allows the full frame; the CFD gate also needs the radial tip clearance
        gap = frame_gap_note(built_tip_dia, spec)
        if gap:
            ok, reason = False, gap
    return PlaceResult(
        flat=work,
        changes=changes,
        fit_status="fits" if ok else "over_spec",
        leftover="" if ok else reason,
    )


def scale_to_hub(flat: dict, spec: FanSpec) -> PlaceResult:
    import math

    src = deepcopy(flat)
    changes: list[PlaceChange] = []

    if "tip_radius" not in src:
        src["tip_radius"] = 56.5
        src_tip = 56.5
    else:
        try:
            src_tip = float(src["tip_radius"])
        except Exception:  # noqa: BLE001
            src_tip = float("nan")
        if not math.isfinite(src_tip):
            src["tip_radius"] = 56.5
            src_tip = 56.5

    if src_tip <= 0.0:
        return PlaceResult(flat=src, changes=[], fit_status="unplaced", leftover="source tip radius <= 0")

    target_tip = float(spec.tip_dia_mm[1]) / 2.0 - 2.0
    s = target_tip / src_tip

    scale_keys = (
        "hub_radius",
        "tip_radius",
        "chord_root",
        "chord_mid",
        "chord_tip",
        "sweep_mid",
        "sweep_tip",
        "skew_mid",
        "skew_tip",
        "le_sweep_mid",
        "le_sweep_tip",
        "hub_height",
        "hub_nose",
        "winglet_sweep",
    )
    for k in scale_keys:
        if k not in src:
            continue
        try:
            before = float(src[k])
        except Exception:  # noqa: BLE001
            continue
        after = before * s
        if abs(after - before) > 1e-9:
            src[k] = after
            changes.append(PlaceChange(k, before=before, after=after))

    fitted = fit_envelope(src, spec)
    return PlaceResult(
        flat=fitted.flat,
        changes=changes + fitted.changes,
        fit_status=fitted.fit_status,
        leftover=fitted.leftover,
    )


def placed_child_record(flat: dict, spec: FanSpec, op: str, parent_id: str, hub_key: str) -> dict:
    """Create a new derived record from a catalog/library parent without mutating the parent."""
    if op == "scale_to_hub":
        result = scale_to_hub(flat, spec)
    elif op == "fit_envelope":
        result = fit_envelope(flat, spec)
    else:
        raise ValueError(f"unknown place op {op!r}")
    return {
        "flat": result.flat,
        "fit_status": result.fit_status,
        "leftover": result.leftover,
        "changes": result.changes,
        "parent_id": parent_id,
        "place_op": op,
        "cfd_stale": True,
        "placed_on": hub_key,
    }

