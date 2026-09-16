"""Screen loft resolution (§13.13): coarse STL for gates/preview, full for CFD."""

from __future__ import annotations

from fansim.geometry.blade import (
    SCREEN_N_CHORD,
    SCREEN_N_SPAN,
    BladeParams,
    build_impeller,
    build_impeller_screen,
    with_screen_loft,
)
from fansim.geometry.export import export_stl, watertight_report
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize import objectives as obj_mod


def test_with_screen_loft_does_not_mutate_and_lowers_counts():
    p = BladeParams()
    assert p.n_span == 18 and p.n_chord == 60
    s = with_screen_loft(p)
    assert s.n_span == SCREEN_N_SPAN
    assert s.n_chord == SCREEN_N_CHORD
    assert p.n_span == 18 and p.n_chord == 60


def test_build_impeller_screen_watertight_envelope(tmp_path):
    p = BladeParams(n_blades=7, tip_radius=54.0)
    screen = build_impeller_screen(p)
    stl = export_stl(screen, tmp_path / "screen.stl")
    rep = watertight_report(stl)
    assert rep.ok
    (xmin, ymin, _), (xmax, ymax, _) = rep.bounds_mm
    dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
    assert abs(dia - 2.0 * p.tip_radius) < 1.5  # cylindrical tip ≈ tip_radius


def test_preview_tip_round_keeps_screen_span():
    """§13.22: tip-round inserts stations; preview must not bump loft to 30."""
    from copy import deepcopy

    from fansim.geometry.blade import apply_tip_shape, build_blade_solid

    p = with_screen_loft(apply_tip_shape(deepcopy(BladeParams()), tip_round=0.85))
    assert len(p.stations) > 3
    assert p.n_span == SCREEN_N_SPAN
    # Spy via interp: build_blade_solid would raise if we force a hook — instead check
    # that screen density is preserved by comparing open tip of screen vs bumped would differ
    # only in cost. Direct: call build and ensure it completes; assert n_span used via monkeypatch.
    used = {}

    import fansim.geometry.blade as blade_mod

    real_interp = blade_mod._interp_stations

    def tracking_interp(params, n_span):
        used["n_span"] = int(n_span)
        return real_interp(params, n_span)

    blade_mod._interp_stations = tracking_interp
    try:
        build_blade_solid(p)
    finally:
        blade_mod._interp_stations = real_interp
    assert used["n_span"] == SCREEN_N_SPAN


def test_full_loft_tip_round_still_bumps_span():
    """CFD/print path keeps the ≥30 bump when tip-round adds stations."""
    from copy import deepcopy

    from fansim.geometry.blade import apply_tip_shape, build_blade_solid
    import fansim.geometry.blade as blade_mod

    p = apply_tip_shape(deepcopy(BladeParams()), tip_round=0.85)
    assert len(p.stations) > 3
    assert p.n_span == 18
    used = {}
    real_interp = blade_mod._interp_stations

    def tracking_interp(params, n_span):
        used["n_span"] = int(n_span)
        return real_interp(params, n_span)

    blade_mod._interp_stations = tracking_interp
    try:
        build_blade_solid(p)
    finally:
        blade_mod._interp_stations = real_interp
    assert used["n_span"] >= 30

