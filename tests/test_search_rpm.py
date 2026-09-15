"""--search-rpm wiring smoke (no Docker)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.optimize.pwm_table import (
    make_pwm_table,
    pwm_caption,
    resolve_pwm_table,
    suggest_rpm,
)

from tests._cli_parsers import load_build_parser


class _Trial:
    def suggest_float(self, name, lo, hi):
        assert name == "rpm"
        return 0.5 * (lo + hi)


def test_suggest_rpm_midband():
    assert suggest_rpm(_Trial()) == pytest.approx(1225.0)


def test_suggest_rpm_custom_band():
    tab = make_pwm_table(600.0, 1600.0)
    assert suggest_rpm(_Trial(), tab) == pytest.approx(1100.0)


def test_resolve_pwm_table_defaults_and_override():
    assert resolve_pwm_table().rpm_min == 450.0
    tab = resolve_pwm_table(500.0, 1800.0)
    assert tab.rpm_min == 500.0
    assert tab.rpm_max == 1800.0
    with pytest.raises(ValueError):
        make_pwm_table(2000.0, 450.0)


def test_pwm_caption_mentions_band():
    text = pwm_caption()
    assert "450" in text and "2000" in text
    assert "Kv" in text


def test_cli_declares_search_rpm_and_bounds():
    ap = load_build_parser("run_optimization.py")()
    args = ap.parse_args(["--search-rpm", "--rpm-min", "500", "--rpm-max", "1800"])
    assert args.search_rpm is True
    assert args.rpm_min == pytest.approx(500.0)
    assert args.rpm_max == pytest.approx(1800.0)


def test_run_study_passes_sampled_rpm_to_evaluate(tmp_path, monkeypatch):
    """§8.3: --search-rpm must reach evaluate_candidate(rpm=...), not only CLI help text."""
    from fansim.optimize import study as study_mod
    from fansim.optimize.objectives import ObjectiveResult

    seen: list[float | None] = []

    def fake_evaluate(_params, workdir, *_a, **kw):
        Path(workdir).mkdir(parents=True, exist_ok=True)
        seen.append(kw.get("rpm"))
        return ObjectiveResult(
            feasible=False,
            reason="stub",
            raw={"tip_gap_mm": 0.5},
        )

    monkeypatch.setattr(study_mod, "evaluate_candidate", fake_evaluate)
    study_mod.run_study(
        n_trials=2,
        out_dir=tmp_path,
        procs=1,
        iters=1,
        base_cell=0.02,
        search_rpm=True,
        rpm_min=600.0,
        rpm_max=1600.0,
    )
    assert len(seen) == 2
    assert all(v is not None for v in seen)
    assert all(600.0 <= float(v) <= 1600.0 for v in seen)
