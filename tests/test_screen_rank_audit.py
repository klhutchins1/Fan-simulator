"""Scoring logic of scripts/screen_rank_audit.py (no CFD)."""

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "screen_rank_audit", Path(__file__).resolve().parents[1] / "scripts" / "screen_rank_audit.py")
sra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sra)


def test_spearman_handles_ties_and_direction():
    assert sra.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert sra.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert 0.9 < sra.spearman([1, 2, 2, 3], [1, 2, 3, 4]) < 1.0


def _full(free, load, eff=20.0):
    return {"feasible": True, "cfm_free": free, "cfm_load": load, "efficiency": eff}


def test_judge_inconclusive_below_n_min():
    q = {f"d{i}": float(i) for i in range(5)}
    full = {f"d{i}": _full(i, i) for i in range(5)}
    assert sra.judge("Q", q, full)["verdict"] == "INCONCLUSIVE"


def test_judge_pass_and_fail():
    names = [f"d{i}" for i in range(10)]
    full = {n: _full(50 + i, 40 + i) for i, n in enumerate(names)}
    good = {n: 60.0 + i for i, n in enumerate(names)}
    assert sra.judge("Q", good, full)["verdict"] == "PASS"
    bad = {n: 60.0 - i for i, n in enumerate(names)}  # reversed ranking
    out = sra.judge("Q", bad, full)
    assert out["verdict"] == "FAIL" and not out["top_recall_ok"]


def test_judge_ignores_designs_the_full_assess_rejected():
    names = [f"d{i}" for i in range(9)]
    full = {n: _full(50 + i, 40 + i) for i, n in enumerate(names)}
    full["d0"] = {"feasible": False}
    q = {n: 60.0 + i for i, n in enumerate(names)}
    assert sra.judge("Q", q, full)["n"] == 8


def test_q1_replays_tail_mean_of_truncated_history(tmp_path, monkeypatch):
    monkeypatch.setattr(sra, "OUT", tmp_path)
    p = tmp_path / "x" / "full" / sra.FREE_HISTORY_DIR / "outletFlow" / "surfaceFieldValue.dat"
    p.parent.mkdir(parents=True)
    # flow 0.01 m3/s up to iteration 300, then 0.02: a 300-iteration run never sees the jump
    lines = ["# Time sum(phi)"] + [f"{t} {0.01 if t <= 300 else 0.02}" for t in range(12, 501, 12)]
    p.write_text("\n".join(lines))
    assert sra.q1_from_history("x", iters=300) == pytest.approx(0.01 * sra.CFM_PER_M3S)
    assert sra.q1_from_history("missing") is None


def test_resume_retries_killed_runs_but_keeps_finished_ones(tmp_path, monkeypatch):
    import json as _json

    monkeypatch.setattr(sra, "OUT", tmp_path)
    q = tmp_path / "stock" / "quick" / "result.json"
    q.parent.mkdir(parents=True)
    q.write_text(_json.dumps({"ok": True, "cfm_free_raw": 55.0}))
    assert sra.run_quick("stock", {})["cfm_free_raw"] == 55.0   # finished: not re-run
    f = tmp_path / "x" / "full" / "result.json"
    f.parent.mkdir(parents=True)
    f.write_text(_json.dumps({"feasible": False, "reason": "unprintable"}))
    assert sra.run_full("x", {})["reason"] == "unprintable"    # gate rejection is a result
