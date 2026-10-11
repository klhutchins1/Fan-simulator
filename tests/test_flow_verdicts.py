from __future__ import annotations

import math

from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd.flow_verdicts import ROW_KEYS, judge, overall_line

STOCK = FlowMetrics(0.06, False, [2.0, 4.0, 6.0, 8.0, 6.0], 0.20, 0.05, 0.80, 60.0, 2.5)


def _m(**kw):
    d = STOCK.to_dict() | kw
    return FlowMetrics.from_dict(d)


def test_stock_vs_itself_all_ok_and_similar():
    rows = judge(STOCK, STOCK)
    assert [r.key for r in rows] == list(ROW_KEYS)
    assert all(r.status == "ok" for r in rows)
    assert rows[1].bands == ["similar"] * 5
    assert overall_line(rows, compared=True) == "About the same as Stock on every check."


def test_backflow_edge():
    assert judge(_m(backflow_frac=0.08), STOCK)[0].status == "ok"      # +0.02 exactly
    assert judge(_m(backflow_frac=0.0801), STOCK)[0].status == "warn"
    assert judge(_m(net_reversed=True), STOCK)[0].status == "bad"


def test_band_labels():
    rows = judge(_m(band_dp0_pa=[2.31, 4.0, 5.09, 9.2, 6.0]), STOCK)  # tol 15 %
    assert rows[1].bands == ["stronger", "similar", "weaker", "similar", "similar"]


def test_swirl_dead_noise_edges():
    assert judge(_m(swirl_frac=0.22), STOCK)[2].status == "ok"
    assert judge(_m(swirl_frac=0.2201), STOCK)[2].status == "warn"
    assert judge(_m(dead_frac=0.0701), STOCK)[3].status == "warn"
    assert judge(_m(tip_band_uz_ratio=0.71), STOCK)[3].status == "warn"
    assert judge(_m(noise_swl_db=62.8), STOCK)[4].status == "ok"
    assert judge(_m(noise_swl_db=62.81), STOCK)[4].status == "warn"


def test_noise_missing_is_na():
    assert judge(_m(noise_swl_db=None), STOCK)[4].status == "na"


def test_unavailable_metrics_never_ok():
    rows = judge(_m(swirl_frac=math.nan, dead_frac=math.nan, tip_band_uz_ratio=math.nan), STOCK)
    assert rows[2].status == "na" and rows[3].status == "na"


def test_no_stock_only_direction_judged():
    rows = judge(STOCK, None)
    assert rows[0].status == "ok"
    assert [r.status for r in rows[1:]] == ["na"] * 4
    assert overall_line(rows, compared=False).startswith("No Stock comparison")


def test_overall_better_and_worse():
    d = _m(backflow_frac=0.02, swirl_frac=0.30)
    line = overall_line(judge(d, STOCK), compared=True)
    assert line == "Better than Stock at: air direction. Worse at: wasted spin."
