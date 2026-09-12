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
            le_skew=float(it["le_skew"][i]),
            tip_notch_count=params.tip_notch_count,
            tip_notch_depth_mm=params.tip_notch_depth_mm,
            le_thick_scale=float(getattr(params, "le_thick_scale", 1.0) or 1.0),
            te_thick_scale=float(getattr(params, "te_thick_scale", 1.0) or 1.0),
            section_family=str(getattr(params, "section_family", "naca") or "naca"),
        )
        zs += [v.z for v in pts]
    return max(zs) - min(zs)


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

    # 2) tip: shrink until built tip diameter fits the frame
    max_dia = float(spec.tip_dia_mm[1])
    tr0 = float(work.get("tip_radius", 0.0))
    tr = tr0
    for _ in range(12):
        work["tip_radius"] = tr
        try:
            dia = blade_max_dia(blade_from_flat(work, Features()))
        except Exception:  # noqa: BLE001
            break
        if dia <= max_dia - 0.15:
            break
        tr -= (dia - max_dia) / 2.0 + 0.15
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
    return PlaceResult(
        flat=work,
        changes=changes,
        fit_status="fits" if ok else "over_spec",
        leftover="" if ok else reason,
    )


def prepare_export_flat(
    flat: dict, spec: FanSpec, fit_frame: bool, features=None,
) -> tuple[dict, list[PlaceChange]]:
    """Return the flat that Export should build from.

    ``fit_frame=False`` copies the editor (no geometry change). ``True`` runs
    ``fit_envelope`` so the STL fits the selected frame before hub-grow.
    """
    if not fit_frame:
        return deepcopy(flat), []
    res = fit_envelope(flat, spec, features=features)
    return res.flat, res.changes


def scale_to_hub(flat: dict, spec: FanSpec, features=None) -> PlaceResult:
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

    fitted = fit_envelope(src, spec, features=features)
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
