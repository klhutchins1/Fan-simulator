"""QA-71 / QA-72 (grok r27): stale ~2× / ~0.6× / ~3–5 % that G4's file list missed."""

from __future__ import annotations

from pathlib import Path

from fansim.optimize.objectives import _operating_point_reason
from fansim.optimize.system_curve import SystemCurveError

ROOT = Path(__file__).resolve().parents[1]


def test_stalled_hose_reject_text_has_no_2x():
    msg = _operating_point_reason(
        SystemCurveError("probe CFM must be positive"), free_signed=35.0, probe_signed=-22.0,
        derate=0.88, p_free_pa=1.4, p_probe_pa=7.3, converged=True, free_drift_pct=0.0, load_drift_pct=0.0,
    )
    assert "stalls at this hose" in msg and "lighter hose" in msg
    assert "~2×" not in msg and "~2x" not in msg
    assert "about 10 %" in msg


def test_bem_prescreen_help_has_no_0_6x():
    src = (ROOT / "scripts" / "run_optimization.py").read_text(encoding="utf-8")
    assert "BEM≈0.6× CFD" not in src


def test_design_rules_generator_caveat_matches_g4():
    src = (ROOT / "scripts" / "extract_design_rules.py").read_text(encoding="utf-8")
    assert "~3–5% discretization" not in src
    assert "screening mesh, GCI ≈ 21 %" in src
