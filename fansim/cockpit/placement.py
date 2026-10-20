from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

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
    zmin, zmax = _blade_z_bounds(params)
    return zmax - zmin


def blade_overhang_below_hub_mm(params) -> float:
    """How far the UNCLIPPED blade sections reach below the hub's motor face (0 if they don't)."""
    import copy

    from fansim.geometry.blade import _hub_axial_range

    raw = copy.copy(params)
    raw.clip_below_hub = False
    return max(0.0, _hub_axial_range(params)[0] - _blade_z_bounds(raw)[0])


def _blade_z_bounds(params) -> tuple[float, float]:
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
            le_skew=float(it["le_skew"][i]),
            tip_notch_count=params.tip_notch_count,
            tip_notch_depth_mm=params.tip_notch_depth_mm,
            le_thick_scale=float(getattr(params, "le_thick_scale", 1.0) or 1.0),
            te_thick_scale=float(getattr(params, "te_thick_scale", 1.0) or 1.0),
            section_family=str(getattr(params, "section_family", "naca") or "naca"),
        )
        zs += [v.z for v in pts]
    lo = min(zs)
    if bool(getattr(params, "clip_below_hub", True)):
        from fansim.geometry.blade import _hub_axial_range

        lo = max(lo, _hub_axial_range(params)[0])  # blades are cut at the hub face (clip_blade_below)
    return lo, max(zs)


def impeller_z_extent(params) -> float:
    """Axial envelope of blades + hub (+ nose) + optional shroud — FAST, no CAD solid.

    Matches the Fit/UI/Assess depth gate: hub height and nose can exceed blade Z alone.
    """
    from fansim.geometry.blade import _hub_axial_range, shroud_axial_range

    b_lo, b_hi = _blade_z_bounds(params)
    hub_lo, hub_hi = _hub_axial_range(params)
    hub_hi = hub_hi + float(getattr(params, "hub_nose_mm", 0.0) or 0.0)
    zs = [b_lo, b_hi, hub_lo, hub_hi]
    shroud = shroud_axial_range(params)
    if shroud is not None:
        zs.extend(shroud)
    return max(zs) - min(zs)


def intake_extra_mm(*, enabled: bool, extra_mm: float) -> float:
    """Clamp Design-session intake overbuild extra (mm). Off → 0; on → [0, 20]."""
    if not enabled:
        return 0.0
    try:
        v = float(extra_mm)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(20.0, v))


def intake_overbuild_note(depth_mm: float | None, nominal_mm: float,
                          extra_mm: float) -> tuple[str, bool]:
    """(caption, is_warning) for the Design Actions card while intake overbuild is on.

    The old caption said "won't drop into stock frame" whenever the switch was on, even for a
    design that fits, and Fit envelope can't clear it (with the switch on, Fit targets
    nominal + extra). Say what the design actually measures and how to get back to stock.
    """
    if extra_mm <= 0:
        return "", False
    if depth_mm is None:
        return (f"intake overbuild on (+{extra_mm:.0f} mm allowed) — depth unknown", True)
    if depth_mm > nominal_mm + 0.05:
        return (
            f"intake overbuild on: impeller {depth_mm:.1f} mm deep vs {nominal_mm:.0f} mm stock "
            f"frame (+{depth_mm - nominal_mm:.1f} mm) — won't drop into a stock frame. To make "
            "it fit: Fit & seed → turn off \"Allow intake overbuild\", then Fit envelope. "
            "(Optimize ignores this switch and always uses the stock depth.)",
            True,
        )
    return (
        f"intake overbuild on (+{extra_mm:.0f} mm allowed), but this impeller is "
        f"{depth_mm:.1f} mm deep — still fits the {nominal_mm:.0f} mm stock frame.",
        False,
    )


def effective_depth_max(spec: FanSpec, *, intake_extra: float = 0.0) -> float:
    """Nominal frame depth + intake overbuild (Fit clamp target)."""
    return float(spec.depth_mm[1]) + float(intake_extra or 0.0)


