"""Rule A: converged iff the tail mean is stable; the swing is reported, not judged."""

from __future__ import annotations

import math

import pytest

from fansim.cfd.metrics import CFD_VERSION, convergence, oscillation_pct


def _write_flow(case, values):
    d = case / "postProcessing" / "outletFlow" / "0"
    d.mkdir(parents=True, exist_ok=True)
    (d / "surfaceFieldValue.dat").write_text(
        "".join(f"{i + 1} {v}\n" for i, v in enumerate(values)), encoding="utf-8")


def test_limit_cycle_with_stable_mean_is_converged(tmp_path):
    # 8% peak-to-peak oscillation around 0.03, many periods in the tail.
    vals = [0.03 * (1 + 0.04 * math.sin(2 * math.pi * i / 10)) for i in range(400)]
    _write_flow(tmp_path, vals)
    ok, shift = convergence(tmp_path)
    assert ok and shift < 2.0
    assert oscillation_pct(tmp_path) == pytest.approx(8.0, abs=0.5)  # samples miss the exact peaks


def test_drifting_mean_is_not_converged(tmp_path):
    vals = [0.02 + 0.00004 * i for i in range(400)]  # still climbing through the tail
    _write_flow(tmp_path, vals)
    ok, shift = convergence(tmp_path)
    assert not ok and shift > 2.0


def test_too_short_history(tmp_path):
    _write_flow(tmp_path, [0.03, 0.03, 0.03])
    assert convergence(tmp_path) == (False, 999.0)


def test_cfd_version_bumped():
    assert CFD_VERSION == 4
