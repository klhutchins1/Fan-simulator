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
    assert 54.0 <= flat["tip_radius"] <= 55.0
    assert 20.0 <= flat["hub_radius"] <= 23.0
    assert float(flat.get("hub_height") or 0.0) >= 15.0
    # Eye-fit planform (narrow root/mid chord vs legacy approx 34/44).
    assert flat["chord_root"] == pytest.approx(18.0)
    assert flat["chord_mid"] == pytest.approx(25.0)
    assert flat["chord_tip"] == pytest.approx(38.0)
    assert flat["stagger_root"] == pytest.approx(40.0)
    assert flat["stagger_mid"] == pytest.approx(30.0)
    assert flat["stagger_tip"] == pytest.approx(22.0)
    assert flat["skew_tip"] == pytest.approx(4.5)


def test_approx_alias_still_loads():
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25_approx")
    assert flat["n_blades"] == 9


def test_reference_stock_fits_a12x25_frame():
    from fansim.cockpit.placement import fit_envelope, nominal_fits_spec
    from fansim.fan_spec import get_fan_spec
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import stock_blade_flat

    spec = get_fan_spec("a12x25")
    flat = stock_blade_flat("a12x25")
    assert nominal_fits_spec(flat, spec)
    fitted = fit_envelope(flat, spec, features=Features())
    assert fitted.fit_status == "fits"
    # Recipe is already frame-sized — Fit should be a no-op (or hub-height only).
    assert all(c.field == "hub_height" for c in fitted.changes) or not fitted.changes


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
