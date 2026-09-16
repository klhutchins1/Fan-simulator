"""Problem definition: the config-driven bundle {archetype, operating points, objectives, constraints}.

A Problem is what you hand the engine: which machine family (archetype), at which operating points,
optimizing which objectives, under which constraints. Loaded from a YAML in config/problems/ so a new
study is a config, not code. Validates against the archetype registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fansim.problem.archetypes import Archetype, archetype_names, get_archetype

_VALID_DIRECTIONS = {"maximize", "minimize"}


@dataclass
class OperatingPoint:
    """One duty point in the fan/turbo map (e.g. free delivery, or a fixed back-pressure load)."""
    name: str
    back_pressure_pa: float = 0.0


@dataclass
class Objective:
    name: str
    direction: str = "maximize"


@dataclass
class Problem:
    """A complete problem statement the optimizer/study can run."""
    name: str
    archetype: str
    operating_points: list[OperatingPoint] = field(default_factory=list)
    objectives: list[Objective] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    search_space: str = "open"
    regime: str | None = None
    notes: str = ""

    def get_archetype(self) -> Archetype:
        return get_archetype(self.archetype)

    def validate(self) -> "Problem":
        if self.archetype not in archetype_names():
            raise ValueError(f"unknown archetype {self.archetype!r}; known: {archetype_names()}")
        if not self.objectives:
            raise ValueError(f"problem {self.name!r} has no objectives")
        for o in self.objectives:
            if o.direction not in _VALID_DIRECTIONS:
                raise ValueError(f"objective {o.name!r}: direction {o.direction!r} "
                                 f"not in {_VALID_DIRECTIONS}")
        if self.search_space not in ("open", "guided", "guided_lc"):
            raise ValueError(f"unknown search_space {self.search_space!r}")
        return self

    @property
    def objective_names(self) -> tuple[str, ...]:
        return tuple(o.name for o in self.objectives)

    @property
    def objective_directions(self) -> tuple[str, ...]:
        return tuple(o.direction for o in self.objectives)


def problem_from_dict(d: dict) -> Problem:
    """Build (and validate) a Problem from a plain dict (e.g. parsed YAML)."""
    ops = [OperatingPoint(**op) if isinstance(op, dict) else OperatingPoint(op)
           for op in d.get("operating_points", [])]
    objs = [Objective(**ob) if isinstance(ob, dict) else Objective(ob)
            for ob in d.get("objectives", [])]
    p = Problem(
        name=d["name"],
        archetype=d["archetype"],
        operating_points=ops,
        objectives=objs,
        constraints=dict(d.get("constraints", {})),
        search_space=d.get("search_space", "open"),
        regime=d.get("regime"),
        notes=d.get("notes", ""),
    )
    return p.validate()


def load_problem(path: str | Path) -> Problem:
    """Load and validate a Problem from a YAML file in config/problems/."""
    import yaml

    data = yaml.safe_load(Path(path).read_text())
    return problem_from_dict(data)
