"""Generality layer: a config-driven Problem/archetype interface.

Decouples *what machine* (axial fan, centrifugal, propeller, wind turbine) from *how we
simulate/optimize* it. The axial fan is the one implemented archetype; the others are registered
stubs so the roadmap is explicit and they slot into the SAME geometry->evaluate->optimize core with
no engine rewrite (plan Architecture principle #1).
"""

from fansim.problem.archetypes import (
    Archetype,
    AxialFanArchetype,
    archetype_names,
    get_archetype,
)
from fansim.problem.definition import Problem, load_problem

__all__ = [
    "Archetype",
    "AxialFanArchetype",
    "get_archetype",
    "archetype_names",
    "Problem",
    "load_problem",
]
