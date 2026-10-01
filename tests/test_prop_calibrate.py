"""Prop spin/sign + datasheet calibration helpers."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from fansim.prop_spec import get_prop_spec
from fansim.propeller.calibrate import (
    affinity_thrust_g,
    bemt_datasheet_report,
    datasheet_compare,
    normalize_metrics_sign,
)


def test_affinity_thrust_scales_n2():
    assert affinity_thrust_g(1600.0, 20000.0, 10000.0) == 400.0


def test_normalize_metrics_sign():
    out = normalize_metrics_sign({"thrust_n": -2.0, "thrust_g": -200.0}, spin=-1)
    assert out["thrust_n_raw"] == -2.0
    assert out["thrust_n"] == 2.0
    assert out["thrust_sign_ok"] is True
    assert "thrust_sign_error" not in out


def test_datasheet_compare_fpv():
    spec = get_prop_spec("fpv_5inch")
    d = datasheet_compare(thrust_g=400.0, rpm=15000.0, spec=spec)
    # ref 1850 @ 30k → scale (0.5)^2 → 462.5; ratio ~0.86
    assert d["thrust_ref_scaled_g"] == affinity_thrust_g(1850.0, 30000.0, 15000.0)
    assert d["within_2x"] is True


def test_bemt_datasheet_report_runs():
    rep = bemt_datasheet_report(get_prop_spec("fpv_5inch"))
    assert rep["source"] == "bemt"
    assert rep["thrust_g"] > 0
    assert "thrust_ratio" in rep["datasheet"]


def test_datasheet_cli_prints_power():
    script = Path(__file__).resolve().parents[1] / "scripts" / "calibrate_prop_datasheet.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--spec", "fpv_5inch"],
        check=True,
        capture_output=True,
        text=True,
    )
    line = proc.stdout.splitlines()[0]
    # Format contract, not BEMT numbers (those moved with the t/c-aware polars, 42ce15f, and are
    # covered by the propeller.bemt audit). Power and its ratio must be printed.
    assert re.fullmatch(
        r"fpv_5inch: BEMT \d+ g, [\d.]+ W @ 30000 RPM \| "
        r"ref_scaled 1850\.0 g, 650\.0 W \| "
        r"thrust_ratio [\d.]+ \| power_ratio [\d.]+ \| within_2x=True",
        line,
    ), line
