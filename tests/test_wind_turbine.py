"""Wind-turbine archetype scaffold — registry wiring, BEM-lite screen (no RANS)."""

from __future__ import annotations

import math

import pytest

from fansim.problem import get_archetype
from fansim.wind_turbine.evaluate import WIND_TURBINE_HONESTY, evaluate_wind_turbine
from fansim.wind_turbine.params import WindTurbineParams


def test_wind_turbine_params_defaults():
    p = WindTurbineParams()
    assert p.diameter_m > 0
    assert p.hub_radius_m < p.diameter_m / 2
    assert p.n_blades >= 2
    assert p.tip_speed_ratio > 0
    assert p.freestream_ms > 0


def test_evaluate_returns_cp_and_power_below_betz():
    res = evaluate_wind_turbine(WindTurbineParams())
    assert res["feasible"] is True
    assert 0.0 < res["Cp"] < 16.0 / 27.0
    assert res["power_w"] > 0.0
    assert res["raw"]["honesty"] == WIND_TURBINE_HONESTY


def test_evaluate_responds_to_tsr():
    good = evaluate_wind_turbine(WindTurbineParams(tip_speed_ratio=7.0))
    bad = evaluate_wind_turbine(WindTurbineParams(tip_speed_ratio=1.0))
    assert good["Cp"] > bad["Cp"]


def test_archetype_is_wired():
    from fansim.wind_turbine.archetype import WindTurbineArchetype

    a = get_archetype("wind_turbine")
    assert isinstance(a, WindTurbineArchetype)
    assert a.objective_names == ("Cp", "power_w")
    assert a.objective_directions == ("maximize", "maximize")
    params = a.suggest_design(None)
    assert isinstance(params, WindTurbineParams)
    out = a.evaluate(params, workdir=".")
    assert out["Cp"] > 0


def test_blade_params_from_wind_fit_envelope():
    from fansim.wind_turbine.geometry import blade_params_from_wind

    bp = blade_params_from_wind(WindTurbineParams())
    assert bp.n_blades == 3
    assert bp.tip_radius == pytest.approx(100.0)  # 0.2 m diameter → 100 mm R
    assert bp.hub_radius < bp.tip_radius
    # turbine: root stagger steeper than tip (extracting twist)
    assert bp.stations[0].stagger_deg > bp.stations[-1].stagger_deg


@pytest.mark.slow
def test_archetype_builds_stl(tmp_path):
    a = get_archetype("wind_turbine")
    params = a.suggest_design(None)
    stl = a.build_geometry(params, tmp_path / "wt.stl")
    assert stl.exists() and stl.stat().st_size > 1000
