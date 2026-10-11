"""Builder direction cross-check, attempt 2 (docs/validation/audits/2026-10-10-direction-crosscheck-2.md)."""

from __future__ import annotations

import dataclasses

import pytest

from fansim.audit.direction import DirectionProof
from fansim.cfd.orientation import builder_direction_refusal
from fansim.geometry.blade import BladeParams, RadialStation, signed_design_camber, validate_blade_params


def _proof(om, pu, chi, verdict="CONCLUSIVE"):
    return DirectionProof(om, pu, chi, 1.0, 20, (), verdict, "")


def test_builder_reading_passes():
    assert builder_direction_refusal(_proof(1, -1, -1), 0.08) is None


def test_lean_artifact_on_flat_blade_passes():
    """9605-style: flat design, leaned tip reads the split backwards; chirality is right."""
    assert builder_direction_refusal(_proof(-1, 1, -1), 0.004) is None


def test_mirror_refused_whatever_the_camber():
    assert "mirror" in builder_direction_refusal(_proof(1, 1, 1), 0.08)
    assert "mirror" in builder_direction_refusal(_proof(-1, -1, 1), 0.004)


def test_flipped_camber_on_cambered_design_refused():
    """P3a: geometry reads (-1,+1) but the design is cambered positive."""
    assert "design camber" in builder_direction_refusal(_proof(-1, 1, -1), 0.08)


def test_negative_design_camber_expects_flipped_split():
    assert builder_direction_refusal(_proof(-1, 1, -1), -0.05) is None
    assert builder_direction_refusal(_proof(1, -1, -1), -0.05) is not None


def test_no_design_camber_means_chirality_only():
    assert builder_direction_refusal(_proof(-1, 1, -1), None) is None
    assert builder_direction_refusal(_proof(1, 1, 1), None) is not None


def test_inconclusive_never_refuses():
    assert builder_direction_refusal(_proof(None, None, None, "INCONCLUSIVE"), 0.08) is None


def _stock_like(camber=0.08):
    st = [RadialStation(0.0, 30.0, 26.0, 0.10, camber, 0.4, 0.0, 0.0, 0.0),
          RadialStation(0.5, 34.0, 26.0, 0.08, camber * 1.2, 0.4, 2.0, 0.0, 10.0),
          RadialStation(1.0, 30.0, 22.0, 0.06, camber * 0.5, 0.4, 4.0, 0.0, 20.0)]
    return BladeParams(n_blades=7, stations=st)


def test_signed_design_camber_takes_largest_magnitude_with_sign():
    assert signed_design_camber(_stock_like(0.08)) == pytest.approx(0.096)
    assert signed_design_camber(_stock_like(-0.08)) == pytest.approx(-0.096)


def test_validate_refuses_backwards_camber():
    """P3b."""
    with pytest.raises(ValueError, match="camber"):
        validate_blade_params(_stock_like(-0.05))
    validate_blade_params(_stock_like(-0.01))  # small negative: within flat-blade noise, allowed
    validate_blade_params(_stock_like(0.08))


def test_optimizer_camber_bounds_are_non_negative():
    from fansim.optimize.search_space import BOUNDS
    for space in BOUNDS.values():
        assert space["max_camber"][0] >= 0.0
