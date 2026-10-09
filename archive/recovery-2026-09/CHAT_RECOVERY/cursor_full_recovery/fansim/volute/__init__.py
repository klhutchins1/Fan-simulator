"""Volute / radial blower package (geometry + sealed-enclosure radial MRF CFD)."""

from __future__ import annotations

__all__ = [
    "VOLUTE_HONESTY",
    "VoluteArchetype",
    "VoluteParams",
    "build_radial_impeller",
    "build_volute_casing",
    "build_volute_case",
    "domain_for_volute",
    "evaluate_volute",
    "export_volute_impeller_stl",
    "export_volute_preview_stl",
    "export_volute_stls",
    "volute_enclosure_extents_mm",
]


def __getattr__(name: str):
    if name == "VoluteArchetype":
        from fansim.volute.archetype import VoluteArchetype
        return VoluteArchetype
    if name == "evaluate_volute":
        from fansim.volute.evaluate import evaluate_volute
        return evaluate_volute
    if name == "build_volute_case":
        from fansim.volute.case import build_volute_case
        return build_volute_case
    if name == "domain_for_volute":
        from fansim.volute.domain import domain_for_volute
        return domain_for_volute
    if name in {
        "VOLUTE_HONESTY",
        "VoluteParams",
        "build_radial_impeller",
        "build_volute_casing",
        "export_volute_impeller_stl",
        "export_volute_preview_stl",
        "export_volute_stls",
        "volute_enclosure_extents_mm",
    }:
        from fansim.volute import geometry as _geo
        return getattr(_geo, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name}")
