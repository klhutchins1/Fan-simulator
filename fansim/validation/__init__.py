"""Validation helpers (A12x25 reference STL silhouette / CFD wiring)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from fansim.validation.reference_stl import (
        DEFAULT_REFERENCE_STL,
        SilhouetteMetrics,
        measure_silhouette,
        prepare_reference_stl,
        rig_for_reference_stl,
    )

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "DEFAULT_REFERENCE_STL": ("fansim.validation.reference_stl", "DEFAULT_REFERENCE_STL"),
    "SilhouetteMetrics": ("fansim.validation.reference_stl", "SilhouetteMetrics"),
    "measure_silhouette": ("fansim.validation.reference_stl", "measure_silhouette"),
    "prepare_reference_stl": ("fansim.validation.reference_stl", "prepare_reference_stl"),
    "rig_for_reference_stl": ("fansim.validation.reference_stl", "rig_for_reference_stl"),
}


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


__all__ = [
    "DEFAULT_REFERENCE_STL",
    "SilhouetteMetrics",
    "measure_silhouette",
    "prepare_reference_stl",
    "rig_for_reference_stl",
]
