# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Parametric axial-fan impeller builder.

Coordinate convention (millimeters):
  * Z is the axis of rotation and the mean airflow direction.
  * The blade spans radially outward; sections are lofted from hub to tip.
  * A section at radius ``r`` is an airfoil whose chord is set at a *stagger* angle to the
    rotation plane (the plane perpendicular to Z). Stagger 90 deg = chord aligned with the
    axis (a paddle); small stagger = chord nearly in the rotation plane.

This is the "simple blade" used by the Phase-1 walking skeleton: a NACA section lofted
through a few radial control stations, patterned into N blades on a cylindrical hub.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cadquery as cq
import numpy as np

from fansim.geometry.airfoil import naca4
from fansim.geometry.features import Features, apply_features


@dataclass
class RadialStation:
    """One spanwise control station. ``r_frac`` runs 0 (hub) to 1 (tip)."""

    r_frac: float
    chord: float  # mm
    stagger_deg: float  # angle of chord to rotation plane
    thickness: float = 0.08  # fraction of chord
    max_camber: float = 0.02  # fraction of chord
    camber_pos: float = 0.4  # fraction of chord
    sweep: float = 0.0  # axial (Z) offset of the WHOLE section, mm
    skew: float = 0.0  # small tangential offset of the section, mm (fine adjust)
    lean_deg: float = 0.0  # circumferential angular position of the section (deg).
    # Varying lean_deg from hub to tip WRAPS the blade around the axis (real fan blades sweep
    # circumferentially so trailing edges overlap the next blade); 0 at every station = a
    # straight radial paddle.
    le_sweep: float = 0.0  # axial (Z) offset of the LEADING-EDGE region only, mm. Blends smoothly
    # to zero by mid-chord, so it rakes/curves the leading edge without moving the trailing edge;
    # varying it hub->tip curves the leading-edge LINE (a swept LE, unlike the flat default). Kept
    # LAST so existing positional RadialStation(...) callers are unaffected.


@dataclass
class BladeParams:
    """Full impeller definition. Defaults approximate a Noctua NF-A12x25 envelope."""

    n_blades: int = 7
    hub_radius: float = 21.5  # mm (~43 mm hub diameter)
    tip_radius: float = 56.5  # mm (~113 mm impeller diameter, inside a 120 mm frame)
    root_embed: float = 2.0  # mm the blade root sinks into the hub for a clean fuse
    hub_axial_margin: float = 1.5  # mm the hub extends beyond the blade ROOT z-span each side
    # Hub axial height, mm. None = AUTO: just tall enough to cover the blade ROOTS (+margins) so
    # swept tips no longer inflate the hub / depth. Set a number to force a taller hub (clamped to
    # the root-coverage minimum). See build_impeller.
    hub_height_mm: float | None = None
    hub_profile: str = "cylinder"  # "cylinder" (stubby, default) | "cone" (pointy spinner) | "dome"
    hub_nose_mm: float = 0.0  # nose height on the +Z (intake) end for cone/dome; 0 = flat top
    rpm: float = 2000.0  # metadata; used later by CFD, not by geometry
    n_span: int = 18  # loft sections across the span (wide wrapped blades need resolution)
    n_chord: int = 60  # points per airfoil surface
    features: Features = field(default_factory=Features)  # bio-inspired feature layer
    # Optional per-blade circumferential angles [deg]. None => equal spacing (360/N). Set to an
    # UNEVEN, statically balanced pattern (fansim.structural.balance.balanced_uneven_spacing) to
    # spread the blade-pass tone. Must have length n_blades. See [[fan-sim-uneven-spacing]].
    blade_angles_deg: list[float] | None = None
    stations: list[RadialStation] = field(
        default_factory=lambda: [
            # High solidity: blades overlap (solidity > 1) at hub/mid like a real fan.
            RadialStation(r_frac=0.0, chord=34.0, stagger_deg=26.0, thickness=0.08,
                          max_camber=0.05, sweep=0.0, lean_deg=0.0),
            RadialStation(r_frac=0.5, chord=44.0, stagger_deg=26.0, thickness=0.05,
                          max_camber=0.06, sweep=3.0, lean_deg=14.0),
            RadialStation(r_frac=1.0, chord=38.0, stagger_deg=22.0, thickness=0.03,
                          max_camber=0.06, sweep=5.0, lean_deg=26.0),
        ]
    )


