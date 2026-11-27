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


@pytest.mark.parametrize("n", [5, 6, 7, 8, 9])
def test_balanced_uneven_spacing_enforces_min_gap_at_high_spread(n):
    # Issue #126: large spread must never cause blades to overlap or collide.
    step = 2.0 * math.pi / n
    min_gap_frac = 0.25
    for seed in range(10):
        ang = balanced_uneven_spacing(
            n, spread=1.8, rng=np.random.default_rng(seed), min_gap_frac=min_gap_frac
        )
        assert is_balanced(ang, tol=1e-6)
        s = np.sort(ang % (2.0 * math.pi))
        gaps = np.diff(np.concatenate([s, [s[0] + 2.0 * math.pi]]))
        assert float(np.min(gaps)) >= min_gap_frac * step - 1e-9


def test_balanced_uneven_spacing_rejects_invalid_min_gap_frac():
    with pytest.raises(ValueError, match="min_gap_frac"):
        balanced_uneven_spacing(7, spread=0.3, min_gap_frac=-0.1)
    with pytest.raises(ValueError, match="min_gap_frac"):
        balanced_uneven_spacing(7, spread=0.3, min_gap_frac=1.0)


def test_couple_unbalance_cg_and_plane_reference():
    # Issue #126: ISO 21940 couple unbalance about CG is invariant to axial origin shifts,
    # even when static unbalance != 0.
    ang = np.radians([0.0, 20.0, 40.0])  # statically unbalanced
    z = np.array([0.0, 0.01, 0.02])
    c_cg = couple_unbalance(ang, z, z_ref="cg")
    c_cg_shifted = couple_unbalance(ang, z + 5.0, z_ref="cg")
    assert c_cg_shifted == pytest.approx(c_cg, rel=1e-12, abs=1e-12)
    assert couple_unbalance(ang, z, z_ref=0.01) == pytest.approx(
        couple_unbalance(ang, z - 0.01), rel=1e-12, abs=1e-12
    )
    # Default z_ref=0 preserves legacy behavior for unbalanced rotors and is already
    # shift-invariant for statically balanced rotors.
    assert couple_unbalance(ang, z) == pytest.approx(couple_unbalance(ang, z, z_ref=0.0))

