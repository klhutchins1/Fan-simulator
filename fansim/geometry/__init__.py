# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Parametric blade geometry generation."""

from fansim.geometry.blade import (
    BladeParams,
    RadialStation,
    blade_solidity,
    build_impeller,
    set_uneven_spacing,
)
from fansim.geometry.export import export_stl, watertight_report

__all__ = [
    "BladeParams",
    "RadialStation",
    "blade_solidity",
    "build_impeller",
    "set_uneven_spacing",
    "export_stl",
    "watertight_report",
]
