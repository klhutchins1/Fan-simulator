"""Centrifugal structural gate (fansim/structural/stress.py) — no CFD."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS
from fansim.structural.stress import LAYER_ADHESION_K, centrifugal_root_stress


def test_petg_at_2000rpm_still_ok():
    r = centrifugal_root_stress(BladeParams(), material="PETG")
    assert r.ok and r.sigma_root_mpa < 1.0
    assert r.adhesion_k == LAYER_ADHESION_K == pytest.approx(0.60)
    assert r.in_plane_yield_mpa == pytest.approx(MATERIALS["PETG"].yield_strength_mpa)
    assert r.yield_mpa == pytest.approx(r.in_plane_yield_mpa * r.adhesion_k)


def test_adhesion_knockdown_scales_safety_factor_not_sigma():
    p = BladeParams()
    iso = centrifugal_root_stress(p, material="PETG", adhesion_k=1.0)
    fdm = centrifugal_root_stress(p, material="PETG", adhesion_k=0.60)
    assert iso.sigma_root_mpa == pytest.approx(fdm.sigma_root_mpa)
    assert fdm.safety_factor == pytest.approx(0.60 * iso.safety_factor)


def test_high_rpm_passes_in_plane_and_fails_layer_adhesion():
    # sigma ∝ RPM²; pick a speed where 3× in-plane yield holds but 3× (0.60 yield) does not.
    p = replace(BladeParams(), rpm=25000.0)
    iso = centrifugal_root_stress(p, material="PETG", adhesion_k=1.0)
    fdm = centrifugal_root_stress(p, material="PETG")
    assert iso.ok
    assert not fdm.ok
    assert "layer-adhesion" in fdm.reason
    assert "layer-adhesion" not in iso.reason
