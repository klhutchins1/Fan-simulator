# RECONSTRUCTED 2026-09-12: my 420-line base + Cursor blade.py edits replayed + shroud_is_full/SHROUD_FULL_EPS/shroud_axial_range/tip_le_te_z spliced. 752 lines vs ~745 target; VERIFY against any real copy.
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
NOTCH_SPAN_SECTIONS = 48
NOTCH_COUNT = 3
NOTCH_DEPTH_MM = 1.5
NOTCH_START_FRAC = 0.88  # outer-span TE bites; hub is untouched
NOTCH_SPAN_SECTIONS = 48


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
    # Chordwise thickness bias (global): scale local NACA thickness near LE / TE.
    # 1.0 = unchanged; typical range 0.5–1.5. Thickness root/mid/tip still set max thickness.
    # Ignored when section_family == "plate".
    le_thick_scale: float = 1.0
    te_thick_scale: float = 1.0
    # Airfoil family: "naca" (default) or "plate" (constant-t stadium / bullnose both ends).
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
    """Build the closed 3D loop of one airfoil section wrapped onto the cylinder at radius ``r``.

    The airfoil is defined on the cylindrical stream-surface of radius ``r`` (standard for
    axial turbomachinery): chordwise/thickness coords are pitched by the stagger angle into
    circumferential (arc) and axial directions, the circumferential distance is mapped to an
    ARC ANGLE about the axis, and the whole section is placed at angular position ``lean_deg``.
    Because lean_deg varies along the span, the blade sweeps/wraps circumferentially and can
    overlap the neighbouring blade — the shape real fans have, which a straight radial stack
    (lean=0) cannot make.
    """
    loop = section_loop_2d(section_family, max_camber=max_camber, camber_pos=camber_pos,
                          thickness=thickness, n_points=n_chord)
    # Drop the explicit closing duplicate; the wire is closed by makePolygon(close=True).
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]

    beta = np.radians(stagger_deg)
    cb, sb = np.cos(beta), np.sin(beta)

    x = loop[:, 0]  # chord fraction, 0=LE .. 1=TE
    a = (x - 0.5) * chord  # chordwise distance from mid-chord
    b = loop[:, 1] * chord  # thickness-wise distance
    b = apply_le_te_thickness(x, b, chord, le_thick_scale, te_thick_scale)
    if features.active:
        a, b = apply_features(x, a, b, r_frac, chord, features)
    # Leading-edge weight: 1 at the LE (x=0), 0 by mid-chord (x>=0.5).
    w_le = np.where(x < 0.5, 0.5 * (1.0 + np.cos(2.0 * np.pi * x)), 0.0)
    t = a * cb - b * sb + skew + le_skew * w_le  # circumferential (tangential) distance, mm
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



def _section_loop(r, r_frac, chord, stagger_deg, thickness, max_camber, camber_pos,
                  sweep, skew, le_sweep, lean_deg, n_chord, features,
                  le_skew=0.0, tip_notch_count=0, tip_notch_depth_mm=0.0):
    """RECOVERY BRIDGE (2026-09-12): (chord-fraction x array, 3D section pts).
    The original _section_loop was never captured whole in any transcript; this mirrors
    _section_points_3d and additionally returns the chord-fraction array used to find LE/TE.
    x[i] corresponds to pts[i] (same naca4 loop order). Verify against a real copy."""
    loop = naca4(max_camber, camber_pos, thickness, n_chord)
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    x = loop[:, 0]
    pts = _section_points_3d(
        r=r, r_frac=r_frac, chord=chord, stagger_deg=stagger_deg, thickness=thickness,
        max_camber=max_camber, camber_pos=camber_pos, sweep=sweep, skew=skew,
        le_sweep=le_sweep, lean_deg=lean_deg, n_chord=n_chord, features=features,
        le_skew=le_skew, tip_notch_count=tip_notch_count, tip_notch_depth_mm=tip_notch_depth_mm)
    return x, pts


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


