"""Parametric blade geometry generation."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from fansim.geometry.blade import (
        BladeParams,
        RadialStation,
        blade_solidity,
        build_impeller,
        set_uneven_spacing,
    )
    from fansim.geometry.export import export_step, export_stl, watertight_report
    from fansim.geometry.handedness import (
        cfd_spin_for_omega,
        handedness_variants,
        mirror_blade_params,
    )

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "BladeParams": ("fansim.geometry.blade", "BladeParams"),
    "RadialStation": ("fansim.geometry.blade", "RadialStation"),
    "blade_solidity": ("fansim.geometry.blade", "blade_solidity"),
    "build_impeller": ("fansim.geometry.blade", "build_impeller"),
    "cfd_spin_for_omega": ("fansim.geometry.handedness", "cfd_spin_for_omega"),
    "export_step": ("fansim.geometry.export", "export_step"),
    "export_stl": ("fansim.geometry.export", "export_stl"),
    "handedness_variants": ("fansim.geometry.handedness", "handedness_variants"),
    "mirror_blade_params": ("fansim.geometry.handedness", "mirror_blade_params"),
    "set_uneven_spacing": ("fansim.geometry.blade", "set_uneven_spacing"),
    "watertight_report": ("fansim.geometry.export", "watertight_report"),
}

__all__ = [
    "BladeParams",
    "RadialStation",
    "blade_solidity",
    "build_impeller",
    "cfd_spin_for_omega",
    "export_step",
    "export_stl",
    "handedness_variants",
    "mirror_blade_params",
    "set_uneven_spacing",
    "watertight_report",
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
