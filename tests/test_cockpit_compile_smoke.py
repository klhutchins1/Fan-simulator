"""Compile/import smoke for every cockpit tab + app (§13.2)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "fansim" / "cockpit"

_TAB_MODULES = (
    "app.py",
    "diagrams.py",
    "home_tab.py",
    "fan_tab.py",
    "fan_tab_ui.py",
    "fan_widgets.py",
    "fan_copy.py",
    "prop_tab.py",
    "mixed_tab.py",
    "cror_tab.py",
    "volute_tab.py",
)


def test_cockpit_modules_parse():
    missing = []
    for name in _TAB_MODULES:
        path = ROOT / name
        if not path.is_file():
            missing.append(name)
            continue
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert not missing, f"missing cockpit modules: {missing}"
