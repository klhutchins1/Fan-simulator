"""Span loft: linear (default) vs optional PCHIP smooth curves."""

from __future__ import annotations

import numpy as np

from fansim.geometry.blade import BladeParams, RadialStation, _interp_stations
from fansim.optimize.search_space import blade_from_flat


def _skew_kink_params(*, mode: str) -> BladeParams:
    """Hub/tip skew 0, mid skew 6 — classic linear elbow case."""
    return BladeParams(
        span_interp=mode,
        stations=[
            RadialStation(0.0, 34.0, 26.0, thickness=0.08, max_camber=0.05, skew=0.0),
            RadialStation(0.5, 44.0, 26.0, thickness=0.05, max_camber=0.06, skew=6.0),
            RadialStation(1.0, 38.0, 22.0, thickness=0.03, max_camber=0.06, skew=0.0),
        ],
    )


def _mid_slope_break(y: np.ndarray, q: np.ndarray) -> float:
    i = int(np.argmin(np.abs(q - 0.5)))
    i = min(max(i, 1), len(q) - 2)
    dl = (y[i] - y[i - 1]) / (q[i] - q[i - 1])
    dr = (y[i + 1] - y[i]) / (q[i + 1] - q[i])
    return abs(dl - dr)


def test_default_span_interp_is_linear():
    assert BladeParams().span_interp == "linear"


def test_linear_span_interp_hits_midpoint_blend():
    p = _skew_kink_params(mode="linear")
    it = _interp_stations(p, 21)
    # r=0.25 → half of mid skew on a linear hub→mid segment
    assert abs(float(np.interp(0.25, it["r_frac"], it["skew"])) - 3.0) < 1e-9
    assert abs(float(np.interp(0.5, it["r_frac"], it["skew"])) - 6.0) < 1e-9


def test_pchip_smooths_mid_skew_kink():
    n = 41
    lin = _interp_stations(_skew_kink_params(mode="linear"), n)
    pch = _interp_stations(_skew_kink_params(mode="pchip"), n)
    # Still passes through the control mid
    assert abs(float(np.interp(0.5, pch["r_frac"], pch["skew"])) - 6.0) < 1e-6
    assert _mid_slope_break(pch["skew"], pch["r_frac"]) < 0.5 * _mid_slope_break(
        lin["skew"], lin["r_frac"]
    )


def test_blade_from_flat_span_interp():
    base = dict(
        n_blades=7, chord_root=34, chord_mid=44, chord_tip=38,
        stagger_root=26, stagger_mid=26, stagger_tip=22,
        max_camber=0.05, sweep_mid=3.0, sweep_tip=5.0,
    )
    assert blade_from_flat(base).span_interp == "linear"
    assert blade_from_flat({**base, "span_interp": "pchip"}).span_interp == "pchip"
    assert blade_from_flat({**base, "span_interp": "nope"}).span_interp == "linear"


def test_config_roundtrip_span_interp(tmp_path):
    from fansim.geometry.config import load_blade_params, save_blade_params

    p = _skew_kink_params(mode="pchip")
    path = save_blade_params(p, tmp_path / "smooth.yaml")
    reloaded = load_blade_params(path)
    assert reloaded.span_interp == "pchip"
    assert reloaded.stations[1].skew == 6.0
