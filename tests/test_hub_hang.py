"""Blades may hang at most 2 mm below the hub's motor face; under that, the hub-face cut is corrected.

Kimball 2026-10-13 (roadmap 27.4 / QA-32): 20 % of optimizer designs hang below the hub face (median
2.5 mm, worst 13 mm) and the cut there leaves camber 0.005-0.011 below the slider. Limit: 2 mm.
"""
from __future__ import annotations

import dataclasses
import json
import tempfile
from pathlib import Path

import pytest

from fansim.geometry import build_impeller
from fansim.geometry.blade import (
    MAX_HANG_BELOW_HUB_MM,
    _section_points_3d,
    _thick_scale_kw,
    blade_hang_below_hub_mm,
    validate_blade_params,
)
from fansim.geometry.chord_realisation import _station_measure_fracs
from fansim.geometry.config import load_blade_params
from fansim.geometry.export import export_stl
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.validation.section_compare import _measure_loop, measure_sections

DATA = json.loads((Path(__file__).parent / "data" / "hub_hang_designs.json").read_text())


def _design(name, **over):
    d = DATA[name]
    return dataclasses.replace(blade_from_flat(d["flat"], Features(**d["features"])), **over)


def test_limit_is_two_mm():
    assert MAX_HANG_BELOW_HUB_MM == 2.0


def test_hang_is_measured_from_the_sections_as_designed():
    # As designed (station chords). The realised loft hangs ~1.6x further: the chord realisation
    # lengthens the section to make up for what the cut removes (QA r9 measured that loft).
    assert blade_hang_below_hub_mm(_design("S2_0176")) == pytest.approx(2.57, abs=0.05)
    assert blade_hang_below_hub_mm(_design("S1_0218")) == pytest.approx(1.10, abs=0.05)
    assert blade_hang_below_hub_mm(load_blade_params("config/problems/a12x25_reference.yaml")) < 1.5


def test_clipped_preview_does_not_hang_when_designed_te_does():
    """Preview/Fit clip at the hub face, so the mesh Kimball sees is flush even when the
    designed trailing edge (the hang check) is past the 2 mm limit."""
    from fansim.cockpit.placement import _blade_z_bounds
    from fansim.geometry.blade import _hub_axial_range

    p = _design("S2_0176")
    assert blade_hang_below_hub_mm(p) > MAX_HANG_BELOW_HUB_MM
    z_face = _hub_axial_range(p)[0]
    blo, _ = _blade_z_bounds(p)
    assert blo == pytest.approx(z_face, abs=0.02)


def test_fit_envelope_grows_hub_until_designed_hang_fits():
    """Fit + Scale used clipped depth, so they never saw designed hang and never grew the hub."""
    from fansim.cockpit.placement import fit_envelope
    from fansim.fan_spec import get_fan_spec
    from fansim.optimize.search_space import stock_blade_flat

    spec = get_fan_spec("a12x25")
    feat = Features()
    flat = {
        **stock_blade_flat("a12x25"),
        "hub_height": 15.0,
        "chord_root": 50.0,
        "stagger_root": 11.0,
    }
    before = blade_from_flat(flat, feat)
    assert blade_hang_below_hub_mm(before) > MAX_HANG_BELOW_HUB_MM
    res = fit_envelope(flat, spec, features=feat, max_depth_mm=35.0)
    after = blade_from_flat(res.flat, feat)
    assert blade_hang_below_hub_mm(after) <= MAX_HANG_BELOW_HUB_MM
    validate_blade_params(after)


def test_a_design_hanging_past_the_limit_is_refused_plainly():
    with pytest.raises(ValueError, match="below the hub"):
        validate_blade_params(_design("S2_0176"))                              # 2.6 mm: refused
    validate_blade_params(_design("S1_0400"))                                  # 1.6 mm: allowed
    validate_blade_params(load_blade_params("config/problems/a12x25_reference.yaml"))


def test_old_planar_saves_and_unclipped_blades_are_not_refused():
    validate_blade_params(_design("S2_0176", section_wrap="planar"))   # old saves rebuild as scored
    validate_blade_params(_design("S2_0176", clip_below_hub=False))    # no motor-face cut, no limit


