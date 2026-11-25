"""R2.7: experimental label on Mixed / Volute / Prop-CFD / CROR — not Fan or Prop BEMT."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = "Experimental: not validated against published data."


def test_app_tabs_use_experimental_names_and_standard_tooltip():
    app = (ROOT / "fansim/cockpit/app.py").read_text(encoding="utf-8")
    assert 'VTab(\n                                "Mixed · experimental"' in app or '"Mixed · experimental"' in app
    assert '"Volute · experimental"' in app
    assert '"CROR · experimental"' in app
    assert '"Volute · estimate"' not in app
    assert '"CROR · estimate"' not in app
    # Prop BEMT tab name stays a fast estimate; CFD honesty is in the tooltip.
    assert '"Prop · fast estimate"' in app
    assert "EXPERIMENTAL_LABEL" in app
    assert LABEL in (ROOT / "fansim/cockpit/experimental.py").read_text(encoding="utf-8")
    # Fan tab must not carry the experimental stamp in its name.
    assert '"Fan · blades"' in app
    assert "Fan · experimental" not in app


def test_volute_and_cror_and_prop_cfd_carry_standard_label():
    volute = (ROOT / "fansim/cockpit/volute_tab.py").read_text(encoding="utf-8")
    cror = (ROOT / "fansim/cockpit/cror_tab.py").read_text(encoding="utf-8")
    prop = (ROOT / "fansim/cockpit/prop_tab.py").read_text(encoding="utf-8")
    honesty = (ROOT / "fansim/propeller/honesty.py").read_text(encoding="utf-8")
    exp = (ROOT / "fansim/cockpit/experimental.py").read_text(encoding="utf-8")
    assert "EXPERIMENTAL_LABEL" in exp and LABEL in exp
    assert "EXPERIMENTAL_LABEL" in volute
    assert "EXPERIMENTAL_LABEL" in cror
    # Prop CFD honesty carries the standard words; prop_tab imports PROP_CFD_HONESTY.
    assert LABEL.rstrip(".") in honesty
    assert "PROP_CFD_HONESTY" in prop
    assert "Analyze" in prop


def test_readme_known_limits_has_one_line_per_surface():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Known limits" in text
    for surface in ("Mixed", "Volute", "Prop CFD", "CROR"):
        assert surface in text
    assert LABEL in text or LABEL.rstrip(".") in text
    assert "nothing printed or measured yet" not in text.lower()


def test_simple_mode_gates_still_hide_experimental_tabs():
    src = (ROOT / "tests/test_simple_mode_copy.py").read_text(encoding="utf-8")
    assert '"Volute · experimental"' in src
    assert '"CROR · experimental"' in src