def depth_allow_max(spec: FanSpec, *, intake_extra: float = 0.0) -> float:
    """Hard allow gate: nominal + Library leeway_depth + intake overbuild."""
    return (
        float(spec.depth_mm[1])
        + float(getattr(spec, "leeway_depth_mm", 0.0) or 0.0)
        + float(intake_extra or 0.0)
    )


def intake_envelope_z_range(
    z_mid: float, nominal_depth: float, intake_extra: float = 0.0,
) -> tuple[float, float]:
    """Outlet-anchored [z_lo, z_hi]: outlet at mid−nominal/2; +Z grows by intake_extra."""
    nom = float(nominal_depth)
    extra = float(intake_extra or 0.0)
    z_lo = float(z_mid) - 0.5 * nom
    z_hi = z_lo + nom + extra
    return z_lo, z_hi


def frame_z_mid_from_points(r, z, hub_radius: float, nominal_depth: float | None = None) -> float:
    """Frame envelope Z mid from outer impeller points (skip motor-cup / grip pads).

    When ``nominal_depth`` is set, the mid is outlet-anchored: z_lo = min(outer z)
    (the clipped hub-face TE), not the bbox centre. Intake overbuild then grows +Z
    only; centering on a taller impeller used to lift z_lo and paint that TE red.
    """
    import numpy as np

    rr = np.asarray(r, dtype=float)
    zz = np.asarray(z, dtype=float)
    outer = rr > float(hub_radius) * 1.05
    z_outlet = float(zz[outer].min()) if np.any(outer) else float(zz.min())
    if nominal_depth is not None:
        return z_outlet + 0.5 * float(nominal_depth)
    if np.any(outer):
        zo = zz[outer]
        return 0.5 * (float(zo.min()) + float(zo.max()))
    return 0.5 * (float(zz.min()) + float(zz.max()))


def out_of_spec_point_mask(
    r,
    z,
    *,
    tip_r: float,
    hub_r: float,
    nom_depth: float,
    intake_extra: float = 0.0,
):
    """True where geometry is past tip OD or frame depth (hub-cup grips ignored for depth)."""
    import numpy as np

    rr = np.asarray(r, dtype=float)
    zz = np.asarray(z, dtype=float)
    zmid = frame_z_mid_from_points(rr, zz, hub_r, nominal_depth=nom_depth)
    z_lo, z_hi = intake_envelope_z_range(zmid, nom_depth, intake_extra)
    depth_oos = ((zz < z_lo) | (zz > z_hi)) & (rr > float(hub_r) * 1.05)
    tip_oos = rr > float(tip_r)
    return (tip_oos | depth_oos).astype(float)


def blade_max_dia(params) -> float:
    """Max impeller DIAMETER (mm) from section points + optional tip ring.

    With ``cylindrical_tip`` (default), OD is capped at ``2*tip_radius``. With trim off,
    open tips can bulge past ``2*tip_radius``. A shroud sits on that built envelope and
    adds ``2 * shroud_thick_mm`` to the diameter.
    """
    from fansim.geometry.blade import open_tip_rmax_mm

    dia = 2.0 * open_tip_rmax_mm(params)
    thick = float(getattr(params, "shroud_thick_mm", 0.0) or 0.0)
    if thick > 0.0:
        dia += 2.0 * thick
    return dia


def preview_changes(changes: list[PlaceChange]) -> str:
    if not changes:
        return "No geometry changes. CFD will be stale."
    lines = [f"{c.field}: {c.before:.2f} → {c.after:.2f} {c.unit}" for c in changes]
    lines.append("CFD will be stale")
    return "\n".join(lines)


