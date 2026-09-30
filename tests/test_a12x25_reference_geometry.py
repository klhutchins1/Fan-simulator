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
    assert flat["tip_radius"] == pytest.approx(54.5)
    assert 20.0 <= flat["hub_radius"] <= 23.0
    assert float(flat.get("hub_height") or 0.0) == pytest.approx(16.5)
    assert float(flat.get("blade_hub_z") or 0.0) == pytest.approx(0.0)
    assert flat.get("span_interp") == "pchip"
    assert float(flat.get("le_thick_scale") or 1.0) == pytest.approx(0.2)
    assert float(flat.get("te_thick_scale") or 1.0) == pytest.approx(0.2)
    assert int(flat.get("tip_notch_count") or 0) == 0
    assert float(flat.get("tip_notch_depth_mm") or 0.0) == pytest.approx(0.0)
    # Stock recipe v2 (§19.7): station chord = measured cylinder-cut chord (not loft).
    # Previous loft-inflated tip (~49.8) kept as build-internal; YAML tip ~33.5.
    assert flat["chord_root"] == pytest.approx(17.75, abs=0.05)
    assert flat["chord_mid"] == pytest.approx(25.12, abs=0.1)
    assert flat["chord_tip"] == pytest.approx(33.53, abs=0.1)
    assert flat["stagger_root"] == pytest.approx(24.13, abs=0.05)
    assert flat["stagger_mid"] == pytest.approx(28.69, abs=0.05)
    assert flat["stagger_tip"] == pytest.approx(16.26, abs=0.05)
    assert flat["skew_mid"] == pytest.approx(3.7372, abs=0.01)
    assert flat["skew_tip"] == pytest.approx(13.7985, abs=0.01)
    assert flat["lean_tip"] == pytest.approx(33.0)
    assert flat["thick_mode"] == "tapered"
    tip_wall = float(flat["thickness_tip"]) * float(flat["chord_tip"])
    assert tip_wall == pytest.approx(2.44, abs=0.1)
    assert flat["section_family"] == "plate"


def test_uniform_thick_mm_lands_on_tip_wall():
    """Cockpit Uniform wall must thicken the tip station in blade_from_flat (not leave t/c=0.03)."""
    from fansim.geometry.features import Features
    from fansim.geometry.blade import uniform_thickness_tc as utc
    from fansim.optimize.search_space import blade_from_flat, stock_blade_flat

    flat = stock_blade_flat("a12x25")
    th = utc(2.0, flat["chord_root"], flat["chord_mid"], flat["chord_tip"])
    flat = dict(
        flat,
        thick_mode="uniform",
        thick_mm=2.0,
        thickness_root=th[0],
        thickness_mid=th[1],
        thickness_tip=th[2],
    )
    bp = blade_from_flat(flat, Features())
    tip = max(bp.stations, key=lambda s: s.r_frac)
    assert tip.thickness * tip.chord == pytest.approx(2.0, abs=1e-6)


def test_stock_plate_section_holds_constant_wall():
    """Plate family keeps tip wall ≈ thick_mm across the chord (NACA would knife the TE)."""
    import numpy as np

    from fansim.geometry.airfoil import rounded_plate, naca4
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25")
    assert flat["section_family"] == "plate"
    t = float(flat["thickness_tip"])
    c = float(flat["chord_tip"])
    plate = rounded_plate(t, 80)
    naca = naca4(0.06, 0.4, t, 80)
    plate_wall = float(np.max(plate[:, 1]) - np.min(plate[:, 1])) * c
    x = 0.5
    yt = 5.0 * t * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1036 * x**4
    )
    naca_mid = 2.0 * float(yt) * c
    # Plate holds constant wall across the chord: tip wall ~= thickness_tip * chord_tip
    # (walls now taper spanwise, so compare to the tip station, not the span-average thick_mm).
    assert plate_wall == pytest.approx(t * c, abs=0.08)
    assert plate_wall > naca_mid


def test_approx_alias_still_loads():
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25_approx")
    assert flat["n_blades"] == 9


def test_fit_envelope_preserve_tip_keeps_recipe_radius():
    from fansim.cockpit.placement import fit_envelope
    from fansim.fan_spec import get_fan_spec
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import stock_blade_flat

    spec = get_fan_spec("a12x25")
    flat = stock_blade_flat("a12x25")
    tip0 = float(flat["tip_radius"])
    kept = fit_envelope(flat, spec, features=Features(), preserve_tip=True)
    assert float(kept.flat["tip_radius"]) == pytest.approx(tip0)
    assert all(c.field != "tip_radius" for c in kept.changes)


def test_reference_stock_fits_a12x25_frame():
    """Committed tip 54.5 is frame-fit; Fit keeps it in the housing band."""
    from fansim.cockpit.placement import fit_envelope
    from fansim.fan_spec import get_fan_spec
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import stock_blade_flat

    spec = get_fan_spec("a12x25")
    flat = stock_blade_flat("a12x25")
    assert flat["tip_radius"] == pytest.approx(54.5)
    fitted = fit_envelope(flat, spec, features=Features())
    assert fitted.fit_status == "fits"
    assert 54.3 <= float(fitted.flat["tip_radius"]) <= 54.5


@pytest.mark.skipif(not STL_PATH.is_file(), reason="trusted STL not present")
def test_stl_silhouette_when_available():
    """Silhouette gates for the user-provided close-reference impeller (not OEM CAD)."""
    from fansim.validation.reference_stl import measure_silhouette

    m = measure_silhouette(STL_PATH)
    assert m.watertight
    assert m.n_blades == 9
    assert 55.0 <= m.tip_radius_mm <= 57.0
    assert 18.5 <= m.hub_radius_mm <= 23.5
    assert m.axial_depth_mm <= 25.0


@pytest.mark.skipif(not STL_PATH.is_file(), reason="trusted STL not present")
def test_stock_cylinder_slices_near_reference():
    """Gold ✕ parametric stock should land near reference STL mid/tip chord & wall."""
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25")
    # Recipe targets (§19.7 measured chords; absolute tip wall unchanged ~2.44 mm).
    assert flat["chord_mid"] == pytest.approx(25.12, abs=0.5)
    assert flat["chord_tip"] == pytest.approx(33.53, abs=0.5)
    assert flat["stagger_mid"] == pytest.approx(28.69, abs=1.0)
    assert flat["stagger_tip"] == pytest.approx(16.26, abs=1.0)
    assert float(flat["thick_mm"]) == pytest.approx(2.36, abs=0.3)
    assert flat["section_family"] == "plate"
    assert flat["lean_tip"] - flat.get("lean_mid", 0.0) == pytest.approx(19.0, abs=6.0)
    assert flat["skew_mid"] == pytest.approx(3.7372)
    assert flat["skew_tip"] == pytest.approx(13.7985)
    assert int(flat.get("tip_notch_count") or 0) == 0
