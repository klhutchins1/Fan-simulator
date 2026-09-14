"""Envelope and stock-loader tests for A12x25 reference vs approximate recipes."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STL_PATH = ROOT / "validation" / "reference" / "a12x25_impeller.stl"


def test_reference_blade_count_and_envelope():
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25")
    assert flat["n_blades"] == 9
    assert 55.0 <= flat["tip_radius"] <= 57.0
    assert 20.0 <= flat["hub_radius"] <= 23.0


def test_approx_alias_still_loads():
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25_approx")
    assert flat["n_blades"] == 9


@pytest.mark.skipif(not STL_PATH.is_file(), reason="trusted STL not present")
def test_stl_silhouette_when_available():
    """Silhouette gates for the user-provided close-reference impeller (not OEM CAD)."""
    from fansim.validation.reference_stl import measure_silhouette

    m = measure_silhouette(STL_PATH)
    assert m.watertight
    assert m.n_blades == 9
    assert 55.0 <= m.tip_radius_mm <= 57.0
    # Vertex p5 can sit slightly inside the geometric hub OD (fillets / hub face).
    assert 18.5 <= m.hub_radius_mm <= 23.5
    assert m.axial_depth_mm <= 25.0
