"""Impossible fans raise a clear ValueError before any CAD work (roadmap §23.3, §23.33)."""

import math

import numpy as np
import pytest

from fansim.centrifugal.geometry import MixedFlowParams
from fansim.geometry.blade import BladeParams, RadialStation, validate_blade_params


def _bp(**kw):
    return BladeParams(**kw)


@pytest.mark.parametrize("kw, match", [
    (dict(n_blades=0), "n_blades"),
    (dict(n_blades=1), "single blade"),
    (dict(hub_radius=60.0, tip_radius=50.0), "must be < tip_radius"),
    (dict(tip_radius=math.nan), "positive numbers"),
    (dict(hub_radius=-1.0), "positive numbers"),
])
def test_bad_blade_params_raise(kw, match):
    with pytest.raises(ValueError, match=match):
        validate_blade_params(_bp(**kw))


def test_bad_stations_raise():
    with pytest.raises(ValueError, match="chord must be > 0"):
        validate_blade_params(_bp(stations=[RadialStation(0.0, 30, 30), RadialStation(1.0, -5, 25)]))
    with pytest.raises(ValueError, match="not a finite number"):
        validate_blade_params(_bp(stations=[RadialStation(0.0, 30, math.nan), RadialStation(1.0, 30, 25)]))
    with pytest.raises(ValueError, match="r_frac"):
        validate_blade_params(_bp(stations=[RadialStation(0.0, 30, 30), RadialStation(1.4, 30, 25)]))


def test_blade_angle_count_checked_for_preview_too():
    with pytest.raises(ValueError, match="blade_angles_deg"):
        validate_blade_params(_bp(n_blades=7, blade_angles_deg=[0.0, 90.0]))


def test_valid_inputs_including_numpy_and_float_counts_pass():
    validate_blade_params(_bp())
    validate_blade_params(_bp(n_blades=np.int64(9)))
    validate_blade_params(_bp(n_blades=9.0))


def test_mixed_flow_rejects_zero_blades_and_negative_span():
    with pytest.raises(ValueError, match="n_blades"):
        MixedFlowParams(n_blades=0)
    with pytest.raises(ValueError, match="z_span_mm"):
        MixedFlowParams(z_span_mm=-5.0)
    MixedFlowParams()  # defaults stay valid
