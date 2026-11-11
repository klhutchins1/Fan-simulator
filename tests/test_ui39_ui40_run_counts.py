"""UI-39 / UI-40 (grok ui-hunt-1, r27): run-count fields refuse bad values visibly; nothing is clamped."""

from pathlib import Path

import pytest

from fansim.cockpit.input_checks import opt_trials, sweep_steps

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("raw", ["", None, "abc", "2.5", "1e9", "1", "13", "100", "-5", "nan"])
def test_sweep_steps_refuses(raw):
    val, msg = sweep_steps(raw)
    assert val is None and "2 to 12" in msg and "Nothing was started" in msg


@pytest.mark.parametrize("raw,want", [("2", 2), ("12", 12), (3, 3), ("5.0", 5)])
def test_sweep_steps_accepts(raw, want):
    assert sweep_steps(raw) == (want, None)


@pytest.mark.parametrize("raw", ["", "abc", "1", "41", "100", "1e9", "-5", "8.5"])
def test_opt_trials_refuses_instead_of_clamping(raw):
    val, msg = opt_trials(raw)
    assert val is None and "2 to 40" in msg


def test_handlers_use_the_checks_and_labels_show_ranges():
    assess = (ROOT / "fansim" / "cockpit" / "fan_assess.py").read_text(encoding="utf-8")
    opt = (ROOT / "fansim" / "cockpit" / "fan_optimize.py").read_text(encoding="utf-8")
    ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "max(2, int(state.sweep_steps))" not in assess and "_check_steps(state.sweep_steps)" in assess
    assert "max(2, min(40, trials))" not in opt and "_check_trials(state.opt_trials)" in opt
    assert 'label="steps (2–12)"' in ui and 'label="Trials (2–40)"' in ui
