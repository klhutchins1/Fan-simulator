"""Centrifugal registry entry: mixed-flow geometry in the A12x25 through-flow envelope."""

from __future__ import annotations

from pathlib import Path

from fansim.centrifugal.geometry import MixedFlowParams, export_mixed_flow_stl
from fansim.problem.archetypes import Archetype


class MixedFlowArchetype(Archetype):
    """Mixed-flow drop-in registered as ``centrifugal``; CFD via ``evaluate_mixed_flow``."""

    name = "centrifugal"
    regime = "incompressible-RANS-MRF"

    def suggest_design(self, trial, **kwargs) -> MixedFlowParams:
        if trial is None:
            return MixedFlowParams()
        n_blades = trial.suggest_int("n_blades", 7, 11)
        stagger = trial.suggest_float("stagger_deg", 25.0, 45.0)
        return MixedFlowParams(n_blades=n_blades, stagger_deg=stagger)

    def build_geometry(self, params, out_path: str | Path):
        return export_mixed_flow_stl(params, out_path)

    def evaluate(self, params, workdir: str | Path, **kwargs):
        from fansim.centrifugal.evaluate import evaluate_mixed_flow
        return evaluate_mixed_flow(params, workdir, **kwargs)

    @property
    def objective_names(self) -> tuple[str, ...]:
        from fansim.optimize.search_space import OBJECTIVE_NAMES
        return tuple(OBJECTIVE_NAMES)

    @property
    def objective_directions(self) -> tuple[str, ...]:
        from fansim.optimize.search_space import OBJECTIVE_DIRECTIONS
        return tuple(OBJECTIVE_DIRECTIONS)
