"""Blade sections wrapped onto their cylinders (roadmap 27.4 option i, spec 2026-10-12-cylinder-sections).

QA r8 Task D / QA-31: planar tangent-plane sections stacked with lean/skew lose most of their camber
in a cylinder cut (Stock: sliders 0.08-0.10 built 0.036-0.040). Wrapped sections must cut back to
their sliders.
"""
from __future__ import annotations

import dataclasses
import math
import tempfile
from pathlib import Path

import pytest

from fansim.geometry.blade import _section_points_3d, build_blade_solid
from fansim.geometry.chord_realisation import _station_measure_fracs, prepare_loft_chords
from fansim.geometry.export import export_stl
from fansim.geometry.features import Features
from fansim.validation.blade_golden import stock_a12x25_params
from fansim.validation.section_compare import measure_sections


def _kw(**over):
    kw = dict(r=40.0, r_frac=0.6, chord=30.0, stagger_deg=30.0, thickness=0.08, max_camber=0.08,
              camber_pos=0.45, sweep=1.0, skew=3.0, le_sweep=0.0, lean_deg=20.0, n_chord=40,
              features=Features())
    kw.update(over)
    return kw


def test_wrapped_section_lies_on_its_cylinder():
    pts = _section_points_3d(**_kw(), wrap=True)
    assert max(abs(math.hypot(p.x, p.y) - 40.0) for p in pts) < 1e-9


def test_planar_section_is_unchanged_by_default():
    flat = _section_points_3d(**_kw())
    assert max(math.hypot(p.x, p.y) for p in flat) > 40.5  # ends stand off the cylinder


def test_wrapped_arc_length_equals_tangential_distance():
    planar = _section_points_3d(**_kw(lean_deg=0.0))
    wrapped = _section_points_3d(**_kw(lean_deg=0.0), wrap=True)
    for p, w in zip(planar, wrapped):
        assert 40.0 * math.atan2(w.y, w.x) == pytest.approx(p.y, abs=1e-9)  # t = r * theta
        assert w.z == pytest.approx(p.z)


def _cut(params):
    fr = _station_measure_fracs(params)
    pairs = [(f, s) for f, s in zip(fr, params.stations) if f is not None]
    with tempfile.TemporaryDirectory() as td:
        stl = Path(td) / "b.stl"
        export_stl(build_blade_solid(prepare_loft_chords(params), _chord_realized=True,
                                     _trim_tip=False), stl)
        rows = measure_sections(stl, [f for f, _ in pairs], tip_radius_mm=params.tip_radius)
    return [(s, r) for (_, s), r in zip(pairs, rows)]


def test_wrapped_stock_cuts_back_to_its_sliders():
    p = dataclasses.replace(stock_a12x25_params(), section_wrap="cylinder")
    for s, r in _cut(p):
        assert r["chord_mm"] == pytest.approx(s.chord, rel=0.03)
        if s.max_camber >= 0.07:  # planar Stock reads 0.036-0.040 here; estimator bias ~-0.014
            assert r["camber_ratio"] > s.max_camber - 0.02, (s.r_frac, r["camber_ratio"])


def test_class_default_stays_planar_for_other_archetypes():
    from fansim.geometry.blade import BladeParams

    assert BladeParams.__dataclass_fields__["section_wrap"].default == "planar"
