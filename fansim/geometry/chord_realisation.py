"""Map station ``chord`` (measured / cylinder-cut target) to loft chord under ``cylindrical_tip``.

Planar-tangent sections near the tip put LE/TE corners outside ``tip_radius``; the cylindrical
trim then shortens the measurable chord. Recipe fit used to inflate YAML chord to compensate.
With this helper, YAML/station ``chord`` means the *measured* chord and the loft uses a larger
internal value found by a short build→measure fixed-point (same update as the old fit step).
"""

from __future__ import annotations

import tempfile
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np

from fansim.geometry.export import export_stl
from fansim.validation.section_compare import measure_sections

CHORD_BASIS_MEASURED = "measured"
CHORD_BASIS_LOFT = "loft"
CHORD_BASES = (CHORD_BASIS_MEASURED, CHORD_BASIS_LOFT)

# Loft chord may exceed the measured target near the tip; keep headroom above recipe BOUNDS.
_LOFT_CHORD_BOUNDS = (5.0, 90.0)
_DEFAULT_ITERS = 2
_MIN_MEAS_MM = 2.0


HUB_MEASURE_MARGIN_MM = 4.1


def _station_measure_fracs(params) -> list[float | None]:
    from fansim.geometry.blade import radius_at_r_frac, station_root_radius

    tip = float(params.tip_radius)
    r0 = station_root_radius(params)
    span = tip - r0
    if tip <= 0.0 or span <= 0.0:
        return [float(s.r_frac) for s in params.stations]
    # Sections closer than HUB_MEASURE_MARGIN_MM to the hub merge into the hub cup. This was a
    # hard-coded 0.47 (the A12x25: (21.5 + 4.1) / 54.5); derive it per design so larger-hub fans
    # don't measure inside the hub annulus (QA 2026-10-08, roadmap §23.34).
    hub_cut = (float(params.hub_radius) + HUB_MEASURE_MARGIN_MM) / tip
    out: list[float | None] = []
    for s in params.stations:
        f = radius_at_r_frac(params, float(s.r_frac)) / tip
        # Tip wire sits on the cut cylinder; measure just inboard (same as fit_recipe tip @ 0.99).
        if f >= 0.995:
            out.append(0.99)
        elif f < hub_cut:
            # Inside / at the hub cup — no reliable blade section.
            out.append(None)
        else:
            out.append(float(f))
    return out


def measure_station_rows(params, *, clip: bool = True) -> list[dict | None]:
    """Build one blade (already chord-realised path) and read the section at each station radius."""
    from fansim.geometry.blade import _hub_axial_range, build_blade_solid, clip_blade_below

    fracs = _station_measure_fracs(params)
    uniq = tuple(sorted({round(f, 4) for f in fracs if f is not None}))
    if not uniq:
        return [None] * len(params.stations)
    with tempfile.TemporaryDirectory() as td:
        stl = Path(td) / "blade.stl"
        # Untrimmed: all measured radii are <= 0.99·tip, where the tip trim removes nothing, so
        # skip the expensive boolean and cut at the true tip radius (the mesh's own outer radius
        # is larger untrimmed). Same chords within 0.05 mm on the 2026-10-08 A/B (roadmap §23.17).
        blade = build_blade_solid(params, _chord_realized=True, _trim_tip=False)
        # Measure what ships: the build cuts every blade at the hub's motor face (QA-16), which
        # took 3-16 % off lt120's chord that an unclipped measurement never saw (QA-30, 27.4).
        if clip:
            blade = clip_blade_below(params, blade, _hub_axial_range(params)[0])
        export_stl(blade, stl)
        rows = measure_sections(stl, uniq, tip_radius_mm=float(params.tip_radius))
    by_f = {round(r["r_frac"], 4): r for r in rows}
    out: list[dict | None] = []
    for f in fracs:
        r = None if f is None else by_f.get(round(f, 4))
        out.append(r if r is not None and int(r.get("n_blades") or 0) > 0 else None)
    return out


def measure_station_chords(params) -> list[float | None]:
    """Build one blade (already chord-realised path) and measure chord at each station radius."""
    return [None if r is None else float(r["chord_mm"]) for r in measure_station_rows(params)]


# Disk cache for the build→measure fixed point (roadmap §23.17). Preview, Assess and Export of the
# same design each run in a fresh worker process, so the in-process cache never hit and every one
# re-ran the iteration. Keyed on the full params + iteration count + LOFT_CACHE_VERSION (bump it
# whenever the measurement/update rule changes). FANSIM_CACHE_DIR overrides the location.
LOFT_CACHE_VERSION = 5   # 2: untrimmed builds at the true tip radius; 3: hub-face clipped; 4-5: clip camber/stagger


