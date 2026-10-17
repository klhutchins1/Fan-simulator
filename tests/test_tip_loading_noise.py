"""27.3c: tip-speed + CFM noise hint is mesh-stable on the published Stock repeats."""

from __future__ import annotations

import json
import math
import statistics

import pytest

from fansim.acoustics.tip_loading import (
    noise_hint_from_case,
    tip_loading_swl_db,
    tip_speed_ms,
)
from fansim.cfd.flow_verdicts import HINT_MARGIN_DB

# Frozen 27.3b table — do not re-solve.
M1_M5_CFM = (53.31, 53.04, 53.58, 52.45, 53.13)
STOCK_RPM = 2000.0
STOCK_TIP_MM = 54.5


def test_dipole_scale_and_cfm_term():
    u = tip_speed_ms(STOCK_RPM, STOCK_TIP_MM)
    assert u == pytest.approx(STOCK_RPM * 2.0 * math.pi / 60.0 * STOCK_TIP_MM / 1000.0)
    a = tip_loading_swl_db(u, 50.0)
    b = tip_loading_swl_db(u, 100.0)
    assert b - a == pytest.approx(10.0 * math.log10(2.0))


def test_m1_m5_two_sigma_passes_one_db():
    u = tip_speed_ms(STOCK_RPM, STOCK_TIP_MM)
    levels = [tip_loading_swl_db(u, q) for q in M1_M5_CFM]
    two_sigma = 2.0 * statistics.stdev(levels)
    assert two_sigma <= 1.0
    assert two_sigma == pytest.approx(0.0686, abs=5e-4)
    assert HINT_MARGIN_DB == 0.5
    assert max(abs(x - levels[0]) for x in levels[1:]) < HINT_MARGIN_DB


def test_hint_from_eval_json(tmp_path):
    (tmp_path / "_eval_result.json").write_text(
        json.dumps({"cfm_free": 53.31, "actual_rpm": 2000.0}), encoding="utf-8")
    (tmp_path / "design.json").write_text(
        json.dumps({"params": {"tip_radius": 54.5, "hub_radius": 18.625}}), encoding="utf-8")
    got = noise_hint_from_case(tmp_path)
    want = tip_loading_swl_db(tip_speed_ms(2000.0, 54.5), 53.31)
    assert got == pytest.approx(want)


def test_hint_missing_without_eval(tmp_path):
    assert noise_hint_from_case(tmp_path) is None
