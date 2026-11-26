from __future__ import annotations

import math

from fansim.cfd import flow_verdicts
from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd.flow_verdicts import (
    BAND_TOL,
    BAR_TOL,
    CLOSE_BACKFLOW,
    CLOSE_BAND,
    CLOSE_DEAD,
    CLOSE_SWIRL_REL,
    CLOSE_TIP_REL,
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
    assert all(r.status == "na" for r in rows[:4])  # R0.3: zero difference is mesh-scatter
    assert all("Too close to call" in r.text for r in rows[:4])
    assert rows[4].status == "na" and rows[4].expert_only  # noise not judged (27.3b)
    assert rows[1].bands == ["similar"] * 5
    assert overall_line(rows, compared=True) == "About the same as Stock on every check."


def test_backflow_edge():
    inside = judge(_m(backflow_frac=STOCK.backflow_frac + CLOSE_BACKFLOW), STOCK)[0]
    assert inside.status == "na" and "Too close to call" in inside.text
    assert judge(_m(backflow_frac=STOCK.backflow_frac + CLOSE_BACKFLOW + 1e-4), STOCK)[0].status == "warn"
    less = judge(_m(backflow_frac=STOCK.backflow_frac - CLOSE_BACKFLOW - 1e-4), STOCK)[0]
    assert less.status == "ok" and less.better is True
    assert judge(_m(net_reversed=True), STOCK)[0].status == "bad"


def test_band_labels():
    rows = judge(_m(band_dp0_pa=[2.25, 4.0, 5.27, 8.9, 6.0]), STOCK)  # bar tol 12 %
    assert rows[1].bands == ["stronger", "similar", "weaker", "similar", "similar"]
    # 27.3b: a 5 % bar wobble is mesh noise, not "stronger"
    assert judge(_m(band_dp0_pa=[2.1, 4.2, 5.7, 8.4, 6.3]), STOCK)[1].bands == ["similar"] * 5


def test_swirl_dead_noise_edges():
    swirl_lo = STOCK.swirl_frac * (1 + CLOSE_SWIRL_REL)
    assert judge(_m(swirl_frac=swirl_lo), STOCK)[2].status == "na"
    assert judge(_m(swirl_frac=swirl_lo + 1e-4), STOCK)[2].status == "warn"
    assert judge(_m(dead_frac=STOCK.dead_frac + CLOSE_DEAD + 1e-4), STOCK)[3].status == "warn"
    weak = STOCK.tip_band_uz_ratio * (1 - CLOSE_TIP_REL) - 1e-4
    assert judge(_m(tip_band_uz_ratio=weak), STOCK)[3].status == "warn"


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
    assert row.status == "na" and row.better is None
    assert "Too close to call" in row.text


def test_push_mean_stronger_and_weaker():
    up = judge(_m(mean_dp0_pa=6.0 * (1 + CLOSE_BAND) + 0.01), STOCK)[1]
    assert up.status == "ok" and up.better is True and "harder" in up.text
    edge = judge(_m(mean_dp0_pa=6.0 * (1 + CLOSE_BAND)), STOCK)[1]
    assert edge.status == "na" and "Too close to call" in edge.text
    down = judge(_m(mean_dp0_pa=6.0 * (1 - CLOSE_BAND) - 0.01), STOCK)[1]
    assert down.status == "warn" and down.better is False and "less" in down.text


def test_push_mean_missing_is_na():
    assert judge(_m(mean_dp0_pa=math.nan), STOCK)[1].status == "na"
    assert judge(STOCK, _m(mean_dp0_pa=0.0))[1].status == "na"  # no Stock push to compare with


def test_baked_tolerances_are_stock_v3_two_sigma():
    assert BAND_TOL == 0.06          # v4 planes, 27.3e / R0.2
    assert BAR_TOL == 0.12          # v4 planes, 27.3e / R0.2
    assert CLOSE_BAND == 0.08        # √2 × 5.65 % mean-push 2σ (R0.3)
    assert CLOSE_BACKFLOW == 0.02
    assert CLOSE_SWIRL_REL == 0.10
    assert CLOSE_DEAD == 0.02
    assert CLOSE_TIP_REL == 0.15
    assert NOISE_MARGIN_DB == 0.5
    assert NOISE_JUDGED is False    # Proudman still not judged
    assert HINT_MARGIN_DB == 0.5    # 27.3c tip+CFM 2σ was 0.069 dB


def test_noise_hint_is_never_judged():
    """R0.4 / G2: the hint restates CFM; never ✓/⚠/better. Expert keeps the number + honesty."""
    stock = _m(noise_hint_db=75.4)
    loud = judge(_m(noise_hint_db=76.4), stock)[4]  # more CFM → higher hint
    assert loud.status == "na" and loud.better is None and loud.expert_only
    assert "⚠" not in loud.text and loud.status != "warn"
    assert "Scales with tip speed and airflow only" in loud.text
    assert "not a comparison of how quiet the design is" in loud.text
    rows = judge(_m(noise_hint_db=76.4, swirl_frac=0.20), stock)
    assert overall_line(rows, compared=True) == "About the same as Stock on every check."


def test_old_metrics_json_without_noise_hint_still_loads():
    d = STOCK.to_dict()
    d.pop("noise_hint_db", None)
    m = FlowMetrics.from_dict(d)
    assert m.noise_hint_db is None


def test_expert_noise_hint_row_kept_without_turbulence_data():
    """QA-70 (grok ui-hunt-1): the R0.4 hint needs only tip speed + CFM, so it shows in Expert even with no SWL."""
    import fansim.cockpit.fan_flow_report as F

    d = _m(noise_hint_db=30.0, noise_swl_db=None)
    s = _m(noise_hint_db=28.0, noise_swl_db=None)
    orig = (F.load_or_compute_metrics, F._attach_noise_hint, F.test_settings, F.first_mismatch, F._stock_pack, F._pictures_cached)
    try:
        F.load_or_compute_metrics = lambda case: d
        F._attach_noise_hint = lambda m, case: m
        F.test_settings = lambda case: {}
        F.first_mismatch = lambda a, b: None
        F._stock_pack = lambda ref: (s, None, {})
        F._pictures_cached = lambda *a, **k: {}
        rows = F.build_report("/tmp/qa70_case", "/tmp/qa70_ref")["flow_rows"]
    finally:
        (F.load_or_compute_metrics, F._attach_noise_hint, F.test_settings, F.first_mismatch, F._stock_pack, F._pictures_cached) = orig
    noise = [r for r in rows if r["key"] == "noise"]
    assert len(noise) == 1 and noise[0]["expert_only"] and noise[0]["status"] == "na"
    assert "not a comparison of how quiet" in noise[0]["text"]


def test_band_labels_handle_negative_stock_push():
    """Negative reference bands (e.g. hub swirl depression) must not invert stronger/weaker."""
    neg_stock = _m(band_dp0_pa=[-5.0, -5.0, -5.0, -5.0, 6.0])
    # BAR_TOL = 0.12 -> ±0.60 around -5.0: similar in [-5.6, -4.4], stronger > -4.4, weaker < -5.6
    design = _m(band_dp0_pa=[-5.0, -5.5, -5.7, -4.3, 6.0])
    assert judge(design, neg_stock)[1].bands == ["similar", "similar", "weaker", "stronger", "similar"]


def test_direction_handles_nan_stock_backflow():
    row = judge(STOCK, _m(backflow_frac=math.nan))[0]
    assert row.status == "na" and row.better is None
    assert "nan" not in row.text.lower()


def test_nonfinite_inf_and_noise_nan_are_na():
    rows = judge(_m(backflow_frac=math.inf, swirl_frac=math.inf,
                    mean_dp0_pa=math.inf, dead_frac=math.inf,
                    noise_swl_db=math.nan, noise_hint_db=math.nan), STOCK)
    assert all(r.status == "na" and r.better is None for r in rows)
    assert all("nan" not in r.text.lower() and "inf" not in r.text.lower() for r in rows)

