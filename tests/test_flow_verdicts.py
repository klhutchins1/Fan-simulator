from __future__ import annotations

import math

from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd import flow_verdicts
from fansim.cfd.flow_verdicts import (
    BAND_TOL,
    BAR_TOL,
    HINT_MARGIN_DB,
    NOISE_JUDGED,
    NOISE_MARGIN_DB,
    ROW_KEYS,
    judge,
    overall_line,
)

STOCK = FlowMetrics(0.06, False, [2.0, 4.0, 6.0, 8.0, 6.0], 0.20, 0.05, 0.80, 60.0, 2.5, mean_dp0_pa=6.0)


def _m(**kw):
    d = STOCK.to_dict() | kw
    return FlowMetrics.from_dict(d)


def test_stock_vs_itself_all_ok_and_similar():
    rows = judge(STOCK, STOCK)
    assert [r.key for r in rows] == list(ROW_KEYS)
    assert all(r.status == "ok" for r in rows[:4])
    assert rows[4].status == "na" and rows[4].expert_only  # noise not judged (27.3b)
    assert rows[1].bands == ["similar"] * 5
    assert overall_line(rows, compared=True) == "About the same as Stock on every check."


def test_backflow_edge():
    assert judge(_m(backflow_frac=0.08), STOCK)[0].status == "ok"      # +0.02 exactly
    assert judge(_m(backflow_frac=0.0801), STOCK)[0].status == "warn"
    assert judge(_m(net_reversed=True), STOCK)[0].status == "bad"


def test_band_labels():
    rows = judge(_m(band_dp0_pa=[2.25, 4.0, 5.27, 8.9, 6.0]), STOCK)  # bar tol 12 %
    assert rows[1].bands == ["stronger", "similar", "weaker", "similar", "similar"]
    # 27.3b: a 5 % bar wobble is mesh noise, not "stronger"
    assert judge(_m(band_dp0_pa=[2.1, 4.2, 5.7, 8.4, 6.3]), STOCK)[1].bands == ["similar"] * 5


def test_swirl_dead_noise_edges():
    assert judge(_m(swirl_frac=0.22), STOCK)[2].status == "ok"
    assert judge(_m(swirl_frac=0.2201), STOCK)[2].status == "warn"
    assert judge(_m(dead_frac=0.0701), STOCK)[3].status == "warn"
    assert judge(_m(tip_band_uz_ratio=0.71), STOCK)[3].status == "warn"


def test_noise_judged_edges_if_ever_turned_back_on(monkeypatch):
    monkeypatch.setattr(flow_verdicts, "NOISE_JUDGED", True)
    assert judge(_m(noise_swl_db=60.5), STOCK)[4].status == "ok"
    assert judge(_m(noise_swl_db=60.51), STOCK)[4].status == "warn"


def test_noise_never_in_the_verdict():
    """Kimball 2026-10-16 (27.3b): Stock alone moved -13.7..+22.2 dB across five meshes."""
    for db in (30.0, 60.0, 90.0):
        rows = judge(_m(noise_swl_db=db), STOCK)
        assert rows[4].status == "na" and rows[4].better is None and rows[4].expert_only
        assert "Not judged" in rows[4].text
        assert overall_line(rows, compared=True) == "About the same as Stock on every check."


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


def test_push_verdict_uses_the_mean_not_the_band_tilt():
    """Kimball 2026-10-12 (27.3 option b): a swirlier fan's bands tilt hub-weak/tip-strong from radial
    equilibrium alone, so the row judges the area-weighted mean; bands stay a picture."""
    tilted = _m(band_dp0_pa=[0.5, 3.0, 6.0, 9.5, 8.0], mean_dp0_pa=6.1)
    row = judge(tilted, STOCK)[1]
    assert row.status == "ok" and row.better is False
    assert row.text.startswith("Pushes about as hard as Stock overall")


def test_push_mean_stronger_and_weaker():
    up = judge(_m(mean_dp0_pa=6.0 * (1 + BAND_TOL) + 0.01), STOCK)[1]
    assert up.status == "ok" and up.better is True and "harder" in up.text
    assert judge(_m(mean_dp0_pa=6.0 * (1 + BAND_TOL)), STOCK)[1].better is False  # edge is "similar"
    down = judge(_m(mean_dp0_pa=6.0 * (1 - BAND_TOL) - 0.01), STOCK)[1]
    assert down.status == "warn" and down.better is False and "less" in down.text


def test_push_mean_missing_is_na():
    assert judge(_m(mean_dp0_pa=math.nan), STOCK)[1].status == "na"
    assert judge(STOCK, _m(mean_dp0_pa=0.0))[1].status == "na"  # no Stock push to compare with


def test_baked_tolerances_are_stock_v3_two_sigma():
    assert BAND_TOL == 0.06          # v4 planes, 27.3e / R0.2
    assert BAR_TOL == 0.12          # v4 planes, 27.3e / R0.2
    assert NOISE_MARGIN_DB == 0.5
    assert NOISE_JUDGED is False    # Proudman still not judged
    assert HINT_MARGIN_DB == 0.5    # 27.3c tip+CFM 2σ was 0.069 dB


def test_noise_hint_is_judged_but_stays_off_the_simple_line():
    """27.3c: Expert row uses tip-speed + CFM; Simple overall must not mention it."""
    stock = _m(noise_hint_db=75.4)
    same = judge(_m(noise_hint_db=75.4), stock)[4]
    assert same.status == "ok" and same.expert_only and "About as loud" in same.text
    quiet = judge(_m(noise_hint_db=74.4), stock)[4]
    assert quiet.status == "ok" and quiet.better is True and "quieter" in quiet.text
    loud = judge(_m(noise_hint_db=76.4), stock)[4]
    assert loud.status == "warn" and loud.better is False and "louder" in loud.text
    rows = judge(_m(noise_hint_db=76.4, swirl_frac=0.20), stock)
    assert overall_line(rows, compared=True) == "About the same as Stock on every check."


def test_old_metrics_json_without_noise_hint_still_loads():
    d = STOCK.to_dict()
    d.pop("noise_hint_db", None)
    m = FlowMetrics.from_dict(d)
    assert m.noise_hint_db is None