def build_blade_solid(params: BladeParams) -> cq.Solid:
    """Loft one blade solid from hub to tip (raising loft resolution for active features)."""
    cq = _cq()
    n_span = params.features.required_span_sections(params.n_span)
    # Extra inserted stations (winglet shoulder / tip rounding) live in the outer span; raise the
    # spanwise loft resolution so that curved tip reads smoothly instead of as a few facets.
    if len(params.stations) > 3:
        n_span = max(n_span, 30)
    if int(params.tip_notch_count or 0) > 0:
        n_span = max(n_span, NOTCH_SPAN_SECTIONS)
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
        tip_notch_depth_mm=params.tip_notch_depth_mm)
    zs = [p.z for p in pts]
    return min(zs), max(zs)


def tip_section_points(params: BladeParams) -> list[Vec]:
    """The outermost control station's section loop — the chord the tip ring must swallow."""
    st = max(params.stations, key=lambda s: s.r_frac)
    r = params.hub_radius - params.root_embed
    r = r + (params.tip_radius - r) * st.r_frac
    return _section_points_3d(
        r=r, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg,
        thickness=st.thickness, max_camber=st.max_camber, camber_pos=st.camber_pos,
        sweep=st.sweep, skew=st.skew, le_sweep=st.le_sweep, lean_deg=st.lean_deg,
        n_chord=params.n_chord, features=Features(), le_skew=st.le_skew,
    )


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
    z0, z1 = _tip_z_span(params)
    h = max(z1 - z0, 1.0)
    outer = cq.Solid.makeCylinder(r_out, h, cq.Vector(0, 0, z0), cq.Vector(0, 0, 1))
    inner = cq.Solid.makeCylinder(r_in, h + 0.4, cq.Vector(0, 0, z0 - 0.2), cq.Vector(0, 0, 1))
    return outer.cut(inner)


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
   )
   if bool(getattr(params, "cylindrical_tip", True)):
       pts = _clamp_points_to_cylinder(pts, float(params.tip_radius))
   i_le = int(x.argmin())
   i_te = int(x.argmax())
   return float(pts[i_le].z), float(pts[i_te].z)


# --- spliced (recovery 2026-09-12) ---
TE_BLUNT_FRAC = 0.18


# --- RECONSTRUCTED 2026-09-12 (never captured in any transcript; from test contract; VERIFY) ---
def le_te_thick_factors(x, le_scale=1.0, te_scale=1.0):
    """Per-point thickness scale: `le_scale` weighted toward the LE (x->0), `te_scale` toward the
    TE (x->1), unity by mid-chord. Returns 1.0 everywhere when both scales are 1.0."""
    import numpy as np
    x = np.asarray(x, dtype=float)
    w_le = np.clip(1.0 - 2.0 * x, 0.0, 1.0)
    w_te = np.clip(2.0 * x - 1.0, 0.0, 1.0)
    return 1.0 + w_le * (float(le_scale) - 1.0) + w_te * (float(te_scale) - 1.0)


def apply_le_te_thickness(x, b, chord, le_scale=1.0, te_scale=1.0):
    """Scale the thickness-wise coordinate array `b` toward the LE/TE. No-op when both scales are 1.0."""
    import numpy as np
    return np.asarray(b, dtype=float) * le_te_thick_factors(x, le_scale, te_scale)


# --- _thick_scale_kw (transcript, recovery) ---
def _thick_scale_kw(params: BladeParams) -> dict[str, float]:
    return dict(
        le_thick_scale=_clamp_thick_scale(getattr(params, "le_thick_scale", 1.0) or 1.0),
        te_thick_scale=_clamp_thick_scale(getattr(params, "te_thick_scale", 1.0) or 1.0),
        section_family=_section_family(params),
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


# --- _trim_blade_to_tip_cylinder (transcript, recovery) ---
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


# --- _clamp_thick_scale (recovery) ---
def _clamp_thick_scale(v: float) -> float:
    return float(min(max(float(v), THICK_SCALE_LO), THICK_SCALE_HI))


# --- _section_family (recovery) ---
def _section_family(params: BladeParams) -> str:
    fam = str(getattr(params, "section_family", SECTION_NACA) or SECTION_NACA).lower().strip()
    return fam if fam in SECTION_FAMILIES else SECTION_NACA

# --- THICK_SCALE_LO (recovery cascade) ---
THICK_SCALE_LO = 0.5

# --- THICK_SCALE_HI (recovery cascade) ---
THICK_SCALE_HI = 1.5
