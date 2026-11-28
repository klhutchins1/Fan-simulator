"""Drone-propeller archetype: prop-appropriate geometry + (later) thrust-based evaluation.

Reuses the shared blade/loft/impeller core — a prop is a few-blade, high-pitch, thin-airfoil variant
with propeller twist (blade angle set by geometric pitch: high at the root, low at the tip) and a small
shaft-mount hub instead of a big motor cup. See fansim/prop_spec.py for the sizes/mounts.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from fansim.propeller.bemt_catalog import (
        BAND_REL_A3,
        approximate_prop_blade,
        bemt_static_ct_cp,
        compare_bemt_to_static_witness,
        load_uiuc_static_fixture,
        run_bemt_catalog_quorum,
    )
    from fansim.propeller.direction import (
        BUILDER_DIRECTION,
        PropDirection,
        chirality_hint_from_name,
        prop_direction,
        resolve_prop_direction,
    )
    from fansim.propeller.geometry import build_prop, build_prop_preview, prop_blade_params
    from fansim.propeller.power import (
        PropulsionExtraMissing,
        find_catalog_prop,
        hover_power_budget,
        list_catalog_props,
        pythrust_available,
        solve_catalog_operating_point,
    )
    from fansim.propeller.pythrust_export import (
        CSV_HEADER,
        default_export_grid,
        export_bemt_pythrust_catalog,
        prop_id_for_export,
    )
    from fansim.propeller.stl_import import (
        PropStlMetrics,
        measure_prop_stl,
        prepare_prop_stl,
        spin_hint_from_name,
    )

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "BAND_REL_A3": ("fansim.propeller.bemt_catalog", "BAND_REL_A3"),
    "approximate_prop_blade": ("fansim.propeller.bemt_catalog", "approximate_prop_blade"),
    "bemt_static_ct_cp": ("fansim.propeller.bemt_catalog", "bemt_static_ct_cp"),
    "load_uiuc_static_fixture": ("fansim.propeller.bemt_catalog", "load_uiuc_static_fixture"),
    "compare_bemt_to_static_witness": ("fansim.propeller.bemt_catalog", "compare_bemt_to_static_witness"),
    "run_bemt_catalog_quorum": ("fansim.propeller.bemt_catalog", "run_bemt_catalog_quorum"),
    "PropDirection": ("fansim.propeller.direction", "PropDirection"),
    "BUILDER_DIRECTION": ("fansim.propeller.direction", "BUILDER_DIRECTION"),
    "chirality_hint_from_name": ("fansim.propeller.direction", "chirality_hint_from_name"),
    "prop_direction": ("fansim.propeller.direction", "prop_direction"),
    "resolve_prop_direction": ("fansim.propeller.direction", "resolve_prop_direction"),
    "prop_blade_params": ("fansim.propeller.geometry", "prop_blade_params"),
    "build_prop": ("fansim.propeller.geometry", "build_prop"),
    "build_prop_preview": ("fansim.propeller.geometry", "build_prop_preview"),
    "hover_power_budget": ("fansim.propeller.power", "hover_power_budget"),
    "PropulsionExtraMissing": ("fansim.propeller.power", "PropulsionExtraMissing"),
    "pythrust_available": ("fansim.propeller.power", "pythrust_available"),
    "list_catalog_props": ("fansim.propeller.power", "list_catalog_props"),
    "find_catalog_prop": ("fansim.propeller.power", "find_catalog_prop"),
    "solve_catalog_operating_point": ("fansim.propeller.power", "solve_catalog_operating_point"),
    "CSV_HEADER": ("fansim.propeller.pythrust_export", "CSV_HEADER"),
    "default_export_grid": ("fansim.propeller.pythrust_export", "default_export_grid"),
    "export_bemt_pythrust_catalog": ("fansim.propeller.pythrust_export", "export_bemt_pythrust_catalog"),
    "prop_id_for_export": ("fansim.propeller.pythrust_export", "prop_id_for_export"),
    "PropStlMetrics": ("fansim.propeller.stl_import", "PropStlMetrics"),
    "prepare_prop_stl": ("fansim.propeller.stl_import", "prepare_prop_stl"),
    "measure_prop_stl": ("fansim.propeller.stl_import", "measure_prop_stl"),
    "spin_hint_from_name": ("fansim.propeller.stl_import", "spin_hint_from_name"),
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
    "BAND_REL_A3",
    "BUILDER_DIRECTION",
    "CSV_HEADER",
    "PropDirection",
    "PropStlMetrics",
    "PropulsionExtraMissing",
    "approximate_prop_blade",
    "bemt_static_ct_cp",
    "build_prop",
    "build_prop_preview",
    "chirality_hint_from_name",
    "compare_bemt_to_static_witness",
    "default_export_grid",
    "export_bemt_pythrust_catalog",
    "find_catalog_prop",
    "hover_power_budget",
    "list_catalog_props",
    "load_uiuc_static_fixture",
    "measure_prop_stl",
    "prepare_prop_stl",
    "prop_blade_params",
    "prop_direction",
    "prop_id_for_export",
    "pythrust_available",
    "resolve_prop_direction",
    "run_bemt_catalog_quorum",
    "solve_catalog_operating_point",
    "spin_hint_from_name",
]
