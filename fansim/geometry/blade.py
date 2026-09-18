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

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import cadquery as cq
import numpy as np

from fansim.geometry.airfoil import (
    SECTION_FAMILIES,
    SECTION_NACA,
    SECTION_PLATE,
    naca4,
    section_loop_2d,
)
from fansim.geometry.features import Features, apply_features

if TYPE_CHECKING:  # pragma: no cover
    import cadquery as cq

_CQ = None


def _cq():
    """Lazy CadQuery import (avoids importing OCCT on pure-math paths)."""
    global _CQ  # noqa: PLW0603
    if _CQ is None:
        import cadquery as cq  # noqa: PLC0415

        _CQ = cq
    return _CQ


@dataclass(frozen=True)
class Vec:
    """Lightweight 3D vector (CadQuery-free).

    Many geometry helpers only need x/y/z floats for envelope checks, shrouds, etc. Keep those
    paths independent from CadQuery/OCCT so unit tests and non-CAD tooling don't pay the import
    cost (or hit platform brittleness).
    """

    x: float
    y: float
    z: float


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
    # varying it hub->tip curves the leading-edge LINE (a swept LE, unlike the flat default).
    le_skew: float = 0.0  # circumferential (θ) offset of the LEADING-EDGE region only, mm.
    # Same blend as le_sweep. Positive = +t (same sign as skew). Kept last so positional callers
    # of RadialStation(...) are unaffected.


SICKLE_DEFAULT_MM = 8.0
NOTCH_COUNT = 3
NOTCH_DEPTH_MM = 1.5
NOTCH_START_FRAC = 0.88  # outer-span TE bites; hub is untouched
# Full/CFD loft floor when tip notches are on. Was 48; §15.6 profile (2026-09-16) showed
# fuse wall-clock ~linear in this floor (48→~168 s, 28→~87 s, 24→~63 s on stock a12x25).
# 28 still resolves three boxy outer-span bites (same as preview).
NOTCH_SPAN_SECTIONS = 28
# Preview can use fewer span samples; still enough to read three boxy bites.
NOTCH_SPAN_SECTIONS_PREVIEW = 28
# Boxy TE tooth: steep ramps + flat bite (skewed-rectangle TE steps vs soft sin lobes).
NOTCH_RAMP = 0.06
NOTCH_DUTY = 0.55


def tip_notch_tooth(u: float, count: int) -> float:
    """Unit-height boxy TE bite at outer-span fraction ``u`` ∈ [0, 1].

    Three (``count``) flat-bottom pulses in the outer band — steep walls so the loft reads as
    skewed rectangular TE steps (close-ref A12x25 tip TE), not a sine wave. 0 at the hub.
    """
    n = int(count)
    if n <= 0 or u <= 0.0:
        return 0.0
    local = (float(n) * float(u)) % 1.0
    ramp = float(NOTCH_RAMP)
    duty = float(NOTCH_DUTY)
    if local < ramp:
        return local / ramp if ramp > 1e-9 else 1.0
    if local < duty:
        return 1.0
    if local < duty + ramp:
        return max(0.0, 1.0 - (local - duty) / ramp) if ramp > 1e-9 else 0.0
    return 0.0


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
    # Where the blade roots sit on the hub, mm. 0 = centered (legacy). Positive = blades higher
    # toward +Z / intake (more hub below the roots). Negative = blades lower toward the outlet.
    # Clamped so the root section stays inside the hub. Needs hub_height taller than the root
    # span to have any effect (auto hub has no slack).
    blade_hub_z_mm: float = 0.0
    hub_profile: str = "cylinder"  # "cylinder" (stubby, default) | "cone" (pointy spinner) | "dome"
    hub_nose_mm: float = 0.0  # nose height on the +Z (intake) end for cone/dome; 0 = flat top
    rpm: float = 2000.0  # metadata; used later by CFD, not by geometry
    n_span: int = 18  # loft sections across the span (wide wrapped blades need resolution)
    n_chord: int = 60  # points per airfoil surface
    features: Features = field(default_factory=Features)  # bio-inspired feature layer
    shroud_thick_mm: float = 0.0  # 0 = no tip ring; else radial wall outside the built tip
    shroud_height_frac: float = 1.0  # 1 = full tip Z-span; <1 = TE-anchored partial ring (recovery)
    # Optional per-blade circumferential angles [deg]. None => equal spacing (360/N). Set to an
    # UNEVEN, statically balanced pattern (fansim.structural.balance.balanced_uneven_spacing) to
    # spread the blade-pass tone. Must have length n_blades. See [[fan-sim-uneven-spacing]].
    blade_angles_deg: list[float] | None = None
    tip_notch_count: int = 0  # 0 = off; stamped 3 by apply_notched_tips
    tip_notch_depth_mm: float = 0.0  # TE bite, mm; 0 = off
    # When True, intersect each lofted blade with a cylinder of radius tip_radius so the tip
    # face is cylindrical (matches the cover circle). False = legacy bulging LE/TE corners.
    cylindrical_tip: bool = True
    # Chordwise thickness bias (global):
    #   NACA — scale local thickness near LE / TE (1 = stock; typical 0.5–1.5).
    #   plate — ``le_thick_scale`` / ``te_thick_scale`` are LE/TE roundness in [0, 1]
    #   (1 = full bullnose, ~0.2 = sharp printable edge).
    le_thick_scale: float = 1.0
    te_thick_scale: float = 1.0
    # Airfoil family: "naca" (default) or "plate" (constant-t; camber bows the face;
    # LE/TE radius from le/te_thick_scale).
    section_family: str = SECTION_NACA
    # Span loft between control stations: "linear" (default, can kink at mid) or "pchip"
    # (shape-preserving cubic — smooth through hub/mid/tip). Stage 1 optional smooth curves.
    span_interp: str = "linear"
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


