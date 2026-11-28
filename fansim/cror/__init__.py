"""Counter-rotating stacked rotors (roadmap §4.2) — geometry scaffold."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from fansim.cror.archetype import CrorArchetype
    from fansim.cror.geometry import CrorParams, build_cror, export_cror_stl

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "CrorArchetype": ("fansim.cror.archetype", "CrorArchetype"),
    "CrorParams": ("fansim.cror.geometry", "CrorParams"),
    "build_cror": ("fansim.cror.geometry", "build_cror"),
    "export_cror_stl": ("fansim.cror.geometry", "export_cror_stl"),
}

__all__ = ["CrorArchetype", "CrorParams", "build_cror", "export_cror_stl"]


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
