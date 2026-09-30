"""§20.6 weighted multi-point duty + CFM at matched relative noise."""

from __future__ import annotations

from fansim.geometry.blade import BladeParams
from fansim.optimize.multi_point import (
    DEFAULT_PC_CYCLE,
    DutyWeight,
    cfm_at_matched_noise,
    format_multi_point,
    relative_fan_noise,
    score_multi_point,
)
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat
from fansim.geometry.features import Features


def _stock() -> BladeParams:
    return blade_from_flat(stock_blade_flat("a12x25"), Features())


def test_default_cycle_weights_sum_to_one():
    assert abs(sum(d.weight for d in DEFAULT_PC_CYCLE) - 1.0) < 1e-9


def test_score_multi_point_positive_cfm():
    score = score_multi_point(_stock())
    assert score.weighted_cfm_load > 0.0
    assert score.weighted_cfm_free >= score.weighted_cfm_load
    assert len(score.points) == 3
    assert all(p.cfm_free > 0 for p in score.points)


def test_higher_duty_raises_noise():
    lo = score_multi_point(_stock(), [DutyWeight(25.0, 1.0, "case")])
    hi = score_multi_point(_stock(), [DutyWeight(100.0, 1.0, "case")])
    assert hi.points[0].rel_noise_db > lo.points[0].rel_noise_db
    assert hi.points[0].rpm > lo.points[0].rpm


def test_cfm_at_matched_noise_in_band():
    stock = _stock()
    mid = score_multi_point(stock, [DutyWeight(50.0, 1.0, "case")])
    target = mid.points[0].rel_noise_db
    hit = cfm_at_matched_noise(stock, target)
    assert hit["cfm_free"] is not None
    assert hit["cfm_free"] > 0.0
    assert hit["duty_pct"] is not None


def test_cfm_at_matched_noise_outside_band_is_none():
    hit = cfm_at_matched_noise(_stock(), noise_ref_db=200.0)
    assert hit["cfm_free"] is None


def test_format_multi_point_mentions_section():
    lines = format_multi_point(score_multi_point(_stock()))
    assert any("§20.6" in ln for ln in lines)


def test_relative_fan_noise_grows_with_rpm():
    p = _stock()
    a, _, _ = relative_fan_noise(p, 800.0, thrust_n=0.5, shaft_power_w=2.0)
    b, _, _ = relative_fan_noise(p, 2000.0, thrust_n=0.5, shaft_power_w=8.0)
    assert b > a
