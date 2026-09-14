"""Envelope and stock-loader tests for A12x25 reference vs approximate recipes."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STL_PATH = ROOT / "validation" / "reference" / "a12x25_impeller.stl"


def test_reference_blade_count_and_envelope():
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25")
    assert flat["n_blades"] == 7
    assert 55.0 <= flat["tip_radius"] <= 57.0
    assert 20.0 <= flat["hub_radius"] <= 23.0


def test_approx_alias_still_loads():
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25_approx")
    assert flat["n_blades"] == 7


@pytest.mark.skipif(not STL_PATH.is_file(), reason="trusted STL not present")
def test_stl_silhouette_when_available():
    """Placeholder for Phase-3+ STL silhouette checks."""
    assert STL_PATH.is_file()
