"""R1.4: state the Stock recipe's ~5 % gap; Simple mode shows nothing extra."""
from pathlib import Path

PHRASE = "about 5 % less airflow than the real A12x25"
ROOT = Path(__file__).resolve().parents[1]


def test_readme_known_limits_state_the_stock_gap():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Known limits" in text
    assert PHRASE in text


def test_stock_expert_copy_states_the_gap():
    from fansim.cockpit.fan_trials import STOCK_RECIPE_GAP

    assert PHRASE in STOCK_RECIPE_GAP
    assert "55.7 vs 58.3 CFM" in STOCK_RECIPE_GAP
    ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "STOCK_RECIPE_GAP" in ui
    assert "ui_mode === 'expert'" in ui
    assert "stale_msg" in ui
    # The gap must not ride on stale_msg (that alert is visible in Simple).
    stale = (ROOT / "fansim" / "cockpit" / "fan_trials.py").read_text(encoding="utf-8")
    assert PHRASE not in stale.split("state.stale_msg", 1)[1].split("session._clear_airflow", 1)[0]