SHROUD_EMBED_MM = 0.8
SHROUD_DEFAULT_MM = 1.6
SHROUD_MIN_WALL_MM = 0.8
SHROUD_FULL_EPS = 1e-9

# Coarser loft for screen-only solids (watertight + envelope). CFD / export keep BladeParams defaults.
SCREEN_N_SPAN = 10
SCREEN_N_CHORD = 36


def with_screen_loft(params: BladeParams) -> BladeParams:
    """Copy ``params`` with screen loft density. Does not mutate the caller's object."""
    from copy import deepcopy
    from dataclasses import replace

    return replace(deepcopy(params), n_span=SCREEN_N_SPAN, n_chord=SCREEN_N_CHORD)


def normalize_shroud_thick_mm(thick: float) -> float:
    """0 stays off. A nudge in (0, min wall) snaps up to a printable two-wall ring.

    The cockpit slider used to step 0.2 mm, so 'turning the shroud on' landed on 0.20 mm —
    a hair-thin hoop that still draws but fails the FDM gate.
    """
    t = float(thick or 0.0)
    if t <= 0.0:
        return 0.0
    if t < SHROUD_MIN_WALL_MM:
        return SHROUD_MIN_WALL_MM
    return t


def shroud_is_full(params: "BladeParams") -> bool:
    t = float(getattr(params, "shroud_thick_mm", 0.0) or 0.0)
    f = min(max(float(getattr(params, "shroud_height_frac", 1.0) or 0.0), 0.0), 1.0)
    return t > 0.0 and f >= 1.0 - SHROUD_FULL_EPS


def open_tip_rmax_mm(params: BladeParams) -> float:
    """Max radial extent (mm) of blade section points — no ring.

    Uses ``params.features`` so tip round / winglets / etc. count toward the CFD tip-gap
    floor (empty Features under-read OD and let Assess launch Docker on an OOS design).
    With ``cylindrical_tip``, the solid is cut to ``tip_radius``, so the reported OD is capped.
    """
    it = _interp_stations(params, params.n_span)
    r0 = params.hub_radius - params.root_embed
    rmax = 0.0
    for i in range(params.n_span):
        rf = float(it["r_frac"][i])
        r = r0 + (params.tip_radius - r0) * rf
        pts = _section_points_3d(
            r=r, r_frac=rf,
            chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]),
            thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]),
            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord,
            features=params.features,
            le_skew=float(it["le_skew"][i]),
            tip_notch_count=params.tip_notch_count,
            tip_notch_depth_mm=params.tip_notch_depth_mm,
            **_thick_scale_kw(params),
        )
        for v in pts:
            rr = math.hypot(v.x, v.y)
            if rr > rmax:
                rmax = rr
    if bool(getattr(params, "cylindrical_tip", True)):
        rmax = min(rmax, float(params.tip_radius))
    return rmax


def blade_solidity(params: BladeParams) -> dict[str, float]:
    """Solidity = blade chord / circumferential pitch, at hub/mid/tip.

    Solidity > 1 means adjacent blades OVERLAP (no see-through gap) — a first-order driver of
    static pressure and the defining look of high-pressure fans like the A12x25. Reported so
    overlap is an explicit, optimizable quantity rather than an accident of the parameters.

    Hub radius is ``params.hub_radius`` (physical annulus), not ``hub − root_embed`` (embed is
    only for CAD fuse depth).
    """
    interp = _interp_stations(params, 3)  # hub, mid, tip
    r_hub = float(params.hub_radius)
    r_tip = float(params.tip_radius)
    out = {}
    for i, name in enumerate(("hub", "mid", "tip")):
        rf = float(interp["r_frac"][i])
        r = r_hub + (r_tip - r_hub) * rf
        chord = float(interp["chord"][i])
        beta = np.radians(float(interp["stagger_deg"][i]))
        pitch = 2.0 * np.pi * r / params.n_blades
        out[name] = float(chord * np.cos(beta) / pitch)
    return out


