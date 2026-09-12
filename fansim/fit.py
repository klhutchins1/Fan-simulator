"""Hub-fit helpers shared by catalog + cockpit (no Trame / Optuna).

Keeps ``fansim.catalog`` off ``fansim.cockpit.placement`` (§11.2).
"""

from __future__ import annotations

from fansim.fan_spec import FanSpec, mount_min_hub_radius


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
