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

from fansim.geometry import build_impeller
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


def test_lt120_hangs_past_the_hub_face_limit_and_is_refused():
    """QA-30 found the hub-face clip shortening lt120's chord. lt120's blades hang 4.8 mm below the hub
    face as designed, past the 2 mm limit (Kimball 2026-10-13), so it is refused outright; the clipped
    chord / camber correction for designs under the limit is tested in test_hub_hang.py."""
    from fansim.geometry.blade import validate_blade_params
    from fansim.geometry.config import load_blade_params

    p = dataclasses.replace(load_blade_params("docs/qa/benchmarks/lt120/fansim_params.json"),
                            section_wrap="cylinder")
    with pytest.raises(ValueError, match="below the hub"):
        validate_blade_params(p)
    validate_blade_params(dataclasses.replace(p, clip_below_hub=False))  # its own rig: no motor face


def test_wrapped_impeller_keeps_its_hub_and_blades():
    """S4_0001 (10 blades, wide roots overlapping in the hub): with planar end wires the wrapped loft
    folded and every boolean returned nothing, so the "impeller" was a single blade (1 190 mm3 vs
    76 518). With capped ruled lofts it must match the planar build's volume."""
    import json

    from fansim.optimize.search_space import blade_from_flat

    d = json.loads((Path(__file__).parent / "data" / "s4_0001_overlapping_roots_flat.json").read_text())
    base = blade_from_flat(d["flat"], Features(**d["features"]))
    vols = {w: float(build_impeller(dataclasses.replace(base, section_wrap=w)).val().Volume())
            for w in ("planar", "cylinder")}
    assert vols["cylinder"] == pytest.approx(vols["planar"], rel=0.05), vols


def test_a_fuse_that_leaves_loose_pieces_is_redone_one_blade_at_a_time(monkeypatch):
    """The first sharp-edge v3 Stock (commit 7a1a466, tests/data/stock_v3_fuse_fragile.yaml) fused
    into 2 solids / 6 mesh bodies with the parallel and the all-at-once serial fuse (the full suite's
    "not watertight (6 bodies)"); one blade at a time gave one clean solid. Whether OCCT trips depends
    on the exact geometry, so simulate the trip: a multi-tool fuse that hands back loose pieces."""
    import cadquery as cq

    import fansim.geometry.blade as gb
    from fansim.geometry.config import load_blade_params
    from fansim.resources import TIERS

    real = gb._fuse

    def tripping(base, tools, parallel=False):
        tools = list(tools)
        if len(tools) > 1:
            return cq.Compound.makeCompound([base, *tools])   # unfused: many solids
        return real(base, tools, parallel=parallel)

    monkeypatch.setattr(gb, "_fuse", tripping)
    p = dataclasses.replace(load_blade_params("config/problems/a12x25_reference.yaml"), n_blades=3)
    hub, blades, ring = gb.build_impeller_parts(p)
    fused = gb.fuse_impeller(hub, blades, ring, tier=next(t for t in TIERS if t.name == "8gb"))
    assert len(fused.Solids()) == 1 and fused.isValid()
