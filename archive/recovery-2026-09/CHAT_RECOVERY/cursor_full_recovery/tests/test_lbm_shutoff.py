"""Tests for LBM shut-off settle reduction (no GPU)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.cfd.lbm_shutoff import PUBLISHED_SHUTOFF_PA, settle_shutoff


def _write_csv(path: Path, rows: list[tuple[float, int, float, float, float, float]]) -> Path:
    path.write_text(
        "t_s,step,rho_intake,rho_disch,dp_pa,cfm\n"
        + "\n".join(f"{t},{s},{ri},{rd},{dp},{q}" for t, s, ri, rd, dp, q in rows)
        + "\n",
        encoding="utf-8",
    )
    return path


def test_settle_uses_late_window_not_overshoot(tmp_path: Path):
    # Early overshoot 30 Pa, then settles at 21 Pa — late window must ignore the peak
    rows = []
    for i in range(100):
        dp = 30.0 if i < 50 else 21.0
        rows.append((0.01 * i, 480 * i, 1.0, 1.001, dp, 0.1 if i < 50 else 0.0))
    csv = _write_csv(tmp_path / "shut.csv", rows)
    m = settle_shutoff(csv, settle_from_frac=0.60)
    assert m["shut_off_pa"] == pytest.approx(21.0)
    assert m["peak_pa"] == pytest.approx(30.0)
    assert m["residual_cfm"] == pytest.approx(0.0)
    assert m["target_pa"] == PUBLISHED_SHUTOFF_PA
    assert m["error_pct"] == pytest.approx(100.0 * (21.0 - 22.9) / 22.9, abs=0.2)
    assert m["n_settle"] == 40


def test_settle_rejects_empty_csv(tmp_path: Path):
    p = tmp_path / "bad.csv"
    p.write_text("t_s,step,rho_intake,rho_disch,dp_pa,cfm\n", encoding="utf-8")
    with pytest.raises(ValueError, match="too short"):
        settle_shutoff(p)