def blade_solidity(params: BladeParams) -> dict[str, float]:
    """Solidity = blade chord / circumferential pitch, at hub/mid/tip.

    Solidity > 1 means adjacent blades OVERLAP (no see-through gap) — a first-order driver of
    static pressure and the defining look of high-pressure fans like the A12x25. Reported so
    overlap is an explicit, optimizable quantity rather than an accident of the parameters.
    """
    interp = _interp_stations(params, 3)  # hub, mid, tip
    r_root = params.hub_radius - params.root_embed
    out = {}
    for i, name in enumerate(("hub", "mid", "tip")):
        rf = interp["r_frac"][i]
        r = r_root + (params.tip_radius - r_root) * rf
        chord = float(interp["chord"][i])
        beta = np.radians(float(interp["stagger_deg"][i]))
        pitch = 2.0 * np.pi * r / params.n_blades
        out[name] = float(chord * np.cos(beta) / pitch)
    return out


def _interp_stations(params: BladeParams, n_span: int) -> dict[str, np.ndarray]:
    """Linearly interpolate the control stations onto ``n_span`` spanwise samples."""
    ctrl = sorted(params.stations, key=lambda s: s.r_frac)
    rf = np.array([s.r_frac for s in ctrl])
    q = np.linspace(0.0, 1.0, n_span)
    fields = ["chord", "stagger_deg", "thickness", "max_camber", "camber_pos",
              "sweep", "skew", "le_sweep", "lean_deg"]
    out = {"r_frac": q}
    for name in fields:
        out[name] = np.interp(q, rf, np.array([getattr(s, name) for s in ctrl]))
    return out


def _section_points_3d(
    r: float,
    r_frac: float,
    chord: float,
    stagger_deg: float,
    thickness: float,
    max_camber: float,
    camber_pos: float,
    sweep: float,
    skew: float,
    le_sweep: float,
    lean_deg: float,
    n_chord: int,
    features: Features,
) -> list[cq.Vector]:
    """Build the closed 3D loop of one airfoil section wrapped onto the cylinder at radius ``r``.

    The airfoil is defined on the cylindrical stream-surface of radius ``r`` (standard for
    axial turbomachinery): chordwise/thickness coords are pitched by the stagger angle into
    circumferential (arc) and axial directions, the circumferential distance is mapped to an
    ARC ANGLE about the axis, and the whole section is placed at angular position ``lean_deg``.
    Because lean_deg varies along the span, the blade sweeps/wraps circumferentially and can
    overlap the neighbouring blade — the shape real fans have, which a straight radial stack
    (lean=0) cannot make.
    """
    loop = naca4(max_camber, camber_pos, thickness, n_chord)
    # Drop the explicit closing duplicate; the wire is closed by makePolygon(close=True).
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]

    beta = np.radians(stagger_deg)
    cb, sb = np.cos(beta), np.sin(beta)

    x = loop[:, 0]  # chord fraction, 0=LE .. 1=TE
    a = (x - 0.5) * chord  # chordwise distance from mid-chord
    b = loop[:, 1] * chord  # thickness-wise distance
    if features.active:
        a, b = apply_features(x, a, b, r_frac, chord, features)
    t = a * cb - b * sb + skew  # circumferential (tangential) distance, mm
    # Leading-edge curve: an axial offset that is full at the LE (x=0) and blends smoothly to zero
    # by mid-chord (x>=0.5), so it rakes the leading edge without disturbing the trailing edge.
    w_le = np.where(x < 0.5, 0.5 * (1.0 + np.cos(2.0 * np.pi * x)), 0.0)
    axial = a * sb + b * cb + sweep + le_sweep * w_le

    # Place the (planar) section in the tangent plane at angular position theta = lean_deg and
    # radius r, i.e. rotate the whole section about the Z axis by theta. Keeping each section
    # planar makes the loft cap cleanly (watertight); varying theta along the span wraps the
    # blade circumferentially.
    th = np.radians(lean_deg)
    ct, st = np.cos(th), np.sin(th)
    xs = r * ct - t * st
    ys = r * st + t * ct
    return [cq.Vector(float(px), float(py), float(z))
            for px, py, z in zip(xs, ys, axial)]


