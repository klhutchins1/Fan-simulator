# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Tests for the generality layer (fansim.problem): registry, archetype wiring, Problem loading."""

from pathlib import Path

import pytest

from fansim.problem import (
    AxialFanArchetype,
    archetype_names,
    get_archetype,
    load_problem,
)
from fansim.problem.definition import Objective, Problem, problem_from_dict

PROBLEMS = Path(__file__).resolve().parent.parent / "config" / "problems"


def test_registry_has_axial_and_stubs():
    names = archetype_names()
    assert "axial_fan" in names
    for stub in ("centrifugal", "propeller", "wind_turbine"):
        assert stub in names


def test_get_archetype_unknown_raises():
    with pytest.raises(KeyError):
        get_archetype("warp_drive")


def test_axial_archetype_exposes_objectives():
    a = get_archetype("axial_fan")
    assert isinstance(a, AxialFanArchetype)
    assert a.objective_names == ("cfm_free", "cfm_load", "efficiency")
    assert set(a.objective_directions) == {"maximize"}


def test_axial_archetype_builds_geometry(tmp_path):
    """The axial archetype delegates to the real geometry engine and writes a watertight STL."""
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    a = get_archetype("axial_fan")
    st = optuna.create_study()
    st.optimize(lambda t: (a.suggest_design(t), 0.0)[1], n_trials=1)
    # rebuild the sampled design and let the archetype write its geometry
    from fansim.optimize.search_space import blade_from_flat
    stl = a.build_geometry(blade_from_flat(st.trials[0].params), tmp_path / "imp.stl")
    assert Path(stl).exists() and Path(stl).stat().st_size > 0


def test_stub_archetype_fails_loudly():
    stub = get_archetype("centrifugal")
    with pytest.raises(NotImplementedError):
        stub.suggest_design(None)


def test_problem_from_dict_validates():
    p = problem_from_dict({
        "name": "t", "archetype": "axial_fan",
        "objectives": [{"name": "cfm_free", "direction": "maximize"}],
        "operating_points": [{"name": "free", "back_pressure_pa": 0.0}],
    })
    assert isinstance(p, Problem)
    assert p.objective_names == ("cfm_free",)
    assert p.get_archetype().name == "axial_fan"


def test_problem_rejects_bad_archetype_and_direction():
    with pytest.raises(ValueError):
        problem_from_dict({"name": "x", "archetype": "nope",
                           "objectives": [{"name": "a", "direction": "maximize"}]})
    with pytest.raises(ValueError):
        Problem(name="x", archetype="axial_fan",
                objectives=[Objective("a", "sideways")]).validate()


def test_load_bundled_axial_problem():
    p = load_problem(PROBLEMS / "axial_fan_a12x25.yaml")
    assert p.archetype == "axial_fan"
    assert p.objective_names == ("cfm_free", "cfm_load", "efficiency")
    assert [op.name for op in p.operating_points] == ["free", "load"]
    assert p.constraints["envelope_dia_mm"] == 119.0