def measure_flat(
    flat: dict, features=None,
) -> tuple[float, float, float] | None:
    """Measure (built_tip_dia_mm, built_depth_mm, hub_radius_mm) from the built geometry.

    Uses the same bio-feature layer as Preview/Assess: pass ``features`` explicitly, or
    omit it to pull tubercle/serration/dimple keys from ``flat``.

    Returns None on failure (missing params, invalid types, geometry rebuild errors, etc).
    """
    from fansim.geometry.features import features_from_flat
    from fansim.optimize.search_space import blade_from_flat

    try:
        feat = features if features is not None else features_from_flat(flat)
        p = blade_from_flat(flat, feat)
        built_tip_dia = float(blade_max_dia(p))
        built_depth = float(impeller_z_extent(p))
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

    if tip_dia > spec.tip_dia_mm[1] or depth > spec.depth_mm[1]:
        return False
    # Same CFD leftover gate Assess uses (OPTIMIZER_TIP_GAP_MM).
    return not bool(frame_gap_note(tip_dia, spec))


def frame_gap_note(tip_dia_mm: float, spec: FanSpec) -> str:
    """CFD tip-clearance gate as a human reason string, or ``\"\"`` if OK.

    ``check_build`` allows the impeller OD up to the frame ID. Assess/CFD also need
    ``OPTIMIZER_TIP_GAP_MM`` radial leftover to that ID (same message shape as
    ``evaluate_candidate``).
    """
    from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM

    casing_id = float(spec.tip_dia_mm[1])
    remaining = casing_id / 2.0 - float(tip_dia_mm) / 2.0
    floor = float(OPTIMIZER_TIP_GAP_MM)
    if remaining + 1e-9 >= floor:
        return ""
    return (
        f"{spec.name}: tip gap {remaining:.2f} mm < min {floor:.2f} mm "
        f"to {casing_id:.0f} mm frame"
    )


def fit_envelope(
    flat: dict,
    spec: FanSpec,
    features=None,
    *,
    preserve_tip: bool = False,
    max_depth_mm: float | None = None,
) -> PlaceResult:
    from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM
    from fansim.geometry.features import features_from_flat
    from fansim.optimize.search_space import blade_from_flat

    feat = features if features is not None else features_from_flat(flat)

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

    # 2) tip: shrink until built tip leaves OPTIMIZER_TIP_GAP_MM to the frame ID
    # Gold ✕ / close-ref overlay: preserve recipe tip_radius (silhouette match).
    if not preserve_tip:
        max_dia = float(spec.tip_dia_mm[1])
        target_dia = max_dia - 2.0 * OPTIMIZER_TIP_GAP_MM
        tr0 = float(work.get("tip_radius", 0.0))
        tr = tr0
        for _ in range(12):
            work["tip_radius"] = tr
            try:
                dia = blade_max_dia(blade_from_flat(work, feat))
            except Exception:  # noqa: BLE001
                break
            if dia <= target_dia:
                break
            tr -= (dia - target_dia) / 2.0 + 0.15
            if tr < 20.0:
                break
        work["tip_radius"] = round(tr, 2)
        if abs(work["tip_radius"] - tr0) > 1e-9:
            changes.append(PlaceChange("tip_radius", before=tr0, after=float(work["tip_radius"])))

    # 3) depth: flatten sweep + LE; if still over, gently reduce stagger
    max_d = float(spec.depth_mm[1] if max_depth_mm is None else max_depth_mm)

    def depth() -> float:
        return impeller_z_extent(blade_from_flat(work, feat))

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

    # 5) designed hang (unclipped TE vs hub face). Fit's depth used the clipped solid, so
    # it never saw this; Preview then refused a mesh that looks flush. Grow the hub until
    # hang ≤ 2 mm or we would exceed max_d.
    try:
        from fansim.geometry.blade import MAX_HANG_BELOW_HUB_MM, blade_hang_below_hub_mm

        p_hang = blade_from_flat(work, feat)
        wrap_clip = (
            bool(getattr(p_hang, "clip_below_hub", True))
            and str(getattr(p_hang, "section_wrap", "planar")) == "cylinder"
        )
        hang = blade_hang_below_hub_mm(p_hang) if wrap_clip else 0.0
    except Exception:  # noqa: BLE001
        wrap_clip, hang, p_hang = False, 0.0, None
    if wrap_clip and hang > MAX_HANG_BELOW_HUB_MM:
        before_h = float(work.get("hub_height", 0.0) or 0.0)
        h = before_h
        if h <= 0.0:
            h = float(getattr(p_hang, "hub_height_mm", 0.0) or 0.0) or max(min_h, 15.0)
        for _ in range(48):
            h += 0.5
            work["hub_height"] = h
            try:
                p2 = blade_from_flat(work, feat)
                if impeller_z_extent(p2) > max_d - 0.1:
                    work["hub_height"] = h - 0.5
                    break
                if blade_hang_below_hub_mm(p2) <= MAX_HANG_BELOW_HUB_MM:
                    break
            except Exception:  # noqa: BLE001
                work["hub_height"] = h - 0.5
                break
        after_h = float(work.get("hub_height", 0.0) or 0.0)
        if abs(after_h - before_h) > 1e-9:
            changes.append(PlaceChange("hub_height", before=before_h, after=after_h))

    # final fit status via check_build
    try:
        p = blade_from_flat(work, feat)
        built_tip_dia = float(blade_max_dia(p))
        z_depth = float(impeller_z_extent(p))
    except Exception as exc:  # noqa: BLE001
        return PlaceResult(
            flat=work,
            changes=changes,
            fit_status="over_spec",
            leftover=f"geometry failed: {type(exc).__name__}: {exc}",
        )

    hub_dia = 2.0 * float(work.get("hub_radius", 0.0))
    ok, reason = check_build(spec, built_tip_dia, hub_dia, z_depth)
    if ok:
        gap = frame_gap_note(built_tip_dia, spec)
        if gap:
            ok, reason = False, gap
    return PlaceResult(
        flat=work,
        changes=changes,
        fit_status="fits" if ok else "over_spec",
        leftover="" if ok else reason,
    )