def min_blade_wall_mm(params: BladeParams) -> float:
    """Thinnest body-wall thickness across the control stations, in mm.

    Each station's wall is ``thickness`` (a fraction of chord) × ``chord`` (mm). The thinnest
    such wall sets how fine the CFD surface mesh must be to resolve the blade (see
    ``openfoam_case.surface_level_for_wall``): a thin plate under-resolved to ~1 cell loses
    blade loading. Excludes the LE/TE ``*_thick_scale`` knife edges, which are sub-features no
    practical mesh resolves.
    """
    return min(float(s.thickness) * float(s.chord) for s in params.stations)


SPAN_INTERP_LINEAR = "linear"
SPAN_INTERP_PCHIP = "pchip"
SPAN_INTERP_MODES = (SPAN_INTERP_LINEAR, SPAN_INTERP_PCHIP)


def _interp_stations(params: BladeParams, n_span: int) -> dict[str, np.ndarray]:
    """Interpolate control stations onto ``n_span`` spanwise samples.

    Default ``span_interp="linear"`` matches historical behavior (can kink at mid).
    ``span_interp="pchip"`` uses a shape-preserving cubic through the same stations
    so mid can move without a sharp elbow.
    """
    ctrl = sorted(params.stations, key=lambda s: s.r_frac)
    rf = np.array([s.r_frac for s in ctrl], dtype=float)
    q = np.linspace(0.0, 1.0, n_span)
    fields = ["chord", "stagger_deg", "thickness", "max_camber", "camber_pos",
              "sweep", "skew", "le_sweep", "le_skew", "lean_deg"]
    out = {"r_frac": q}
    mode = str(getattr(params, "span_interp", SPAN_INTERP_LINEAR) or SPAN_INTERP_LINEAR).lower()
    use_pchip = mode == SPAN_INTERP_PCHIP and len(rf) >= 3
    for name in fields:
        y = np.array([getattr(s, name) for s in ctrl], dtype=float)
        if use_pchip:
            try:
                from scipy.interpolate import PchipInterpolator
                out[name] = PchipInterpolator(rf, y)(q)
                continue
            except Exception:  # noqa: BLE001 — fall back to linear
                pass
        out[name] = np.interp(q, rf, y)
    return out


