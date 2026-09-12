"""Shared optimization objective key names.

Keep this module import-light: tests and helper modules should be able to reference the
objective keys without importing geometry/CAD-kernel dependencies transitively.
"""

from __future__ import annotations

OBJECTIVE_NAMES = ("cfm_free", "cfm_load", "efficiency")
