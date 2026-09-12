"""Tests for LE-only circumferential sickle (le_skew). No Docker."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from fansim.geometry.blade import (
    BladeParams,
    RadialStation,
    SICKLE_DEFAULT_MM,
    _section_loop,
    apply_sickle,
    build_impeller,
)
from fansim.geometry.features import Features


def _le_te(params: BladeParams, r_frac: float):
    st = min(params.stations, key=lambda s: abs(s.r_frac - r_frac))
    r0 = params.hub_radius - params.root_embed
    r = r0 + (params.tip_radius - r0) * st.r_frac
    x, pts = _section_loop(
        r=r, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg,
        thickness=st.thickness, max_camber=st.max_camber, camber_pos=st.camber_pos,
        sweep=st.sweep, skew=st.skew, le_sweep=st.le_sweep, lean_deg=st.lean_deg,
        n_chord=params.n_chord, features=Features(), le_skew=st.le_skew,
    )
    return pts[int(x.argmin())], pts[int(x.argmax())]


def _unswept() -> BladeParams:
    """Radial paddle (lean 0) so +t is +Y on the +X station."""
    return BladeParams(stations=[
        RadialStation(0.0, 34.0, 26.0, thickness=0.08, max_camber=0.05, lean_deg=0.0),
        RadialStation(0.5, 44.0, 26.0, thickness=0.05, max_camber=0.06, lean_deg=0.0),
        RadialStation(1.0, 38.0, 22.0, thickness=0.03, max_camber=0.06, lean_deg=0.0),
    ])


def test_zero_le_skew_matches_omitted_field():
    with_zero = RadialStation(1.0, 38.0, 22.0, le_skew=0.0)
    omitted = RadialStation(1.0, 38.0, 22.0)
    p0 = BladeParams(stations=[
        RadialStation(0.0, 34.0, 26.0), RadialStation(0.5, 44.0, 26.0), omitted,
    ])
    p1 = BladeParams(stations=[
        RadialStation(0.0, 34.0, 26.0), RadialStation(0.5, 44.0, 26.0), with_zero,
    ])
    le0, _ = _le_te(p0, 1.0)
    le1, _ = _le_te(p1, 1.0)
    assert abs(le0.x - le1.x) < 1e-6
    assert abs(le0.y - le1.y) < 1e-6
    assert abs(le0.z - le1.z) < 1e-6


def test_apply_sickle_moves_tip_le_not_te():
    p = _unswept()
    le0, te0 = _le_te(p, 1.0)
    apply_sickle(p, 8.0)
    assert p.stations[-1].le_skew == 8.0
    assert p.stations[1].le_skew == pytest.approx(3.2)
    le1, te1 = _le_te(p, 1.0)
    assert le1.y - le0.y == pytest.approx(8.0, abs=0.3)
    assert abs(te1.y - te0.y) < 0.3
    assert abs(te1.x - te0.x) < 0.3


def test_apply_sickle_leaves_hub_le():
    import math

    p = _unswept()
    le0, _ = _le_te(p, 0.0)
    apply_sickle(p, 8.0)
    le1, _ = _le_te(p, 0.0)
    assert math.hypot(le1.x - le0.x, le1.y - le0.y, le1.z - le0.z) < 0.3


def test_apply_sickle_zero_is_noop():
    p = _unswept()
    apply_sickle(p, 0.0)
    assert all(s.le_skew == 0.0 for s in p.stations)


def test_blade_from_flat_sickle_mm_round_trips():
    from fansim.optimize.search_space import blade_from_flat

    bp = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
        "sickle_mm": 8,
    })
    tip = max(bp.stations, key=lambda s: s.r_frac)
    assert tip.le_skew == pytest.approx(SICKLE_DEFAULT_MM)


def test_sickled_default_is_one_solid_in_120mm():
    p = apply_sickle(deepcopy(BladeParams()), 8.0)
    solid = build_impeller(p).val()
    assert len(solid.Solids()) == 1
    bb = solid.BoundingBox()
    dia = 2.0 * max(abs(bb.xmax), abs(bb.xmin), abs(bb.ymax), abs(bb.ymin))
    assert dia <= 120.0 + 0.2


def test_apply_sickle_band_edges_set_tip_le_skew():
    for tip_mm in (4.0, 12.0):
        p = apply_sickle(deepcopy(_unswept()), tip_mm)
        tip = max(p.stations, key=lambda s: s.r_frac)
        mid = min(p.stations, key=lambda s: abs(s.r_frac - 0.5))
        hub = min(p.stations, key=lambda s: s.r_frac)
        assert tip.le_skew == pytest.approx(tip_mm)
        assert mid.le_skew == pytest.approx(0.4 * tip_mm)
        assert hub.le_skew == pytest.approx(0.0)


def test_run_optimization_declares_sickle_flag():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--sickle" in text
    assert "★" not in text
