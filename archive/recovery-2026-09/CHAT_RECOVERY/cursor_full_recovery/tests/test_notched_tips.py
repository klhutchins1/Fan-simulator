"""Tests for tip-only trailing-edge notches. No Docker."""

from __future__ import annotations

import math
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from fansim.geometry.blade import (
    BladeParams,
    NOTCH_COUNT,
    NOTCH_DEPTH_MM,
    NOTCH_START_FRAC,
    RadialStation,
    _interp_stations,
    _section_loop,
    apply_notched_tips,
    build_impeller,
)
from fansim.geometry.features import Features


def _unswept() -> BladeParams:
    return BladeParams(stations=[
        RadialStation(0.0, 34.0, 26.0, thickness=0.08, max_camber=0.05, lean_deg=0.0),
        RadialStation(0.5, 44.0, 26.0, thickness=0.05, max_camber=0.06, lean_deg=0.0),
        RadialStation(1.0, 38.0, 22.0, thickness=0.03, max_camber=0.06, lean_deg=0.0),
    ])


def _le_te_at(params: BladeParams, r_frac: float):
    it = _interp_stations(params, 3)
    r0 = params.hub_radius - params.root_embed
    r = r0 + (params.tip_radius - r0) * r_frac
    chord = float(np.interp(r_frac, it["r_frac"], it["chord"]))
    stagger = float(np.interp(r_frac, it["r_frac"], it["stagger_deg"]))
    thickness = float(np.interp(r_frac, it["r_frac"], it["thickness"]))
    camber = float(np.interp(r_frac, it["r_frac"], it["max_camber"]))
    cpos = float(np.interp(r_frac, it["r_frac"], it["camber_pos"]))
    sweep = float(np.interp(r_frac, it["r_frac"], it["sweep"]))
    skew = float(np.interp(r_frac, it["r_frac"], it["skew"]))
    le_sweep = float(np.interp(r_frac, it["r_frac"], it["le_sweep"]))
    lean = float(np.interp(r_frac, it["r_frac"], it["lean_deg"]))
    le_skew = float(np.interp(r_frac, it["r_frac"], it["le_skew"]))
    x, pts = _section_loop(
        r=r, r_frac=r_frac, chord=chord, stagger_deg=stagger, thickness=thickness,
        max_camber=camber, camber_pos=cpos, sweep=sweep, skew=skew, le_sweep=le_sweep,
        lean_deg=lean, n_chord=params.n_chord, features=Features(), le_skew=le_skew,
        tip_notch_count=params.tip_notch_count,
        tip_notch_depth_mm=params.tip_notch_depth_mm,
    )
    return pts[int(x.argmin())], pts[int(x.argmax())]


def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y, a.z - b.z)


def test_notched_tips_leave_hub_te():
    p = _unswept()
    le0, te0 = _le_te_at(p, 0.0)
    apply_notched_tips(p)
    le1, te1 = _le_te_at(p, 0.0)
    assert _dist(te1, te0) < 0.3
    assert _dist(le1, le0) < 0.3


def test_notched_tips_bite_te_at_first_tooth_not_le():
    p = _unswept()
    u_peak = 0.25 / NOTCH_COUNT  # first positive lobe of sin(2π count u)
    rf = NOTCH_START_FRAC + (1.0 - NOTCH_START_FRAC) * u_peak
    le0, te0 = _le_te_at(p, rf)
    apply_notched_tips(p)
    assert p.tip_notch_count == NOTCH_COUNT
    assert p.tip_notch_depth_mm == pytest.approx(NOTCH_DEPTH_MM)
    le1, te1 = _le_te_at(p, rf)
    assert _dist(le1, le0) < 0.3
    chord0 = _dist(le0, te0)
    chord1 = _dist(le1, te1)
    assert chord0 - chord1 == pytest.approx(NOTCH_DEPTH_MM, abs=0.3)


def test_apply_notched_tips_is_idempotent():
    p = _unswept()
    apply_notched_tips(p)
    apply_notched_tips(p)
    assert p.tip_notch_count == NOTCH_COUNT
    assert p.tip_notch_depth_mm == pytest.approx(NOTCH_DEPTH_MM)


def test_blade_from_flat_notched_tips_round_trips():
    from fansim.optimize.search_space import blade_from_flat

    bp = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
        "notched_tips": True,
    })
    assert bp.tip_notch_count == NOTCH_COUNT
    assert bp.tip_notch_depth_mm == pytest.approx(NOTCH_DEPTH_MM)
    assert bp.features.serration_amp == 0.0
    assert bp.features.serration_waves == 0


def test_notched_default_is_one_solid_in_120mm():
    p = apply_notched_tips(deepcopy(BladeParams()))
    solid = build_impeller(p).val()
    assert len(solid.Solids()) == 1
    bb = solid.BoundingBox()
    dia = 2.0 * max(abs(bb.xmax), abs(bb.xmin), abs(bb.ymax), abs(bb.ymin))
    assert dia <= 120.0 + 0.2


def test_run_optimization_declares_notched_tips_flag():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--notched-tips" in text
    assert "★" not in text