def _section_loop(
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
    le_skew: float = 0.0,
    tip_notch_count: int = 0,
    tip_notch_depth_mm: float = 0.0,
    le_thick_scale: float = 1.0,
    te_thick_scale: float = 1.0,
    section_family: str = SECTION_NACA,
) -> tuple[np.ndarray, list[cq.Vector]]:
    """Closed section on the cylinder at ``r``, plus chord-fraction ``x`` (LE/TE indexing)."""
    fam = str(section_family or SECTION_NACA).lower().strip()
    if fam not in SECTION_FAMILIES:
        fam = SECTION_NACA
    # Plate: le/te_thick_scale → edge roundness (1=full bullnose, 0=sharp). NACA ignores.
    if fam == SECTION_PLATE:
        le_radius_frac = float(np.clip(le_thick_scale, 0.0, 1.0))
        te_radius_frac = float(np.clip(te_thick_scale, 0.0, 1.0))
    else:
        le_radius_frac = te_radius_frac = 1.0
    loop, x_param = section_loop_2d(
        fam, max_camber=max_camber, camber_pos=camber_pos, thickness=thickness,
        n_points=n_chord, te_radius_frac=te_radius_frac, le_radius_frac=le_radius_frac,
        return_chord_param=True,
    )
    # Drop the explicit closing duplicate; the wire is closed by makePolygon(close=True).
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
        x_param = x_param[:-1]

    beta = np.radians(stagger_deg)
    cb, sb = np.cos(beta), np.sin(beta)

    # Surface X places the section; generator chord param drives LE/TE weights (not cambered X).
    x_surf = loop[:, 0]
    x = np.asarray(x_param, dtype=float)
    a = (x_surf - 0.5) * chord  # chordwise distance from mid-chord (cambered surface)
    b = loop[:, 1] * chord  # thickness-wise distance
    if fam != SECTION_PLATE:
        b = apply_le_te_thickness(x, b, chord, le_thick_scale, te_thick_scale)
    if features.active:
        a, b = apply_features(x, a, b, r_frac, chord, features)
    if tip_notch_count > 0 and tip_notch_depth_mm > 0.0:
        span = 1.0 - NOTCH_START_FRAC
        u = float(np.clip((float(r_frac) - NOTCH_START_FRAC) / span, 0.0, 1.0))
        w_te = np.clip((x - 0.5) / 0.5, 0.0, 1.0)
        # Mild tip-ward amplitude ramp (skewed-rectangle read on TE). Do NOT reuse
        # the name ``skew`` — that is the circumferential station offset below.
        tooth_amp = 0.92 + 0.16 * u
        tooth = tip_notch_tooth(u, int(tip_notch_count)) * tooth_amp
        a = a - float(tip_notch_depth_mm) * tooth * w_te
    # Leading-edge weight: 1 at the LE (x=0), 0 by mid-chord (x>=0.5).
    w_le = np.where(x < 0.5, 0.5 * (1.0 + np.cos(2.0 * np.pi * x)), 0.0)
    t = a * cb - b * sb + skew + le_skew * w_le  # circumferential (tangential) distance, mm
    axial = a * sb + b * cb + sweep + le_sweep * w_le

    # Place the (planar) section in the TANGENT PLANE at angular position theta = lean_deg and
    # radius r: rotate the section about Z by theta. This is NOT stream-surface wrapping
    # (θ = t/r); chordwise ``t`` stays Euclidean in the tangent plane. Keeping each section
    # planar makes the loft watertight; varying lean along the span wraps the planform
    # circumferentially. ``cylindrical_tip`` then clips the solid to a cylinder of tip_radius
    # (whole tip face — LE/TE corners included).
    th = np.radians(lean_deg)
    ct, st = np.cos(th), np.sin(th)
    xs = r * ct - t * st
    ys = r * st + t * ct
    pts = [cq.Vector(float(px), float(py), float(z))
           for px, py, z in zip(xs, ys, axial)]
    return x, pts


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
    le_skew: float = 0.0,
    tip_notch_count: int = 0,
    tip_notch_depth_mm: float = 0.0,
    le_thick_scale: float = 1.0,
    te_thick_scale: float = 1.0,
    section_family: str = SECTION_NACA,
) -> list[cq.Vector]:
    """Build the closed 3D loop of one airfoil section in the tangent plane at radius ``r``.

    Placement is planar-tangent (not θ = t/r stream-surface wrap): chordwise/thickness coords
    are pitched by stagger into tangential ``t`` and axial ``z``, then the whole planar section
    is rotated about Z to ``lean_deg``. Varying lean along the span wraps the planform so
    blades can overlap — a straight radial stack (lean=0) cannot. ``cylindrical_tip`` later
    clips the lofted solid to a cylinder of ``tip_radius``. Optional ``le_thick_scale`` /
    ``te_thick_scale`` biases NACA LE/TE thickness; on plate they set LE/TE roundness (0–1).
    """
    _, pts = _section_loop(
        r=r, r_frac=r_frac, chord=chord, stagger_deg=stagger_deg, thickness=thickness,
        max_camber=max_camber, camber_pos=camber_pos, sweep=sweep, skew=skew, le_sweep=le_sweep,
        lean_deg=lean_deg, n_chord=n_chord, features=features, le_skew=le_skew,
        tip_notch_count=tip_notch_count, tip_notch_depth_mm=tip_notch_depth_mm,
        le_thick_scale=le_thick_scale, te_thick_scale=te_thick_scale,
        section_family=section_family,
    )
    return pts


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
                             interp("lean_deg"), le_sweep=interp("le_sweep"), le_skew=interp("le_skew"))
    tip = st[-1]
    tip_wl = RadialStation(tip.r_frac, tip.chord, tip.stagger_deg, tip.thickness, tip.max_camber,
                           tip.camber_pos, tip.sweep + sweep_add, tip.skew, tip.lean_deg + lean_add,
                           le_sweep=tip.le_sweep, le_skew=tip.le_skew)
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
            interp("skew", rf), interp("lean_deg", rf), le_sweep=interp("le_sweep", rf),
            le_skew=interp("le_skew", rf)))
    params.stations = kept + tip_stations
    return params