def _cache_dir() -> Path:
    import os

    root = os.environ.get("FANSIM_CACHE_DIR")
    base = Path(root) if root else Path.home() / ".cache" / "fansim"
    return base / "loft_chords"


def _cache_key(params, n_iter: int) -> str:
    import hashlib
    import json
    from dataclasses import asdict

    blob = json.dumps({"v": LOFT_CACHE_VERSION, "n_iter": int(n_iter), "p": asdict(params)},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _cache_get(key: str, n: int) -> list[float] | None:
    import json

    try:
        vals = json.loads((_cache_dir() / f"{key}.json").read_text(encoding="utf-8"))
        return [float(v) for v in vals] if len(vals) == n else None
    except (OSError, ValueError, TypeError):
        return None


def _cache_put(key: str, loft: list[float]) -> None:
    import json
    import os

    try:
        d = _cache_dir()
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / f"{key}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps([float(v) for v in loft]), encoding="utf-8")
        os.replace(tmp, d / f"{key}.json")
    except OSError:
        pass  # cache is an optimisation only


def loft_chords_for_measured_targets(params, n_iter: int = _DEFAULT_ITERS) -> list[float]:
    """Return per-station loft chords that realize ``station.chord`` as measured chord.

    ``params.stations[i].chord`` is the *target measured* chord (mm). The returned list is what
    the loft wires should use. No-op copy of targets when ``cylindrical_tip`` is False.
    Measurement builds always use full loft density (not screen ``n_span``), so preview/screen
    callers get the same loft chords as CFD/export.
    """
    targets = [float(s.chord) for s in params.stations]
    if not bool(getattr(params, "cylindrical_tip", True)):
        return list(targets)
    key = _cache_key(params, n_iter)
    cached = _cache_get(key, len(targets))
    if cached is not None:
        return cached

    # Screen loft lowers n_span; measuring on that mesh under-reads tip chord and under-compensates.
    from fansim.geometry.blade import SCREEN_N_SPAN

    measure_params = params
    if int(params.n_span) <= SCREEN_N_SPAN:
        measure_params = replace(params, n_span=18, n_chord=max(int(params.n_chord), 60))

    loft = list(targets)
    lo, hi = _LOFT_CHORD_BOUNDS
    for _ in range(max(1, int(n_iter))):
        # Scale thickness/camber with loft so fixed-point measures the same absolute wall as
        # prepare_loft_chords (YAML fractions are of the measured target, not the loft chord).
        trial = with_loft_chords(measure_params, loft)
        built = measure_station_chords(trial)
        for i, tgt in enumerate(targets):
            m = built[i]
            if m is None or m < _MIN_MEAS_MM or tgt <= 0.0:
                continue
            loft[i] = float(np.clip(loft[i] * tgt / m, lo, hi))
    _cache_put(key, loft)
    return loft


def prepare_loft_chords(params):
    """Return params whose station ``chord`` values are loft chords realizing measured targets.

    Legacy ``chord_basis="loft"`` params already hold loft chords and are returned unchanged.
    """
    if not bool(getattr(params, "cylindrical_tip", True)):
        return params
    basis = str(getattr(params, "chord_basis", CHORD_BASIS_MEASURED) or CHORD_BASIS_MEASURED)
    if basis not in CHORD_BASES:
        raise ValueError(f"chord_basis must be one of {CHORD_BASES}, got {basis!r}")
    if basis == CHORD_BASIS_LOFT:
        return params
    loft = with_loft_chords(params, loft_chords_for_measured_targets(params))
    return correct_clipped_sections(loft, params)


# Hub-face clip correction (Kimball 2026-10-13, roadmap 27.4 / QA-32). Where the motor-face cut
# reaches a station, restoring its chord isn't enough: the cut section is a truncated airfoil whose
# camber read 0.005-0.011 low and stagger up to 1.8 deg off. Nudge the loft camber/stagger there until
# the cut section reads like the designed one through the same estimator (its bias cancels).
CLIP_REACHED_MM = 0.1      # a station counts as reached when the cut removes this much chord,
CLIP_REACHED_CAMBER = 0.001  # or moves its camber reading this much,
CLIP_REACHED_STAGGER_DEG = 0.2  # or its stagger this much
_CLIP_ITERS = 3
_CLIP_DAMPING = 0.8


def _cut_changes(cut: dict, whole: dict) -> bool:
    """True when the hub-face cut changes this section's reading: its chord, or its camber/stagger.

    Stock's cut removes < 0.1 mm of chord at its inner stations yet trims the trailing edge at an
    angle, which moved its camber reading by 0.005-0.007.
    """
    return (float(whole["chord_mm"]) - float(cut["chord_mm"]) > CLIP_REACHED_MM
            or abs(float(whole["camber_ratio"]) - float(cut["camber_ratio"])) > CLIP_REACHED_CAMBER
            or abs(float(whole["stagger_deg"]) - float(cut["stagger_deg"])) > CLIP_REACHED_STAGGER_DEG)


def _designed_reading(design, station, r_mm: float, omega: int) -> dict | None:
    """The station's own section, wrapped at r with no lean/sweep, read by the section estimator."""
    from fansim.geometry.blade import _section_points_3d, _thick_scale_kw
    from fansim.geometry.features import Features
    from fansim.validation.section_compare import _measure_loop

    kw = _thick_scale_kw(design)
    kw["wrap"] = True
    pts = _section_points_3d(
        r=r_mm, r_frac=station.r_frac, chord=station.chord, stagger_deg=station.stagger_deg,
        thickness=station.thickness, max_camber=station.max_camber, camber_pos=station.camber_pos,
        sweep=0.0, skew=0.0, le_sweep=0.0, lean_deg=0.0, n_chord=max(int(design.n_chord), 60),
        features=Features(), **kw)
    return _measure_loop(np.array([[v.x, v.y, v.z] for v in pts]), r_mm, omega, 1)


def correct_clipped_sections(loft, design):
    """``loft`` with camber/stagger corrected at stations the hub-face cut reaches (else unchanged).

    Only wrapped, clipped designs that actually hang below the hub face pay for the extra builds.
    """
    from fansim.geometry.blade import blade_hang_below_hub_mm

    if (str(getattr(design, "section_wrap", "planar")) != "cylinder"
            or not bool(getattr(design, "clip_below_hub", True))
            or blade_hang_below_hub_mm(loft) <= 0.0):
        return loft
    key = "clip_" + _cache_key(design, _CLIP_ITERS)
    cached = _cache_get(key, 2 * len(loft.stations))
    if cached is not None:
        return _with_camber_stagger(loft, cached[0::2], cached[1::2])
    cut = measure_station_rows(loft)
    whole = measure_station_rows(loft, clip=False)
    reached = [c is not None and w is not None and _cut_changes(c, w) for c, w in zip(cut, whole)]
    cam = [float(s.max_camber) for s in loft.stations]
    stag = [float(s.stagger_deg) for s in loft.stations]
    if any(reached):
        targets = [_designed_reading(design, s, float(c["r_mm"]), int(c.get("omega_sign", 1)))
                   if hit else None for s, c, hit in zip(design.stations, cut, reached)]
        for _ in range(_CLIP_ITERS):
            for i, (hit, tgt, row) in enumerate(zip(reached, targets, cut)):
                if not hit or tgt is None or row is None or float(row["camber_ratio"]) <= 1e-6:
                    continue
                ratio = float(np.clip(float(tgt["camber_ratio"]) / float(row["camber_ratio"]),
                                      0.5, 2.0))
                cam[i] *= 1.0 + _CLIP_DAMPING * (ratio - 1.0)
                stag[i] += _CLIP_DAMPING * (float(tgt["stagger_deg"]) - float(row["stagger_deg"]))
            cut = measure_station_rows(_with_camber_stagger(loft, cam, stag))
    _cache_put(key, [v for pair in zip(cam, stag) for v in pair])
    return _with_camber_stagger(loft, cam, stag)


def _with_camber_stagger(params, cam, stag):
    stations = [replace(s, max_camber=float(c), stagger_deg=float(g))
                for s, c, g in zip(params.stations, cam, stag)]
    return replace(deepcopy(params), stations=stations)


def with_loft_chords(params, loft_chords: list[float]):
    """Deep copy of ``params`` whose station ``chord`` fields are the loft values.

    ``thickness`` and ``max_camber`` are fractions of the *measured* chord in the recipe. When the
    loft chord is longer, scale those fractions down so absolute wall / camber height stay put.
    """
    if len(loft_chords) != len(params.stations):
        raise ValueError(
            f"loft_chords length {len(loft_chords)} != n_stations {len(params.stations)}")
    stations = []
    for i, s in enumerate(params.stations):
        loft = float(loft_chords[i])
        tgt = float(s.chord)
        scale = (tgt / loft) if loft > 1e-9 else 1.0
        stations.append(replace(
            s,
            chord=loft,
            thickness=float(s.thickness) * scale,
            max_camber=float(s.max_camber) * scale,
        ))
    # The result holds loft chords, so mark it: preparing it again is then a no-op.
    return replace(deepcopy(params), stations=stations, chord_basis=CHORD_BASIS_LOFT)
