"""Pre-registered 2σ rule for flow-card thresholds (roadmap 27.3). No CFD."""
from __future__ import annotations

import math

from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd.flow_verdicts import judge
from scripts.stock_flow_repeats import (
    BAND_FLOOR,
    NOISE_FLOOR_DB,
    proposed_tolerances,
    sample_std,
)

# Five Stock v3 Assess repeats (runs/stock_flow_repeats/r1..r5, 2026-10-13). Gitignored.
_STOCK_V3_REPEATS = [
    {
        "mean_dp0_pa": 12.711160314596807,
        "noise_swl_db": 20.78027756250812,
        "band_dp0_pa": [
            8.266548537403766, 9.885739493507275, 11.172732698622834,
            13.146920343103943, 17.462532136513534,
        ],
    },
    {
        "mean_dp0_pa": 12.885857268226452,
        "noise_swl_db": 20.56024512375927,
        "band_dp0_pa": [
            8.482868711055122, 10.068244485809073, 11.36584726918475,
            13.328027964550806, 17.603816714286417,
        ],
    },
    {
        "mean_dp0_pa": 12.87971143089971,
        "noise_swl_db": 20.531114402729212,
        "band_dp0_pa": [
            8.470708054681591, 10.12959971766573, 11.341799985036074,
            13.333064080705107, 17.555501874093977,
        ],
    },
    {
        "mean_dp0_pa": 12.91858165425651,
        "noise_swl_db": 20.659155790647628,
        "band_dp0_pa": [
            8.518959241608357, 10.14012268025361, 11.394465537662679,
            13.339563403554497, 17.60748057179892,
        ],
    },
    {
        "mean_dp0_pa": 12.740930296542205,
        "noise_swl_db": 20.73778923504905,
        "band_dp0_pa": [
            8.307707439914484, 9.931126501034464, 11.225078496794666,
            13.180828499773783, 17.467318100169454,
        ],
    },
]


def _repeat_metrics(row: dict) -> FlowMetrics:
    return FlowMetrics(
        0.025, False, row["band_dp0_pa"], 0.60, 0.03, 0.95, row["noise_swl_db"], 2.5,
        mean_dp0_pa=row["mean_dp0_pa"],
    )


def test_sample_std_is_n_minus_one():
    assert sample_std([1.0, 3.0]) == 2.0 ** 0.5


def test_two_sigma_floors_when_repeats_are_identical():
    band, noise = proposed_tolerances(
        [10.0, 10.0, 10.0, 10.0, 10.0],
        [[2.0, 4.0, 6.0, 8.0, 6.0]] * 5,
        [60.0] * 5,
    )
    assert band == BAND_FLOOR
    assert noise == NOISE_FLOOR_DB


def test_two_sigma_uses_the_noisiest_kept_series_and_rounds_up():
    # mean_dp0 relative 2σ = 2 * 0.1 / 10 = 0.02 → floor.
    # band 0: values 2.0, 2.5, 3.0, 2.5, 2.0 → mean 2.4, σ≈0.418, 2σ_rel≈0.349 → 0.35
    means = [10.0, 10.1, 9.9, 10.0, 10.0]
    bands = [
        [2.0, 4.0, 6.0, 8.0, 6.0],
        [2.5, 4.0, 6.0, 8.0, 6.0],
        [3.0, 4.0, 6.0, 8.0, 6.0],
        [2.5, 4.0, 6.0, 8.0, 6.0],
        [2.0, 4.0, 6.0, 8.0, 6.0],
    ]
    noise = [60.0, 60.4, 59.7, 60.1, 60.2]
    band, db = proposed_tolerances(means, bands, noise)
    rel = 2.0 * sample_std([2.0, 2.5, 3.0, 2.5, 2.0]) / 2.4
    assert band == math.ceil(rel * 100.0 - 1e-12) / 100.0
    assert band >= 0.34
    assert db == math.ceil(2.0 * sample_std(noise) * 10.0 - 1e-12) / 10.0


def test_near_zero_band_is_ignored():
    means = [10.0] * 5
    bands = [[0.1 + 0.4 * i, 4.0, 6.0, 8.0, 6.0] for i in range(5)]
    band, _ = proposed_tolerances(means, bands, [60.0] * 5)
    assert band == BAND_FLOOR


def test_measured_stock_v3_repeats_propose_0_03_and_0_5():
    means = [r["mean_dp0_pa"] for r in _STOCK_V3_REPEATS]
    bands = [r["band_dp0_pa"] for r in _STOCK_V3_REPEATS]
    noise = [r["noise_swl_db"] for r in _STOCK_V3_REPEATS]
    assert proposed_tolerances(means, bands, noise) == (0.03, 0.5)


def test_after_bake_same_mesh_repeats():
    """27.3 after-bake recorded r4's hub bar 3.05 % above r1 (a FAIL at the old shared 3 %). Since 27.3b
    (Kimball 2026-10-16) bars use their own margin and noise is not judged; since R0.3 (2026-10-17) a same-fan
    repeat reads "too close to call" (na, never better) on the push row, and every row reads the same."""
    r1 = _repeat_metrics(_STOCK_V3_REPEATS[0])
    rows_by_id = []
    for row in _STOCK_V3_REPEATS[1:]:
        rows_by_id.append(judge(_repeat_metrics(row), r1))
    for rows in rows_by_id:
        assert rows[1].status == "na" and not rows[1].better and "Too close to call" in rows[1].text
        assert rows[4].status == "na"
    r2, r3, r4, r5 = rows_by_id
    assert r2[1].bands == ["similar"] * 5
    assert r3[1].bands == ["similar"] * 5
    assert r4[1].bands == ["similar"] * 5
    assert r5[1].bands == ["similar"] * 5