def test_optimizer_treats_overhang_as_early_infeasible(tmp_path, monkeypatch):
    """Roadmap 27.8: a hang past 2 mm is infeasible before CAD/CFD, not a crash.

    R1.7 scores the print hub, so pick a grok r16 design that still hangs there
    (S2_0176's auto-hub 2.6 mm hang drops to 0.4 mm once the hub grows below).
    """
    from fansim.optimize.objectives import evaluate_candidate
    from tests.test_one_hub import _r16

    def boom(*_a, **_k):
        raise AssertionError("must not build CAD for a hang refusal")

    monkeypatch.setattr("fansim.optimize.objectives.build_impeller", boom)
    monkeypatch.setattr("fansim.optimize.objectives.export_stl", boom)
    result = evaluate_candidate(_r16("S1_0006"), workdir=tmp_path)
    assert result.feasible is False
    assert "below the hub" in (result.reason or "")


def test_preview_worker_refuses_overhang(tmp_path):
    """27.8: the isolated Preview worker keeps the hang sentence (stderr_tail=400)."""
    from fansim.geometry.isolated import build_stl_isolated
    from fansim.optimize.search_space import blade_to_flat

    p = _design("S2_0176")
    with pytest.raises(RuntimeError, match="below the hub"):
        build_stl_isolated(blade_to_flat(p), p.features, tmp_path / "hang.stl",
                           timeout=60, preview=True)


def _analytic(p, st, r_mm, omega, n):
    kw = _thick_scale_kw(p)
    kw["wrap"] = True
    pts = _section_points_3d(
        r=r_mm, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg, thickness=st.thickness,
        max_camber=st.max_camber, camber_pos=st.camber_pos, sweep=0.0, skew=0.0, le_sweep=0.0,
        lean_deg=0.0, n_chord=60, features=Features(), **kw)
    import numpy as np

    return _measure_loop(np.array([[v.x, v.y, v.z] for v in pts]), r_mm, omega, n)


def test_clip_reached_station_keeps_its_camber_and_angle():
    """QA-32: where the hub-face cut reaches, chord was restored but camber read 0.005-0.011 low and
    stagger up to 1 deg off. The realisation now corrects camber and stagger there too (V1 rule)."""
    p = _design("S8_0056", n_blades=2)   # 1.96 mm: the worst allowed hang
    fr = _station_measure_fracs(p)
    pairs = [(f, s) for f, s in zip(fr, p.stations) if f is not None]
    with tempfile.TemporaryDirectory() as td:
        stl = Path(td) / "i.stl"
        export_stl(build_impeller(p), stl)
        rows = measure_sections(stl, [f for f, _ in pairs])
    for (_, s), r in zip(pairs, rows):
        a = _analytic(p, s, r["r_mm"], int(r.get("omega_sign", 1)), int(r["n_blades"]))
        assert r["chord_mm"] == pytest.approx(s.chord, rel=0.03), (s.r_frac, r["chord_mm"])
        assert r["camber_ratio"] == pytest.approx(a["camber_ratio"], abs=0.005), (s.r_frac, r, a)
        assert r["stagger_deg"] == pytest.approx(a["stagger_deg"], abs=1.5), (s.r_frac, r, a)


def test_stock_sections_read_as_designed_despite_its_1_mm_hang():
    """Stock's cut removes < 0.1 mm of chord at its inner stations but trims the trailing edge at an
    angle, which moved the camber reading 0.005-0.007. A station counts as reached when the cut changes
    its reading at all, not only its chord."""
    p = dataclasses.replace(load_blade_params("config/problems/a12x25_reference.yaml"), n_blades=2)
    fr = _station_measure_fracs(p)
    pairs = [(f, s) for f, s in zip(fr, p.stations) if f is not None]
    with tempfile.TemporaryDirectory() as td:
        stl = Path(td) / "i.stl"
        export_stl(build_impeller(p), stl)
        rows = measure_sections(stl, [f for f, _ in pairs])
    for (_, s), r in zip(pairs, rows):
        a = _analytic(p, s, r["r_mm"], int(r.get("omega_sign", 1)), int(r["n_blades"]))
        assert r["camber_ratio"] == pytest.approx(a["camber_ratio"], abs=0.005), (s.r_frac, r, a)
        assert r["stagger_deg"] == pytest.approx(a["stagger_deg"], abs=1.5), (s.r_frac, r, a)
