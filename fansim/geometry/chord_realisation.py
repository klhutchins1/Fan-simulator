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

# Loft chord may exceed the measured target near the tip; keep headroom above recipe BOUNDS.
_LOFT_CHORD_BOUNDS = (5.0, 90.0)
_DEFAULT_ITERS = 2
_MIN_MEAS_MM = 2.0


def _station_measure_fracs(params) -> list[float | None]:
    tip = float(params.tip_radius)
    r0 = float(params.hub_radius) - float(params.root_embed)
    span = tip - r0
    if tip <= 0.0 or span <= 0.0:
        return [float(s.r_frac) for s in params.stations]
    out: list[float | None] = []
    for s in params.stations:
        f = (r0 + span * float(s.r_frac)) / tip
        # Tip wire sits on the cut cylinder; measure just inboard (same as fit_recipe tip @ 0.99).
        if f >= 0.995:
            out.append(0.99)
        elif f < 0.47:
            # Inside / at the hub cup — no reliable blade section.
            out.append(None)
        else:
            out.append(float(f))
    return out


def measure_station_chords(params) -> list[float | None]:
    """Build one blade (already chord-realised path) and measure chord at each station radius."""
    from fansim.geometry.blade import build_blade_solid

    fracs = _station_measure_fracs(params)
    uniq = tuple(sorted({round(f, 4) for f in fracs if f is not None}))
    if not uniq:
        return [None] * len(params.stations)
    with tempfile.TemporaryDirectory() as td:
        stl = Path(td) / "blade.stl"
        export_stl(build_blade_solid(params, _chord_realized=True), stl)
        rows = measure_sections(stl, uniq)
    by_f = {round(r["r_frac"], 4): r for r in rows}
    out: list[float | None] = []
    for f in fracs:
        if f is None:
            out.append(None)
            continue
        r = by_f.get(round(f, 4))
        if r is None or int(r.get("n_blades") or 0) <= 0:
            out.append(None)
            continue
        out.append(float(r["chord_mm"]))
    return out


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
    return loft


def prepare_loft_chords(params):
    """Return params whose station ``chord`` values are loft chords realizing measured targets."""
    if not bool(getattr(params, "cylindrical_tip", True)):
        return params
    return with_loft_chords(params, loft_chords_for_measured_targets(params))


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
    return replace(deepcopy(params), stations=stations)