def build_blade_solid(params: BladeParams) -> cq.Solid:
    """Loft one blade solid from hub to tip (raising loft resolution for active features)."""
    cq = _cq()
    n_span = params.features.required_span_sections(params.n_span)
    # Extra inserted stations (winglet shoulder / tip rounding) live in the outer span; raise the
    # spanwise loft resolution so that curved tip reads smoothly instead of as a few facets.
    # Screen/preview loft (§13.22): do NOT bump — ``with_screen_loft`` already set n_span low on
    # purpose; bumping to 30 defeats Preview timing (tip-round was ~7.8 s vs stock ~2.3 s).
    screen = int(params.n_span) <= SCREEN_N_SPAN
    if len(params.stations) > 3 and not screen:
        n_span = max(n_span, 30)
    if int(params.tip_notch_count or 0) > 0:
        # Full solids keep 48; screen/preview loft uses a lighter floor.
        notch_floor = (
            NOTCH_SPAN_SECTIONS_PREVIEW if screen else NOTCH_SPAN_SECTIONS
        )
        n_span = max(n_span, notch_floor)
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
            le_skew=float(interp["le_skew"][i]),
            tip_notch_count=params.tip_notch_count,
            tip_notch_depth_mm=params.tip_notch_depth_mm,
            **_thick_scale_kw(params),
        )
        wires.append(cq.Wire.makePolygon(pts, close=True))

    blade = cq.Solid.makeLoft(wires, True)
    if bool(getattr(params, "cylindrical_tip", True)):
        blade = _trim_blade_to_tip_cylinder(blade, float(params.tip_radius))
    return blade


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
        le_sweep=st.le_sweep, lean_deg=st.lean_deg, n_chord=params.n_chord, features=Features(),
        le_skew=st.le_skew,
        tip_notch_count=params.tip_notch_count,
        tip_notch_depth_mm=params.tip_notch_depth_mm,
        **_thick_scale_kw(params),
    )
    zs = [p.z for p in pts]
    return min(zs), max(zs)


def tip_section_points(params: BladeParams) -> list[Vec]:
    """The outermost control station's section loop — the chord the tip ring must swallow."""
    st = max(params.stations, key=lambda s: s.r_frac)
    r = params.hub_radius - params.root_embed
    r = r + (params.tip_radius - r) * st.r_frac
    pts = _section_points_3d(
        r=r, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg,
        thickness=st.thickness, max_camber=st.max_camber, camber_pos=st.camber_pos,
        sweep=st.sweep, skew=st.skew, le_sweep=st.le_sweep, lean_deg=st.lean_deg,
        n_chord=params.n_chord, features=Features(), le_skew=st.le_skew,
        tip_notch_count=params.tip_notch_count,
        tip_notch_depth_mm=params.tip_notch_depth_mm,
        **_thick_scale_kw(params),
    )
    if bool(getattr(params, "cylindrical_tip", True)):
        pts = _clamp_points_to_cylinder(pts, float(params.tip_radius))
    return pts


def tip_section_rmin_mm(params: BladeParams) -> float:
    """MIN radial extent (mm) of the tip section — the mid-chord, which sits near ``tip_radius``.

    The max hypot occurs at the LE/TE corners (a staggered chord swings its ends outboard), so
    sizing the ring bore off ``open_tip_rmax_mm`` would only fuse the corners and leave the rest
    of the chord open to the outside. The bore must go under this minimum instead."""
    import math

    return min(math.hypot(v.x, v.y) for v in tip_section_points(params))


def _tip_z_span(params: BladeParams) -> tuple[float, float]:
    zs = [p.z for p in tip_section_points(params)]
    return min(zs), max(zs)


def _shroud_solid(params: BladeParams) -> cq.Solid | None:
    cq = _cq()
    t = float(params.shroud_thick_mm or 0.0)
    if t <= 0.0:
        return None
    # Outer wall clears the widest point of the blade (LE/TE corners); the bore dives under the
    # NARROWEST point of the tip chord so the whole section is buried in the ring, not just its
    # corners. Anything else leaves a radial channel straight past the tip.
    r_out = open_tip_rmax_mm(params) + t
    r_in = tip_section_rmin_mm(params) - SHROUD_EMBED_MM
    if r_in <= 0.0 or r_out <= r_in:
        return None
    z_span = shroud_axial_range(params)
    if z_span is None:
        return None
    z0, z1 = z_span
    h = max(z1 - z0, 1.0)
    outer = cq.Solid.makeCylinder(r_out, h, cq.Vector(0, 0, z0), cq.Vector(0, 0, 1))
    inner = cq.Solid.makeCylinder(r_in, h + 0.4, cq.Vector(0, 0, z0 - 0.2), cq.Vector(0, 0, 1))
    return outer.cut(inner)


