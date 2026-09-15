"""Compile/import smoke for the Fan tab (§13.1) — must stay importable."""

from __future__ import annotations

import ast
from pathlib import Path


def test_fan_tab_parses():
    root = Path(__file__).resolve().parents[1] / "fansim" / "cockpit"
    for name in ("fan_tab.py", "fan_tab_ui.py", "fan_widgets.py", "fan_copy.py"):
        src = (root / name).read_text(encoding="utf-8")
        ast.parse(src)


def test_placement_exports_impeller_z_extent():
    from fansim.cockpit.placement import impeller_z_extent
    from fansim.geometry.blade import BladeParams

    d = impeller_z_extent(BladeParams())
    assert d > 0.0


def test_impeller_z_extent_includes_hub_nose():
    from fansim.cockpit.placement import blade_z_extent, impeller_z_extent
    from fansim.geometry.blade import BladeParams

    base = BladeParams(hub_height_mm=20.0, hub_nose_mm=0.0)
    tall = BladeParams(hub_height_mm=20.0, hub_nose_mm=8.0)
    assert impeller_z_extent(tall) > impeller_z_extent(base)
    assert impeller_z_extent(tall) >= blade_z_extent(tall)
