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


def test_evaluate_candidate_uses_full_loft_not_screen(tmp_path, monkeypatch):
    """CFD path must not silently drop loft resolution (§13.13)."""
    seen = {"n_span": None}

    real_build = obj_mod.build_impeller

    def tracking_build(params):
        seen["n_span"] = int(params.n_span)
        seen["n_chord"] = int(params.n_chord)
        raise RuntimeError("stop-after-loft-check")

    monkeypatch.setattr(obj_mod, "build_impeller", tracking_build)
    from fansim.optimize.search_space import stock_blade_flat, blade_from_flat
    from fansim.geometry.features import Features
    from dataclasses import replace

    params = replace(blade_from_flat(stock_blade_flat("a12x25"), Features()), tip_radius=50.0)
    res = evaluate_candidate(params, tmp_path / "full", procs=1, iters=1)
    assert res.feasible is False
    assert "geometry failed" in res.reason
    assert seen["n_span"] == 18
    assert seen["n_chord"] == 60
    # Sanity: full builder still exists for real CFD.
    assert callable(real_build)
