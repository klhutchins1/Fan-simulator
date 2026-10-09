"""Wind-turbine registry entry: loft geometry + BEM-lite Cp screen (scaffold)."""

from __future__ import annotations

from pathlib import Path

from fansim.problem.archetypes import Archetype
from fansim.wind_turbine.params import WindTurbineParams


class WindTurbineArchetype(Archetype):
    """HAWT-shaped scaffold registered as ``wind_turbine``."""

    name = "wind_turbine"
    regime = "high-Re-BEM+RANS"

    def suggest_design(self, trial, **kwargs) -> WindTurbineParams:
        if trial is None:
            return WindTurbineParams()
        return WindTurbineParams(
            n_blades=trial.suggest_int("wt_n_blades", 2, 4),
            tip_speed_ratio=trial.suggest_float("wt_tsr", 4.0, 10.0),
            pitch_deg=trial.suggest_float("wt_pitch_deg", 0.0, 12.0),
            freestream_ms=float(kwargs.get("freestream_ms", 8.0)),
            diameter_m=float(kwargs.get("diameter_m", 0.20)),
            hub_radius_m=float(kwargs.get("hub_radius_m", 0.025)),
        )

    def build_geometry(self, params, out_path: str | Path, **kwargs):
        from fansim.wind_turbine.geometry import export_wind_turbine_stl

        if not isinstance(params, WindTurbineParams):
            raise TypeError(f"expected WindTurbineParams, got {type(params)!r}")
        return export_wind_turbine_stl(params, out_path)

    def evaluate(self, params, workdir: str | Path, **kwargs):
        from fansim.wind_turbine.evaluate import evaluate_wind_turbine

        if not isinstance(params, WindTurbineParams):
            raise TypeError(f"expected WindTurbineParams, got {type(params)!r}")
        return evaluate_wind_turbine(params, workdir, **kwargs)

    @property
    def objective_names(self) -> tuple[str, ...]:
        return ("Cp", "power_w")

    @property
    def objective_directions(self) -> tuple[str, ...]:
        return ("maximize", "maximize")
