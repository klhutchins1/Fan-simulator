"""Propeller registry entry: BEMT geometry + optional open-air CFD evaluate."""

from __future__ import annotations

from pathlib import Path

from fansim.geometry.blade import BladeParams
from fansim.problem.archetypes import Archetype
from fansim.prop_spec import PropSpec, get_prop_spec


class PropellerArchetype(Archetype):
    """Open-rotor prop registered as ``propeller``; CFD via ``evaluate_prop_cfd``."""

    name = "propeller"
    regime = "incompressible/compressible-RANS"

    def suggest_design(self, trial, **kwargs) -> BladeParams:
        from fansim.propeller.geometry import prop_blade_params
        from fansim.propeller.optimize import suggest_prop

        spec = kwargs.get("spec")
        if spec is None:
            spec = get_prop_spec(str(kwargs.get("prop_model", "fpv_5inch")))
        if trial is None:
            return prop_blade_params(spec)
        return suggest_prop(trial, spec)

    def build_geometry(self, params, out_path: str | Path, **kwargs):
        """Write a prop STL. ``params`` may be BladeParams or PropSpec."""
        from fansim.geometry import build_impeller, export_stl
        from fansim.propeller.geometry import build_prop, prop_blade_params

        out_path = Path(out_path)
        if isinstance(params, PropSpec):
            build_prop(params, out_path, **kwargs)
            return out_path
        blade = params if isinstance(params, BladeParams) else prop_blade_params(params)
        export_stl(build_impeller(blade), out_path, tolerance=0.02, angular_tolerance=0.1)
        return out_path

    def evaluate(self, params, workdir: str | Path, **kwargs):
        """Open-air prop CFD (or BEMT-only dict when ``bemt_only=True``)."""
        from fansim.propeller.bemt import analyze
        from fansim.propeller.cfd import evaluate_prop_cfd
        from fansim.propeller.geometry import prop_blade_params

        spec = kwargs.pop("spec", None)
        if spec is None:
            spec = get_prop_spec(str(kwargs.pop("prop_model", "fpv_5inch")))
        else:
            kwargs.pop("prop_model", None)
        blade = params if isinstance(params, BladeParams) else prop_blade_params(spec)
        if kwargs.pop("bemt_only", False):
            perf = analyze(blade, rpm=float(kwargs.get("rpm") or spec.rpm_max))
            return {
                "feasible": True,
                "thrust_g": perf.thrust_g,
                "efficiency_g_per_w": perf.efficiency_g_per_w,
                "power_w": perf.power_w,
                "fm": perf.figure_of_merit,
            }
        return evaluate_prop_cfd(spec, workdir, params=blade, **kwargs)

    @property
    def objective_names(self) -> tuple[str, ...]:
        return ("thrust_g", "efficiency_g_per_w")

    @property
    def objective_directions(self) -> tuple[str, ...]:
        return ("maximize", "maximize")