def apply_winglet(params: BladeParams, span_frac: float = 0.85,
                  sweep_add: float = 0.0, lean_add: float = 0.0) -> BladeParams:
    """Add a winglet: the outer span (beyond ``span_frac``) curls, by inserting a 'shoulder' station on
    the nominal blade trajectory and deflecting the TIP beyond it (extra axial sweep + circumferential
    lean). This concentrates the bend at the tip — a real winglet/tip-cap — without a full multi-station
    rewrite. sweep_add/lean_add = 0 is a no-op. Mutates and returns ``params``."""
    if sweep_add == 0.0 and lean_add == 0.0:
        return params
    span_frac = float(min(max(span_frac, 0.55), 0.95))
    st = sorted(params.stations, key=lambda s: s.r_frac)
    rs = [s.r_frac for s in st]

    def interp(field):
        return float(np.interp(span_frac, rs, [getattr(s, field) for s in st]))

    shoulder = RadialStation(span_frac, interp("chord"), interp("stagger_deg"), interp("thickness"),
                             interp("max_camber"), interp("camber_pos"), interp("sweep"), interp("skew"),
                             interp("lean_deg"), le_sweep=interp("le_sweep"))
    tip = st[-1]
    tip_wl = RadialStation(tip.r_frac, tip.chord, tip.stagger_deg, tip.thickness, tip.max_camber,
                           tip.camber_pos, tip.sweep + sweep_add, tip.skew, tip.lean_deg + lean_add,
                           le_sweep=tip.le_sweep)
    params.stations = [s for s in st if s.r_frac < span_frac] + [shoulder, tip_wl]
    return params


def apply_tip_shape(params: BladeParams, tip_round: float = 0.0,
                    start_frac: float = 0.80, n: int = 4) -> BladeParams:
    """Round the blade TIP instead of leaving a blunt straight edge between the LE and TE.

    Over the outer span (beyond ``start_frac``) the chord is tapered following a quarter-ellipse, so
    the leading and trailing edges converge into a smooth curved tip. Sections are centred on their
    mid-chord (see _section_points_3d: ``a = (x-0.5)*chord``), so shrinking the chord pulls BOTH edges
    inward symmetrically -> a rounded tip. ``tip_round`` in [0,1]: 0 = square tip (unchanged), 1 =
    fully rounded. Intermediate stations are inserted for a smooth arc. Mutates and returns ``params``.
    Apply AFTER apply_winglet so the rounded tip inherits any winglet deflection."""
    tr = float(min(max(tip_round, 0.0), 1.0))
    if tr <= 0.0:
        return params
    start_frac = float(min(max(start_frac, 0.5), 0.92))
    st = sorted(params.stations, key=lambda s: s.r_frac)
    rs = [s.r_frac for s in st]

    def interp(field, rf):
        return float(np.interp(rf, rs, [getattr(s, field) for s in st]))

    kept = [s for s in st if s.r_frac < start_frac]
    tip_stations = []
    for i in range(1, n + 1):
        rf = start_frac + (1.0 - start_frac) * i / n
        u = (rf - start_frac) / (1.0 - start_frac)          # 0 at start .. 1 at the tip
        # quarter-ellipse chord scale: 1.0 at the start, (1-tr) at the very tip, bulging outward so
        # the outer edge reads as a rounded arc rather than a straight taper.
        scale = (1.0 - tr) + tr * float(np.sqrt(max(0.0, 1.0 - u * u)))
        scale = max(scale, 0.12)                             # keep the tip wire non-degenerate for the loft
        tip_stations.append(RadialStation(
            rf, interp("chord", rf) * scale, interp("stagger_deg", rf), interp("thickness", rf),
            interp("max_camber", rf), interp("camber_pos", rf), interp("sweep", rf),
            interp("skew", rf), interp("lean_deg", rf), le_sweep=interp("le_sweep", rf)))
    params.stations = kept + tip_stations
    return params


def build_blade_solid(params: BladeParams) -> cq.Solid:
    """Loft one blade solid from hub to tip (raising loft resolution for active features)."""
    n_span = params.features.required_span_sections(params.n_span)
    # Extra inserted stations (winglet shoulder / tip rounding) live in the outer span; raise the
    # spanwise loft resolution so that curved tip reads smoothly instead of as a few facets.
    if len(params.stations) > 3:
        n_span = max(n_span, 30)
    n_chord = params.features.required_chord_points(params.n_chord)
    interp = _interp_stations(params, n_span)
    r_root = params.hub_radius - params.root_embed
    r_tip = params.tip_radius

    wires: list[cq.Wire] = []
    for i in range(n_span):
        rf = float(interp["r_frac"][i])
        r = r_root + (r_tip - r_root) * rf
        pts = _section_points_3d(
            r=r,
            r_frac=rf,
            chord=float(interp["chord"][i]),
            stagger_deg=float(interp["stagger_deg"][i]),
            thickness=float(interp["thickness"][i]),
            max_camber=float(interp["max_camber"][i]),
            camber_pos=float(interp["camber_pos"][i]),
            sweep=float(interp["sweep"][i]),
            skew=float(interp["skew"][i]),
            le_sweep=float(interp["le_sweep"][i]),
            lean_deg=float(interp["lean_deg"][i]),
            n_chord=n_chord,
            features=params.features,
        )
        wires.append(cq.Wire.makePolygon(pts, close=True))

    return cq.Solid.makeLoft(wires, True)


