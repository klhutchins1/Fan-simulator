from __future__ import annotations

import pytest

pytest.importorskip("pythrust")

pytestmark = pytest.mark.propulsion


def test_catalog_solve_apc_5x45_feasible():
    from fansim.propeller.power import solve_catalog_operating_point

    out = solve_catalog_operating_point(
        motor={
            "kv_rpm_per_v": 1900.0,
            "resistance_ohm": 0.05,
            "no_load_current_a": 1.0,
            "current_max_a": 40.0,
        },
        battery_voltage_v=22.2,
        diameter_in=5.0,
        pitch_in=4.5,
        throttle=0.7,
        airspeed_mps=0.0,
    )
    assert out["source"] == "pythrust"
    assert out["pythrust_version"] == "0.2.3"
    assert out["is_feasible"] is True
    assert out["thrust_n"] > 0.0
    assert out["rpm"] > 1000.0
    assert out["prop_id"]
