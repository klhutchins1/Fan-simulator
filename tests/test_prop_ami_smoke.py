# tests/test_prop_ami_smoke.py
from __future__ import annotations

from fansim.propeller.ami_smoke import (
    DELTA_T,
    N_REVS,
    ami_exit_code,
    assess_band,
    band_limits,
    end_time_s,
    rev_period_s,
    window_thrust_g,
)


def test_locked_time_knobs():
    period = rev_period_s(25257.0)
    assert period == 60.0 / 25257.0
    assert end_time_s(25257.0) == N_REVS * period
    assert DELTA_T == 4e-5


def test_window_uses_last_revolution_and_abs_fz():
    end = end_time_s(25257.0)
    period = rev_period_s(25257.0)
    t0 = end - period
    # column 3 is total Fz (N). 9.80665 N → 1000 g.
    rows = [
        [0.0, 0.0, 0.0, 9.80665],
        [t0 - 1e-6, 0.0, 0.0, -9.80665],
        [t0, 0.0, 0.0, 9.80665],
        [end, 0.0, 0.0, -9.80665],
    ]
    mean, count = window_thrust_g(rows, end_time=end, rpm=25257.0)
    assert count == 2
    assert mean == 1000.0


def test_window_zero_samples_is_none():
    end = end_time_s(25257.0)
    mean, count = window_thrust_g([[0.0, 0.0, 0.0, 1.0]], end_time=end, rpm=25257.0)
    assert mean is None
    assert count == 0


def test_band_edges_are_inclusive():
    lo, hi = band_limits()
    assert lo == 703.5
    assert hi == 1172.5
    assert assess_band(lo)["band_pass"] is True
    assert assess_band(hi)["band_pass"] is True
    assert assess_band(938.0)["band_pass"] is True
    assert assess_band(lo - 1e-6)["band_pass"] is False
    assert assess_band(hi + 1e-6)["band_pass"] is False
    assert assess_band(5.0)["band_pass"] is False
    assert assess_band(None)["band_pass"] is False
    assert assess_band(None)["mean_thrust_g"] is None


def test_exit_codes():
    assert ami_exit_code(assess_band(938.0)) == 0
    assert ami_exit_code(assess_band(2000.0)) == 2
    assert ami_exit_code(assess_band(5.0)) == 2
    assert ami_exit_code(assess_band(None)) == 1
    assert ami_exit_code({"mean_thrust_g": float("nan"), "band_pass": False}) == 1
