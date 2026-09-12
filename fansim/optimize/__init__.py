# RECOVERED-FROM-CHAT 2026-09-12 + CURSOR overlay
"""Multi-objective optimization of the blade design vector.

Lazy exports so importing ``fansim.optimize.presets`` / ``system_curve`` does not
pull CadQuery/OpenFOAM via ``objectives`` during unit tests.
"""

from __future__ import annotations

__all__ = ["ObjectiveResult", "evaluate_candidate"]


def __getattr__(name: str):
    if name in ("ObjectiveResult", "evaluate_candidate"):
        from fansim.optimize.objectives import ObjectiveResult, evaluate_candidate
        return ObjectiveResult if name == "ObjectiveResult" else evaluate_candidate
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