def _hub_axial_range(params: BladeParams, blade: cq.Solid | None = None) -> tuple[float, float]:
    """(z_bottom, z_top) of the hub CYLINDER body.

    AUTO (``hub_height_mm`` is None): cover the blade ROOTS + ``hub_axial_margin`` each side —
    short, so a swept tip no longer drags the hub (and total depth) taller. An explicit
    ``hub_height_mm`` forces a taller hub (clamped to the root-coverage minimum).

    ``blade_hub_z_mm`` shifts the hub relative to the roots: positive places the blades higher
    on the hub (more hub below / toward the outlet). Clamped so the root section stays inside.
    """
    del blade  # kept for call-site compatibility; sizing is root-station based
    r_lo, r_hi = _root_axial_span(params)
    center = 0.5 * (r_lo + r_hi)
    root_h = r_hi - r_lo
    min_h = root_h + 2.0 * float(params.hub_axial_margin)
    if params.hub_height_mm is not None:
        h = max(float(params.hub_height_mm), min_h)
    else:
        h = min_h
    bias = float(getattr(params, "blade_hub_z_mm", 0.0) or 0.0)
    # Keep roots inside the hub: |bias| <= (h - root_h) / 2
    max_bias = max(0.0, (h - root_h) / 2.0)
    if bias > max_bias:
        bias = max_bias
    elif bias < -max_bias:
        bias = -max_bias
    return center - h / 2.0 - bias, center + h / 2.0 - bias


def _cylinder_hub(params: BladeParams, z_bottom: float, z_top: float) -> cq.Solid:
    cq = _cq()
    return cq.Solid.makeCylinder(params.hub_radius, z_top - z_bottom,
                                 cq.Vector(0, 0, z_bottom), cq.Vector(0, 0, 1))


def build_hub(params: BladeParams, z_bottom: float, z_top: float) -> cq.Solid:
    """The hub solid between z_bottom..z_top: a cylinder, optionally capped with a pointy cone or a
    rounded dome nose of height ``hub_nose_mm`` on the +Z (intake) end. Falls back to a plain
    cylinder if a nose op fails, so the impeller always builds."""
    cq = _cq()
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
    cq = _cq()
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
    ring = _shroud_solid(params)
    if ring is not None:
        fused = fused.fuse(ring).clean()
    return cq.Workplane(obj=fused)


def build_impeller_screen(params: BladeParams | None = None) -> cq.Workplane:
    """Fused impeller at ``SCREEN_N_*`` loft density (watertight + envelope, not CFD mesh).

    CFD / print-export / Assess must call ``build_impeller`` at default loft resolution.
    """
    return build_impeller(with_screen_loft(params or BladeParams()))


def build_impeller_preview(
    params: BladeParams | None = None,
    tol: float = 0.15,
    *,
    screen: bool = True,
):
    """FAST visual impeller for the live preview: tessellate ONE lofted blade + the hub, then
    rotate-copy the blade mesh around the axis — with NO boolean fuse.

    The boolean union in ``build_impeller`` dominates featured builds (a fuse of 11 featured blades
    onto the hub is ~140 s and blows the preview timeout), yet a preview only needs to LOOK right, not
    be watertight. Skipping the fuse turns ~160 s into ~6 s. Default ``screen=True`` uses
    ``with_screen_loft`` so the single blade loft is also cheap. Pass ``screen=False`` to keep
    ``params.n_span`` / ``n_chord`` (smoother LE for gold-✕ overlay / fit checks).

    Returns ``(trimesh.Trimesh, volume_mm3)``
    where volume is the accurate sum of the solids' own volumes (the meshes overlap at the blade roots,
    so the concatenated mesh's own volume would be wrong for the weight check). NOT watertight — use
    ``build_impeller`` for CFD/export where a single sealed solid is required."""
    import trimesh

    params = params or BladeParams()
    if screen:
        params = with_screen_loft(params)
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
    ring = _shroud_solid(params)
    if ring is not None:
        parts.append(_tm(ring))
        volume_mm3 += float(ring.Volume())
        mesh = trimesh.util.concatenate(parts)
    return mesh, volume_mm3


def shroud_axial_range(params: BladeParams) -> tuple[float, float] | None:
    t = float(params.shroud_thick_mm or 0.0)
    if t <= 0.0:
        return None
    z0, z1 = _tip_z_span(params)
    span = z1 - z0
    frac = min(max(float(params.shroud_height_frac or 0.0), 0.0), 1.0)
    if frac >= 1.0 - SHROUD_FULL_EPS:
        return z0, z1
    h = frac * span
    if span >= SHROUD_MIN_WALL_MM:
        h = min(max(h, SHROUD_MIN_WALL_MM), span)
    else:
        h = span
    z_le, z_te = tip_le_te_z(params)
    if z_te >= z_le:
        z_hi = z_te
        z_lo = z_te - h
    else:
        z_lo = z_te
        z_hi = z_te + h
    return (z_lo, z_hi) if z_hi >= z_lo else (z_hi, z_lo)


