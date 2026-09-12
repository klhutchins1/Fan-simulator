"""CROR archetype: geometry + dual-MRF evaluate (roadmap §4.2 stage 1)."""

from __future__ import annotations

from pathlib import Path

from fansim.cror.evaluate import evaluate_cror
from fansim.cror.geometry import CrorParams, export_cror_stl
from fansim.problem.archetypes import Archetype


class CrorArchetype(Archetype):
    name = "cror"
    regime = "incompressible-RANS-dual-MRF"

    def suggest_design(self, trial, **kwargs) -> CrorParams:
        if trial is None:
            return CrorParams()
        n_f = trial.suggest_int("cror_n_front", 5, 9)
        n_r = trial.suggest_int("cror_n_rear", 6, 11)
        gap = trial.suggest_float("cror_gap_mm", 4.0, 12.0)
        stag = trial.suggest_float("cror_stagger", 28.0, 48.0)
        from fansim.cror.geometry import _default_stations
        from fansim.geometry.blade import BladeParams
        front = BladeParams(n_blades=n_f, stations=_default_stations(stagger=stag))
        rear = BladeParams(n_blades=n_r, stations=_default_stations(stagger=stag))
        return CrorParams(front=front, rear=rear, axial_gap_mm=gap)

    def build_geometry(self, params, out_path: str | Path):
        return export_cror_stl(params, out_path)

    def evaluate(self, params, workdir: str | Path, **kwargs):
        return evaluate_cror(params, workdir, **kwargs)

    @property
    def objective_names(self) -> tuple[str, ...]:
        from fansim.optimize.search_space import OBJECTIVE_NAMES
        return tuple(OBJECTIVE_NAMES)

    @property
    def objective_directions(self) -> tuple[str, ...]:
        from fansim.optimize.search_space import OBJECTIVE_DIRECTIONS
        return tuple(OBJECTIVE_DIRECTIONS)
