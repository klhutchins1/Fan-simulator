"""Validation helpers (A12x25 reference STL silhouette / CFD wiring)."""

from fansim.validation.reference_stl import (
    DEFAULT_REFERENCE_STL,
    SilhouetteMetrics,
    measure_silhouette,
    prepare_reference_stl,
    rig_for_reference_stl,
)

__all__ = [
    "DEFAULT_REFERENCE_STL",
    "SilhouetteMetrics",
    "measure_silhouette",
    "prepare_reference_stl",
    "rig_for_reference_stl",
]
