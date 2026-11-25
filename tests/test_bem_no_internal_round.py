"""#50: BEM/BEMT must not round inside the maths (display may)."""
from __future__ import annotations

import math

from fansim.fan_bem import operating_point
from fansim.geometry.config import load_blade_params
from fansim.prop_spec import get_prop_spec
from fansim.propeller import prop_blade_params
from fansim.propeller.bemt import analyze


def _has_sub_round(x: float, ndigits: int) -> bool:
    return not math.isclose(x, round(x, ndigits), rel_tol=0.0, abs_tol=0.0)


def test_fan_bem_operating_point_keeps_sub_round_precision():
    p = load_blade_params("config/problems/a12x25_reference_planar.yaml")
    tip_r = p.tip_radius / 1000.0
    hub_r = p.hub_radius / 1000.0
    area = math.pi * (tip_r * tip_r - hub_r * hub_r)
    q = 0.25 * (2000.0 * 2.0 * math.pi / 60.0) * tip_r * area
    pt = operating_point(p, 2000.0, q)
    kept = (
        _has_sub_round(pt.flow_cfm, 1)
        or _has_sub_round(pt.dp_static_pa, 2)
        or _has_sub_round(pt.efficiency, 3)
        or _has_sub_round(pt.power_w, 2)
    )
    assert kept, (
        f"all fields still look pre-rounded: cfm={pt.flow_cfm} "
        f"dp={pt.dp_static_pa} eta={pt.efficiency} P={pt.power_w}"
    )


def test_bemt_analyze_keeps_sub_round_precision():
    p = prop_blade_params(get_prop_spec("fpv_5inch"))
    r = analyze(p, rpm=30000)
    kept = (
        _has_sub_round(r.thrust_n, 3)
        or _has_sub_round(r.power_w, 1)
        or _has_sub_round(r.figure_of_merit_raw, 4)
    )
    assert kept, (
        f"all fields still look pre-rounded: T={r.thrust_n} "
        f"P={r.power_w} FM_raw={r.figure_of_merit_raw}"
    )
