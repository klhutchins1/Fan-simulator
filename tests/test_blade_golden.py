"""blade.py geometry-golden sign-off (roadmap §15.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.validation.blade_golden import (
    GOLDEN_PATH,
    assert_close_ref_envelope,
    assert_matches_golden,
    load_golden,
    measure_stock_golden,
)

STL_PATH = Path("validation/reference/a12x25_impeller.stl")


@pytest.fixture(scope="module")
def stock_golden_metrics():
    return measure_stock_golden()


def test_a12x25_stock_matches_blade_golden(stock_golden_metrics):
    """Parametric stock volume/bounds/tip-section must not drift vs committed golden."""
    assert GOLDEN_PATH.is_file(), f"missing golden {GOLDEN_PATH}"
    assert_matches_golden(stock_golden_metrics, load_golden())


@pytest.mark.skipif(not STL_PATH.is_file(), reason="trusted STL not present")
def test_a12x25_stock_envelope_near_close_ref(stock_golden_metrics):
    """Soft tip/axial envelope vs close-ref STL (volume is not expected to match)."""
    assert_close_ref_envelope(stock_golden_metrics, STL_PATH)