def set_uneven_spacing(params: BladeParams, spread: float = 0.3, rng=None,
                       min_gap_deg: float = 20.0, max_tries: int = 60) -> BladeParams:
    """Set an uneven-but-balanced circumferential blade pattern on ``params`` (mutates + returns).

    Delegates to fansim.structural.balance.balanced_uneven_spacing (balanced by construction) and
    stores the angles in degrees. Retries until the smallest adjacent gap >= ``min_gap_deg`` (so
    high-solidity blades don't collide); if none qualifies, falls back to equal spacing
    (blade_angles_deg=None). spread<=0 leaves equal spacing. See fansim.acoustics.tonal for the
    compute-free peak-tone score of a pattern.
    """
    from fansim.structural.balance import balanced_uneven_spacing  # local import avoids a cycle

    if spread <= 0.0:
        params.blade_angles_deg = None
        return params
    rng = np.random.default_rng() if rng is None else rng
    for _ in range(max_tries):
        ang = balanced_uneven_spacing(params.n_blades, spread=spread, rng=rng)
        gaps = np.diff(np.concatenate([ang, [ang[0] + 2 * np.pi]]))
        if np.degrees(gaps.min()) >= min_gap_deg:
            params.blade_angles_deg = [float(a) for a in np.degrees(ang)]
            return params
    params.blade_angles_deg = None  # couldn't place without collision -> equal spacing
    return params


def _root_axial_span(params: BladeParams) -> tuple[float, float]:
    """Axial (z) min/max of the blade ROOT section — the zone the hub must cover to fuse cleanly.

    Only the root attaches to the hub, so this (not the swept-tip bounding box) is what sets the
    minimum hub height. Features are ignored here (negligible axial effect for sizing)."""
    st = params.stations[0]
    r = params.hub_radius - params.root_embed
    pts = _section_points_3d(
        r=r, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg, thickness=st.thickness,
        max_camber=st.max_camber, camber_pos=st.camber_pos, sweep=st.sweep, skew=st.skew,
        le_sweep=st.le_sweep, lean_deg=st.lean_deg, n_chord=params.n_chord, features=Features())
    zs = [p.z for p in pts]
    return min(zs), max(zs)


def _hub_axial_range(params: BladeParams, blade: cq.Solid) -> tuple[float, float]:
    """(z_bottom, z_top) of the hub CYLINDER body.

    AUTO (hub_height_mm is None): cover the blade ROOTS + hub_axial_margin each side — short, so a
    swept tip no longer drags the hub (and total depth) taller. An explicit hub_height_mm forces a
    taller hub (clamped to the root-coverage minimum), centered on the root z-span."""
    r_lo, r_hi = _root_axial_span(params)
    center = 0.5 * (r_lo + r_hi)
    min_h = (r_hi - r_lo) + 2.0 * params.hub_axial_margin
    if params.hub_height_mm is not None:
        h = max(float(params.hub_height_mm), min_h)
    else:
        h = min_h
    return center - h / 2.0, center + h / 2.0


def _cylinder_hub(params: BladeParams, z_bottom: float, z_top: float) -> cq.Solid:
    return cq.Solid.makeCylinder(params.hub_radius, z_top - z_bottom,
                                 cq.Vector(0, 0, z_bottom), cq.Vector(0, 0, 1))


