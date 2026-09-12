# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Manufacturability constraints and filament material properties."""

from fansim.manufacturability.materials import MATERIALS, Material
from fansim.manufacturability.fdm_rules import PrintabilityReport, check_printability

__all__ = ["MATERIALS", "Material", "PrintabilityReport", "check_printability"]
