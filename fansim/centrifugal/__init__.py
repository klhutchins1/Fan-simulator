"""Mixed-flow (centrifugal registry) geometry + archetype + evaluate."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from fansim.centrifugal.archetype import MixedFlowArchetype
    from fansim.centrifugal.evaluate import evaluate_mixed_flow
    from fansim.centrifugal.geometry import (
        MixedFlowParams,
        build_mixed_flow,
        build_mixed_flow_preview,
        export_mixed_flow_stl,
    )

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "MixedFlowArchetype": ("fansim.centrifugal.archetype", "MixedFlowArchetype"),
    "MixedFlowParams": ("fansim.centrifugal.geometry", "MixedFlowParams"),
    "build_mixed_flow": ("fansim.centrifugal.geometry", "build_mixed_flow"),
    "build_mixed_flow_preview": ("fansim.centrifugal.geometry", "build_mixed_flow_preview"),
    "evaluate_mixed_flow": ("fansim.centrifugal.evaluate", "evaluate_mixed_flow"),
    "export_mixed_flow_stl": ("fansim.centrifugal.geometry", "export_mixed_flow_stl"),
}

__all__ = [
    "MixedFlowArchetype",
    "MixedFlowParams",
    "build_mixed_flow",
    "build_mixed_flow_preview",
    "evaluate_mixed_flow",
    "export_mixed_flow_stl",
]


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod_name, attr_name = target
    val = getattr(importlib.import_module(mod_name), attr_name)
    globals()[name] = val
    return val


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