def tip_le_te_z(params: BladeParams) -> tuple[float, float]:
   """Axial Z of LE (`x` min) and TE (`x` max) on the tip section."""
   st = max(params.stations, key=lambda s: s.r_frac)
   r = params.hub_radius - params.root_embed
   r = r + (params.tip_radius - r) * st.r_frac
   x, pts = _section_loop(
       r=r, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg,
       thickness=st.thickness, max_camber=st.max_camber, camber_pos=st.camber_pos,
       sweep=st.sweep, skew=st.skew, le_sweep=st.le_sweep, lean_deg=st.lean_deg,
       n_chord=params.n_chord, features=Features(), le_skew=st.le_skew,
       tip_notch_count=params.tip_notch_count,
       tip_notch_depth_mm=params.tip_notch_depth_mm,
       **_thick_scale_kw(params),
   )
   if bool(getattr(params, "cylindrical_tip", True)):
       pts = _clamp_points_to_cylinder(pts, float(params.tip_radius))
   i_le = int(x.argmin())
   i_te = int(x.argmax())
   return float(pts[i_le].z), float(pts[i_te].z)


# --- LE / TE chordwise thickness bias ---
THICK_SCALE_LO = 0.5
THICK_SCALE_HI = 2.0
# Cap TE blunt to this fraction of peak half-thickness (avoids the tall TE paddle).
TE_BLUNT_FRAC = 0.10
# TE blunt only in the last this fraction of chord (keeps a short tip, not a long face lip).
TE_BLUNT_START = 0.92


def _clamp_thick_scale(v: float) -> float:
    return float(min(max(float(v), THICK_SCALE_LO), THICK_SCALE_HI))


def _section_family(params: BladeParams) -> str:
    fam = str(getattr(params, "section_family", SECTION_NACA) or SECTION_NACA).lower().strip()
    return fam if fam in SECTION_FAMILIES else SECTION_NACA


def _thick_scale_kw(params: BladeParams) -> dict[str, float | str]:
    fam = _section_family(params)
    te_raw = float(getattr(params, "te_thick_scale", 1.0) or 1.0)
    le_raw = float(getattr(params, "le_thick_scale", 1.0) or 1.0)
    if fam == SECTION_PLATE:
        # Plate LE/TE roundness is 0–1 (sharp→bullnose); do not apply NACA 0.5 floor.
        te = float(min(max(te_raw, 0.0), 1.0))
        # Full LE bullnose (legacy default 1.0) with uniform wall is a ~t/2 bead the
        # length of the blade — it fights constant thickness. When LE was left at that
        # unused default, follow TE roundness (stock sharpens both to ~0.2).
        if abs(le_raw - 1.0) < 1e-9:
            le = te
        else:
            le = float(min(max(le_raw, 0.0), 1.0))
    else:
        te = _clamp_thick_scale(te_raw)
        le = _clamp_thick_scale(le_raw)
    return dict(le_thick_scale=le, te_thick_scale=te, section_family=fam)


def le_te_thick_factors(
    x: np.ndarray, le_thick_scale: float = 1.0, te_thick_scale: float = 1.0,
) -> np.ndarray:
    """Per-point thickness multipliers that keep mid-chord near stock when only ends change.

    ``factor = 1 + (le-1)*(1-x)^3 + (te-1)*x^3`` — at x=0 → le, x=1 → te, mid barely moves.
    TE may be >1 (fattens the aft section); a separate blunt floor still closes the razor tip.
    """
    le = _clamp_thick_scale(le_thick_scale)
    te = _clamp_thick_scale(te_thick_scale)
    x = np.asarray(x, dtype=float)
    return 1.0 + (le - 1.0) * (1.0 - x) ** 3 + (te - 1.0) * x ** 3


def apply_le_te_thickness(
    x: np.ndarray, b: np.ndarray, chord: float,
    le_thick_scale: float = 1.0, te_thick_scale: float = 1.0,
) -> np.ndarray:
    """Bias NACA thickness toward LE / TE without double-fattening the mid-chord.

    Multiplicative end-weighted blend (no additive LE puff). LE/TE scales may both exceed 1
    so the nose and aft section actually thicken. TE > 1 also adds a short blunt floor in the
    last few % of chord so the NACA razor tip does not stay zero. Both 1.0 = stock NACA.
    """
    le = _clamp_thick_scale(le_thick_scale)
    te = _clamp_thick_scale(te_thick_scale)
    if abs(le - 1.0) < 1e-9 and abs(te - 1.0) < 1e-9:
        return b

    out = b * le_te_thick_factors(x, le, te)

    if te > 1.0 + 1e-9:
        # EXPERIMENTAL under stagger≠0: blunt is applied in section (a,b) before pitch, so
        # the floor is chord-normal, not TE-normal in the staggered plane. Prefer Rounded
        # plate for a true bullnose TE. Keep for printable NACA tips at moderate stagger.
        abs_b = np.abs(out)
        t_peak = float(np.max(abs_b)) if abs_b.size else 0.01 * float(chord)
        # te=1 → 0; te=2 → TE_BLUNT_FRAC * peak
        te_half = TE_BLUNT_FRAC * t_peak * (te - 1.0) / (THICK_SCALE_HI - 1.0)
        te_half = min(te_half, TE_BLUNT_FRAC * t_peak)
        span = max(1.0 - TE_BLUNT_START, 1e-6)
        w = np.clip((x - TE_BLUNT_START) / span, 0.0, 1.0)
        w = w * w
        # Upper = TE→LE (indices ≤ LE), lower = LE→TE. Matches naca4 / rounded_plate loop order.
        i_le = int(np.argmin(x))
        side = np.ones(len(x), dtype=float)
        side[i_le + 1 :] = -1.0
        mag = abs_b * (1.0 - w) + np.maximum(abs_b, te_half) * w
        orig = np.sign(out)
        orig = np.where(orig == 0.0, side, orig)
        lifted = mag > abs_b + 1e-12
        s = np.where(lifted, side, orig)
        out = s * mag
    return out


