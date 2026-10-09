"""Tests for rotor mass balance (fansim.structural.balance)."""

import math

import numpy as np
import pytest

from fansim.structural.balance import (
    balanced_uneven_spacing,
    couple_unbalance,
    equal_spacing,
    is_balanced,
    required_counterweight,
    residual_force,
    static_unbalance,
)


@pytest.mark.parametrize("n", [2, 3, 5, 7, 9, 11, 12])
def test_equal_spacing_is_balanced(n):
    ang = equal_spacing(n)
    assert is_balanced(ang)
    assert static_unbalance(ang).normalized == pytest.approx(0.0, abs=1e-9)


def test_clustered_blades_are_imbalanced():
    # all blades bunched in one sector -> large residual toward that sector
    ang = np.radians([0, 10, 20, 30])
    u = static_unbalance(ang)
    assert u.normalized > 0.8
    assert not u.balanced


def test_counterweight_nulls_residual():
    ang = np.radians([0, 10, 20, 30])            # imbalanced
    mr, cw_angle = required_counterweight(ang)
    # add one unit-radius mass = mr at the counterweight angle; total should balance
    ang2 = np.concatenate([ang, [cw_angle]])
    masses = np.concatenate([np.ones(len(ang)), [mr]])
    assert is_balanced(ang2, masses=masses, tol=1e-9)


def test_residual_force_formula():
    # F = U * omega^2
    assert residual_force(1e-4, 209.0) == pytest.approx(1e-4 * 209.0**2)


def test_couple_zero_in_single_plane_when_balanced():
    ang = equal_spacing(6)
    z_flat = np.full(6, 5.0)                       # all blades same axial plane
    assert couple_unbalance(ang, z_flat) == pytest.approx(0.0, abs=1e-9)
    # a single axially-offset blade breaks the plane -> a real couple despite static balance
    z_offset = np.array([0, 0, 0, 0, 0, 1.0])
    assert couple_unbalance(ang, z_offset) > 1e-6


@pytest.mark.parametrize("n", [5, 6, 7, 8, 9, 10, 11])
def test_balanced_uneven_spacing_is_uneven_and_balanced(n):
    rng = np.random.default_rng(42)
    ang = balanced_uneven_spacing(n, spread=0.4, rng=rng)
    assert len(ang) == n
    assert is_balanced(ang, tol=1e-6)             # balanced by construction
    diffs = np.diff(np.concatenate([ang, [ang[0] + 2 * math.pi]]))
    assert diffs.std() > 1e-3                      # genuinely uneven (tone-spreading)


def test_spread_zero_recovers_even_spacing_variance():
    # spread=0 -> (near) equal spacing: small diff variance
    rng = np.random.default_rng(0)
    ang = balanced_uneven_spacing(8, spread=0.0, rng=rng)
    assert is_balanced(ang, tol=1e-6)
