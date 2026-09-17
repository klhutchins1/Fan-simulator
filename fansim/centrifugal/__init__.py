"""Mixed-flow (centrifugal registry) geometry + archetype + evaluate."""

from fansim.centrifugal.geometry import (
    MixedFlowParams,
    build_mixed_flow,
    build_mixed_flow_preview,
    export_mixed_flow_stl,
)

__all__ = [
    "MixedFlowArchetype",
    "MixedFlowParams",
    "build_mixed_flow",
    "build_mixed_flow_preview",
    "evaluate_mixed_flow",
    "export_mixed_flow_stl",
]


def __getattr__(name: str):
    if name == "MixedFlowArchetype":
        from fansim.centrifugal.archetype import MixedFlowArchetype
        return MixedFlowArchetype
    if name == "evaluate_mixed_flow":
        from fansim.centrifugal.evaluate import evaluate_mixed_flow
        return evaluate_mixed_flow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
