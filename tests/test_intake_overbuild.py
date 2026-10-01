"""Intake overbuild (+Z) helpers and Fit clamp (§2026-09-30)."""

from __future__ import annotations

import dataclasses

import pytest

from fansim.cockpit.placement import (
    depth_allow_max,
    effective_depth_max,
    fit_envelope,
    impeller_z_extent,
    intake_envelope_z_range,
    intake_extra_mm,
)
from fansim.fan_spec import get_fan_spec
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat


def test_intake_extra_mm_clamps_and_gates():
    assert intake_extra_mm(enabled=False, extra_mm=10) == 0.0
    assert intake_extra_mm(enabled=True, extra_mm=10) == 10.0
    assert intake_extra_mm(enabled=True, extra_mm=-5) == 0.0
    assert intake_extra_mm(enabled=True, extra_mm=99) == 20.0


def test_effective_and_allow_compose_with_leeway():
    spec = dataclasses.replace(get_fan_spec("a12x25"), leeway_depth_mm=2.0)
    assert effective_depth_max(spec, intake_extra=10.0) == 35.0
    assert depth_allow_max(spec, intake_extra=10.0) == 37.0


def test_intake_envelope_z_range_outlet_anchored():
    lo, hi = intake_envelope_z_range(0.0, 25.0, 0.0)
    assert lo == pytest.approx(-12.5)
    assert hi == pytest.approx(12.5)
    lo2, hi2 = intake_envelope_z_range(0.0, 25.0, 10.0)
    assert lo2 == pytest.approx(-12.5)
    assert hi2 == pytest.approx(22.5)


def test_fit_envelope_respects_max_depth_mm():
    spec = get_fan_spec("a12x25")
    flat = {**stock_blade_flat("a12x25"), "sweep_tip": 8.0, "sweep_mid": 6.0}
    fitted_nom = fit_envelope(flat, spec, features=Features())
    fitted_wide = fit_envelope(flat, spec, features=Features(), max_depth_mm=40.0)
    d_nom = impeller_z_extent(blade_from_flat(fitted_nom.flat, Features()))
    assert d_nom <= spec.depth_mm[1] + 0.15
    assert abs(float(fitted_wide.flat.get("sweep_tip", 0))) >= abs(
        float(fitted_nom.flat.get("sweep_tip", 0))
    ) - 1e-6
