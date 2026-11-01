"""R1.11 / UI-31: cockpit Optimize must not rank designs with synthetic_label."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cockpit_optimize_does_not_wire_surrogate_guided_state():
    src = (ROOT / "fansim" / "cockpit" / "fan_optimize.py").read_text(encoding="utf-8")
    assert "surrogate_guided=bool(state.opt_surrogate_guided)" not in src
    assert "surrogate_guided=False" in src


def test_surrogate_guided_switch_is_hidden_from_the_cockpit():
    ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "opt_surrogate_guided" not in ui
    assert "Surrogate-guided" not in ui