def build_hub(params: BladeParams, z_bottom: float, z_top: float) -> cq.Solid:
    """The hub solid between z_bottom..z_top: a cylinder, optionally capped with a pointy cone or a
    rounded dome nose of height ``hub_nose_mm`` on the +Z (intake) end. Falls back to a plain
    cylinder if a nose op fails, so the impeller always builds."""
    R = params.hub_radius
    profile = (params.hub_profile or "cylinder").lower()
    nose = float(params.hub_nose_mm or 0.0)
    if profile == "cylinder" or nose <= 0.0:
        return _cylinder_hub(params, z_bottom, z_top)
    try:
        if profile == "cone":  # analytic cone cap, seated 0.5 mm into the hub for a clean fuse
            ov = 0.5
            base = _cylinder_hub(params, z_bottom, z_top)
            cap = cq.Solid.makeCone(R, 0.5, nose + ov, cq.Vector(0, 0, z_top - ov), cq.Vector(0, 0, 1))
            return base.fuse(cap).clean()
        if profile == "dome":  # ONE revolved profile (hub wall + quarter-ellipse dome) — no fuse seam
            import numpy as np
            eps = 0.1  # tiny axis offset avoids the revolve axis-degeneracy (negligible center pinhole)
            arc = [(max(float(R * np.cos(t)), eps), float(z_top + nose * np.sin(t)))
                   for t in np.linspace(0.0, np.pi / 2, 24)[1:]]
            outline = [(eps, z_bottom), (R, z_bottom), (R, z_top), *arc]  # close() returns down the axis
            wp = cq.Workplane("XZ").polyline(outline).close().revolve(360, (0, 0, 0), (0, 1, 0))
            return wp.val()
    except Exception:  # noqa: BLE001 - a kernel hiccup on the nose shouldn't kill the build
        pass
    return _cylinder_hub(params, z_bottom, z_top)


def build_impeller(params: BladeParams | None = None) -> cq.Workplane:
    """Build the full impeller: N patterned blades fused onto a hub.

    Returns a CadQuery ``Workplane`` wrapping the fused solid.
    """
    params = params or BladeParams()
    blade = build_blade_solid(params)

    z_bottom, z_top = _hub_axial_range(params, blade)
    hub = build_hub(params, z_bottom, z_top)

    # Blade angular positions: equal spacing by default, or a custom (e.g. balanced-uneven) pattern.
    if params.blade_angles_deg is None:
        angles = [k * 360.0 / params.n_blades for k in range(params.n_blades)]
    else:
        angles = list(params.blade_angles_deg)
        if len(angles) != params.n_blades:
            raise ValueError(
                f"blade_angles_deg has {len(angles)} entries, expected n_blades={params.n_blades}")
    blades = [blade.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), a) for a in angles]

    fused = hub.fuse(*blades).clean()
    return cq.Workplane(obj=fused)


def build_impeller_preview(params: BladeParams | None = None, tol: float = 0.15):
    """FAST visual impeller for the live preview: tessellate ONE lofted blade + the hub, then
    rotate-copy the blade mesh around the axis — with NO boolean fuse.

    The boolean union in ``build_impeller`` dominates featured builds (a fuse of 11 featured blades
    onto the hub is ~140 s and blows the preview timeout), yet a preview only needs to LOOK right, not
    be watertight. Skipping the fuse turns ~160 s into ~6 s. Returns ``(trimesh.Trimesh, volume_mm3)``
    where volume is the accurate sum of the solids' own volumes (the meshes overlap at the blade roots,
    so the concatenated mesh's own volume would be wrong for the weight check). NOT watertight — use
    ``build_impeller`` for CFD/export where a single sealed solid is required."""
    import trimesh

    params = params or BladeParams()
    blade = build_blade_solid(params)
    z_bottom, z_top = _hub_axial_range(params, blade)
    hub = build_hub(params, z_bottom, z_top)

    def _tm(shape: cq.Solid) -> "trimesh.Trimesh":
        verts, faces = shape.tessellate(tol)
        v = np.array([[p.x, p.y, p.z] for p in verts], dtype=float)
        return trimesh.Trimesh(vertices=v, faces=np.array(faces, dtype=int), process=False)

    blade_mesh, hub_mesh = _tm(blade), _tm(hub)
    if params.blade_angles_deg is None:
        angles = [k * 360.0 / params.n_blades for k in range(params.n_blades)]
    else:
        angles = list(params.blade_angles_deg)
    parts = [hub_mesh]
    for a in angles:
        m = blade_mesh.copy()
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(a), (0, 0, 1)))
        parts.append(m)
    mesh = trimesh.util.concatenate(parts)
    volume_mm3 = float(blade.Volume()) * len(angles) + float(hub.Volume())
    return mesh, volume_mm3
