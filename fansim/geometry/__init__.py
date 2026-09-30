"""Parametric blade geometry generation."""

from fansim.geometry.blade import (
    BladeParams,
    RadialStation,
    blade_solidity,
    build_impeller,
    set_uneven_spacing,
)
from fansim.geometry.export import export_stl, export_step, watertight_report
from fansim.geometry.handedness import (
    cfd_spin_for_omega,
    handedness_variants,
    mirror_blade_params,
)

__all__ = [
    "BladeParams",
    "RadialStation",
    "blade_solidity",
    "build_impeller",
    "set_uneven_spacing",
    "export_stl",
    "export_step",
    "watertight_report",
    "mirror_blade_params",
    "handedness_variants",
    "cfd_spin_for_omega",
]
