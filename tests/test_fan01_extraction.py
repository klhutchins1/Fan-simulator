"""Unit tests for the pure geometric helpers in fansim.validation.fan01.

These do NOT touch the 26 MB FAN-01 IGES file (not checked into CI) -- they only exercise
the synthetic-data helpers used to pick the rotor cluster out of the full test-rig assembly.
"""

from __future__ import annotations

import numpy as np

from fansim.validation.fan01 import (
    _find_blade_groups,
    _fit_axis,
    _radial_distance,
    _rotation_to_z,
)


def test_find_blade_groups_prefers_largest_area_group():
    # a small-area group of 9 (e.g. fillets) and a large-area group of 9 (blades)
    areas = np.array(
        [0.11] * 9 + [8405.8] * 9 + [123.4, 555.6, 42.0]  # plus unrelated singletons
    )
    groups = _find_blade_groups(areas, expected_blade_count=9)
    assert len(groups) == 2
    # largest-area group must come first
    assert areas[groups[0]].mean() > areas[groups[1]].mean()
    np.testing.assert_allclose(areas[groups[0]], 8405.8)


def test_find_blade_groups_returns_empty_when_no_group_of_that_size():
    areas = np.array([1.0, 1.0, 1.0, 2.0, 2.0])
    assert _find_blade_groups(areas, expected_blade_count=9) == []


def test_fit_axis_recovers_known_axis_for_disk_like_points():
    rng = np.random.default_rng(0)
    n = 2000
    theta = rng.uniform(0, 2 * np.pi, n)
    radius = rng.uniform(50, 250, n)
    axial = rng.uniform(-10, 10, n)  # short compared to the 500 mm disk diameter
    local = np.column_stack([radius * np.cos(theta), radius * np.sin(theta), axial])

    # embed in a rotated, translated frame: true axis = +Z rotated to (0, 0.8, 0.6)
    true_mean = np.array([100.0, -50.0, 30.0])
    true_axis = np.array([0.0, 0.8, 0.6])
    true_axis /= np.linalg.norm(true_axis)
    r = _rotation_to_z(true_axis)  # maps true_axis -> +Z; use its transpose to go back
    points = local @ r + true_mean

    mean, axis = _fit_axis(points)
    np.testing.assert_allclose(mean, true_mean, atol=2.0)
    # axis direction is only defined up to sign
    assert abs(abs(np.dot(axis, true_axis)) - 1.0) < 1e-3


def test_radial_distance_matches_known_radii():
    mean = np.zeros(3)
    axis = np.array([0.0, 0.0, 1.0])
    points = np.array([[3.0, 4.0, 0.0], [0.0, 5.0, 10.0], [0.0, 0.0, 7.0]])
    r = _radial_distance(points, mean, axis)
    np.testing.assert_allclose(r, [5.0, 5.0, 0.0])


def test_rotation_to_z_is_proper_and_maps_axis_to_z():
    axis = np.array([0.1, 0.9, 0.2])
    axis /= np.linalg.norm(axis)
    r = _rotation_to_z(axis)
    np.testing.assert_allclose(np.linalg.det(r), 1.0, atol=1e-9)
    mapped = r @ (axis if axis[1] >= 0 else -axis)
    np.testing.assert_allclose(mapped, [0.0, 0.0, 1.0], atol=1e-9)
    # orthonormal
    np.testing.assert_allclose(r @ r.T, np.eye(3), atol=1e-9)


def test_rotation_to_z_handles_axis_already_on_z():
    r = _rotation_to_z(np.array([0.0, 0.0, 1.0]))
    np.testing.assert_allclose(r, np.eye(3), atol=1e-12)