def thickness_tc_from_mm(thick_mm: float, chord_mm: float) -> float:
    """Convert absolute section thickness (mm) to NACA t/c for a given chord (mm)."""
    return float(thick_mm) / max(float(chord_mm), 1e-6)


def uniform_thickness_tc(
    thick_mm: float, chord_root: float, chord_mid: float, chord_tip: float,
) -> tuple[float, float, float]:
    """Same wall thickness (mm) at root/mid/tip → per-station t/c (chord usually grows outward)."""
    return (
        thickness_tc_from_mm(thick_mm, chord_root),
        thickness_tc_from_mm(thick_mm, chord_mid),
        thickness_tc_from_mm(thick_mm, chord_tip),
    )

# --- _clamp_points_to_cylinder (transcript, recovery) ---
def _clamp_points_to_cylinder(pts: list[cq.Vector], radius: float) -> list[cq.Vector]:
    """Measurement helper: pull XY onto the cylinder (Z unchanged). Not used for loft wires."""
    R = float(radius)
    if R <= 0.0:
        return pts
    out: list[cq.Vector] = []
    for v in pts:
        rho = math.hypot(v.x, v.y)
        if rho > R and rho > 0.0:
            s = R / rho
            out.append(cq.Vector(v.x * s, v.y * s, v.z))
        else:
            out.append(v)
    return out


# --- real feature fns (deduped, from transcript, recovery) ---
def apply_sickle(params: BladeParams, tip_mm: float) -> BladeParams:
    """Forward-sweep the leading edge in the rotation plane (LE-only ``le_skew``).

    Hub stays 0, mid is 40% of ``tip_mm``, tip is ``tip_mm``. Extra stations (winglet / tip-round)
    interpolate that recipe on ``r_frac``. ``tip_mm <= 0`` is a no-op. Mutates and returns ``params``.
    """
    tip_mm = float(tip_mm)
    if tip_mm <= 0.0:
        return params
    for s in params.stations:
        s.le_skew = float(np.interp(s.r_frac, [0.0, 0.5, 1.0], [0.0, 0.40 * tip_mm, tip_mm]))
    return params


def apply_notched_tips(params: BladeParams) -> BladeParams:
    """Stamp three cut-only TE bites in the outer 12% of span.

    Sets ``tip_notch_count`` / ``tip_notch_depth_mm`` to the fixed recipe. Idempotent.
    Mutates and returns ``params``.
    """
    params.tip_notch_count = NOTCH_COUNT
    params.tip_notch_depth_mm = NOTCH_DEPTH_MM
    return params


def _trim_blade_to_tip_cylinder(blade: cq.Solid, tip_radius: float) -> cq.Solid:
    """Intersect the lofted blade with a cylinder of radius ``tip_radius`` (true cylindrical tip)."""
    R = float(tip_radius)
    if R <= 0.0:
        return blade
    bb = blade.BoundingBox()
    pad = 5.0
    z0 = float(bb.zmin) - pad
    h = float(bb.zmax - bb.zmin) + 2.0 * pad
    if h <= 0.0:
        return blade
    cyl = cq.Solid.makeCylinder(R, h, cq.Vector(0, 0, z0), cq.Vector(0, 0, 1))
    cut = blade.intersect(cyl)
    solids = list(cut.Solids()) if hasattr(cut, "Solids") else []
    if not solids:
        # Some CadQuery builds return a single Solid from intersect.
        if isinstance(cut, cq.Solid) or cut.ShapeType() == "Solid":
            return cut
        return blade
    return max(solids, key=lambda s: abs(float(s.Volume())))
