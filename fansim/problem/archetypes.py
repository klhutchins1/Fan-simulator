"""Archetype interface + registry. One implemented (axial fan); the rest are explicit stubs.

An Archetype is the pluggable bridge between a machine family and the shared core: it knows how to
sample a design, build its geometry, and evaluate it. The optimizer/study talk only to this
interface, so adding centrifugal/propeller/wind-turbine later is a new Archetype, not an engine
rewrite. The axial-fan archetype delegates to the existing, validated modules (no logic duplicated).
"""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Archetype(ABC):
    """Bridge between a machine family and the geometry->evaluate->optimize core."""

    #: short registry key, e.g. "axial_fan"
    name: str = ""
    #: physics regime hint (informs solver/turbulence choice; see plan physics/regime.py)
    regime: str = "incompressible-RANS-MRF"

    @abstractmethod
    def suggest_design(self, trial, **kwargs) -> Any:
        """Sample a design vector (archetype-specific params object) from an Optuna trial."""

    @abstractmethod
    def build_geometry(self, params, out_path: str | Path):
        """Build printable geometry for ``params``; return the written STL path."""

    @abstractmethod
    def evaluate(self, params, workdir: str | Path, **kwargs):
        """Gate + simulate ``params``; return an ObjectiveResult-like object."""

    @property
    @abstractmethod
    def objective_names(self) -> tuple[str, ...]:
        ...

    @property
    @abstractmethod
    def objective_directions(self) -> tuple[str, ...]:
        ...

    def __repr__(self) -> str:
        return f"<Archetype {self.name!r} regime={self.regime!r}>"


class AxialFanArchetype(Archetype):
    """The implemented archetype: axial PC fan (A12x25 family). Delegates to existing modules."""

    name = "axial_fan"
    regime = "incompressible-RANS-MRF"

    def suggest_design(
        self, trial, *, with_features: bool = False, space: str = "open", **kwargs
    ):
        from fansim.optimize.search_space import suggest_params
        return suggest_params(trial, with_features=with_features, space=space, **kwargs)

    def build_geometry(self, params, out_path: str | Path):
        from fansim.geometry import build_impeller, export_stl
        return export_stl(build_impeller(params), out_path)

    def evaluate(self, params, workdir: str | Path, **kwargs):
        from fansim.optimize.objectives import evaluate_candidate
        return evaluate_candidate(params, workdir, **kwargs)

    @property
    def objective_names(self) -> tuple[str, ...]:
        from fansim.optimize.search_space import OBJECTIVE_NAMES
        return tuple(OBJECTIVE_NAMES)

    @property
    def objective_directions(self) -> tuple[str, ...]:
        from fansim.optimize.search_space import OBJECTIVE_DIRECTIONS
        return tuple(OBJECTIVE_DIRECTIONS)


class _StubArchetype(Archetype):
    """A registered-but-unimplemented archetype: documents the roadmap, fails loudly if used."""

    def __init__(self, name: str, regime: str, note: str):
        self.name, self.regime, self._note = name, regime, note

    def _fail(self):
        raise NotImplementedError(
            f"archetype {self.name!r} is a roadmap stub ({self._note}). The Problem/optimize core "
            "is archetype-agnostic; implement this class (geometry + search space + domain/BC) to "
            "add it -- no engine changes needed.")

    def suggest_design(self, trial, **kwargs):
        self._fail()

    def build_geometry(self, params, out_path):
        self._fail()

    def evaluate(self, params, workdir, **kwargs):
        self._fail()

    @property
    def objective_names(self) -> tuple[str, ...]:
        self._fail()

    @property
    def objective_directions(self) -> tuple[str, ...]:
        self._fail()


# registry: implemented archetypes (stubs removed once each package landed)
_REGISTRY: dict[str, Archetype] = {
    "axial_fan": AxialFanArchetype(),
}

def _register_optional() -> None:
    """Lazy-import package archetypes so a missing optional module doesn't break axial."""
    try:
        from fansim.centrifugal.archetype import MixedFlowArchetype
        _REGISTRY["centrifugal"] = MixedFlowArchetype()
    except Exception:  # noqa: BLE001
        _REGISTRY.setdefault("centrifugal", _StubArchetype(
            "centrifugal", "incompressible-RANS-MRF",
            "radial impeller + volute; high pressure ratio"))
    try:
        from fansim.propeller.archetype import PropellerArchetype
        _REGISTRY["propeller"] = PropellerArchetype()
    except Exception:  # noqa: BLE001
        _REGISTRY.setdefault("propeller", _StubArchetype(
            "propeller", "incompressible/compressible-RANS",
            "open rotor, no duct; thrust/efficiency objectives"))
    try:
        from fansim.wind_turbine.archetype import WindTurbineArchetype
        _REGISTRY["wind_turbine"] = WindTurbineArchetype()
    except Exception:  # noqa: BLE001
        _REGISTRY.setdefault("wind_turbine", _StubArchetype(
            "wind_turbine", "high-Re-BEM+RANS",
            "large blade, BEM+aeroelastic; power coefficient"))
    with contextlib.suppress(Exception):
        from fansim.volute.archetype import VoluteArchetype
        _REGISTRY["volute"] = VoluteArchetype()
    with contextlib.suppress(Exception):
        from fansim.cror.archetype import CrorArchetype
        _REGISTRY["cror"] = CrorArchetype()


_register_optional()


def get_archetype(name: str) -> Archetype:
    """Look up an archetype by registry key (e.g. 'axial_fan'). Raises KeyError with the valid set."""
    # Re-run optional registration: a first-pass import can hit a circular load
    # (centrifugal.archetype → problem.archetypes mid-_register_optional) and leave a stub.
    # Once the package finishes importing, this overwrites the stub with the real class.
    _register_optional()
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown archetype {name!r}; known: {sorted(_REGISTRY)}") from None


def archetype_names() -> list[str]:
    """All registered archetype keys (implemented + roadmap stubs)."""
    return sorted(_REGISTRY)
