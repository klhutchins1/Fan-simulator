"""Drone-propeller archetype: prop-appropriate geometry + (later) thrust-based evaluation.

Reuses the shared blade/loft/impeller core — a prop is a few-blade, high-pitch, thin-airfoil variant
with propeller twist (blade angle set by geometric pitch: high at the root, low at the tip) and a small
shaft-mount hub instead of a big motor cup. See fansim/prop_spec.py for the sizes/mounts.
"""

from fansim.propeller.geometry import build_prop, build_prop_preview, prop_blade_params
from fansim.propeller.power import (
    PropulsionExtraMissing,
    find_catalog_prop,
    hover_power_budget,
    list_catalog_props,
    pythrust_available,
    solve_catalog_operating_point,
)

__all__ = [
    "prop_blade_params",
    "build_prop",
    "build_prop_preview",
    "hover_power_budget",
    "PropulsionExtraMissing",
    "pythrust_available",
    "list_catalog_props",
    "find_catalog_prop",
    "solve_catalog_operating_point",
]
