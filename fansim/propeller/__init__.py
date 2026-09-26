"""Drone-propeller archetype: prop-appropriate geometry + (later) thrust-based evaluation.

Reuses the shared blade/loft/impeller core — a prop is a few-blade, high-pitch, thin-airfoil variant
with propeller twist (blade angle set by geometric pitch: high at the root, low at the tip) and a small
shaft-mount hub instead of a big motor cup. See fansim/prop_spec.py for the sizes/mounts.
"""

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

__all__ = [
    "BAND_REL_A3",
    "approximate_prop_blade",
    "bemt_static_ct_cp",
    "load_uiuc_static_fixture",
    "compare_bemt_to_static_witness",
    "run_bemt_catalog_quorum",
    "PropDirection",
    "BUILDER_DIRECTION",
    "chirality_hint_from_name",
    "prop_direction",
    "resolve_prop_direction",
    "prop_blade_params",
    "build_prop",
    "build_prop_preview",
    "hover_power_budget",
    "PropulsionExtraMissing",
    "pythrust_available",
    "list_catalog_props",
    "find_catalog_prop",
    "solve_catalog_operating_point",
    "CSV_HEADER",
    "default_export_grid",
    "export_bemt_pythrust_catalog",
    "prop_id_for_export",
    "PropStlMetrics",
    "prepare_prop_stl",
    "measure_prop_stl",
    "spin_hint_from_name",
]
