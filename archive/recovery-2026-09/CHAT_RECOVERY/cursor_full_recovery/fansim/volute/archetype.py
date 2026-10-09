"""Volute / radial blower archetype — geometry + radial MRF evaluate (stage 1)."""

from __future__ import annotations

from pathlib import Path

from fansim.problem.archetypes import Archetype
from fansim.volute.geometry import VoluteParams, export_volute_impeller_stl


class VoluteArchetype(Archetype):
    name = "volute"
    regime = "incompressible-RANS-volute"

    def suggest_design(self, trial, **kwargs) -> VoluteParams:
        if trial is None:
            return VoluteParams()
        return VoluteParams(
            n_blades=trial.suggest_int("volute_n_blades", 5, 11),
            r_hub_mm=trial.suggest_float("volute_r_hub", 14.0, 24.0),
            r_tip_mm=trial.suggest_float("volute_r_tip", 40.0, 55.0),
            blade_height_mm=trial.suggest_float("volute_blade_h", 14.0, 28.0),
            spiral_growth_mm=trial.suggest_float("volute_spiral", 15.0, 35.0),
        )

    def build_geometry(self, params, out_path: str | Path):
        return export_volute_impeller_stl(params, out_path)

    def evaluate(self, params, workdir: str | Path, **kwargs):
        from fansim.volute.evaluate import evaluate_volute
        return evaluate_volute(params, workdir, **kwargs)

    @property
    def objective_names(self) -> tuple[str, ...]:
        from fansim.optimize.search_space import OBJECTIVE_NAMES
        return tuple(OBJECTIVE_NAMES)

    @property
    def objective_directions(self) -> tuple[str, ...]:
        from fansim.optimize.search_space import OBJECTIVE_DIRECTIONS
        return tuple(OBJECTIVE_DIRECTIONS)