def prepare_export_flat(
    flat: dict, spec: FanSpec, fit_frame: bool, features=None, *, fit_hub: bool = False,
) -> tuple[dict, list[PlaceChange]]:
    """Return the flat that Export should build from.

    Order (when flags are on): grow grip-aware hub first, then ``fit_envelope`` tip/depth,
    so mounting clearance is not lost when tip shrink runs. ``fit_frame=False`` still
    applies hub grow when ``fit_hub=True``.
    """
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

    if fit_hub:
        need = mount_min_hub_radius(spec)
        if need is not None and float(work.get("hub_radius", 0.0)) < need:
            set_mm("hub_radius", float(need) + 0.05)
        if spec.motor_mount is not None:
            from fansim.manufacturability.print_export import mount_hub_params
            from fansim.optimize.search_space import blade_from_flat

            grown, _note = mount_hub_params(blade_from_flat(work, features), spec.motor_mount)
            if grown.hub_height_mm is not None:
                set_mm("hub_height", float(grown.hub_height_mm))
            set_mm("blade_hub_z", float(getattr(grown, "blade_hub_z_mm", 0.0) or 0.0))

    if not fit_frame:
        return work, changes
    res = fit_envelope(work, spec, features=features)
    return res.flat, changes + res.changes


def scale_to_hub(flat: dict, spec: FanSpec, features=None, *, max_depth_mm: float | None = None) -> PlaceResult:
    import math

    from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM

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

    # Same leftover as Fit / Assess / CFD (not a hardcoded 2 mm cushion).
    target_tip = float(spec.tip_dia_mm[1]) / 2.0 - float(OPTIMIZER_TIP_GAP_MM)
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

    fitted = fit_envelope(src, spec, features=features, max_depth_mm=max_depth_mm)
    return PlaceResult(
        flat=fitted.flat,
        changes=changes + fitted.changes,
        fit_status=fitted.fit_status,
        leftover=fitted.leftover,
    )


def placed_child_record(flat: dict, spec: FanSpec, op: str, parent_id: str, hub_key: str,
                        features=None) -> dict:
    """Create a new derived record from a catalog/library parent without mutating the parent."""
    if op == "scale_to_hub":
        result = scale_to_hub(flat, spec, features=features)
    elif op == "fit_envelope":
        result = fit_envelope(flat, spec, features=features)
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
