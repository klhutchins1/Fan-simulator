# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Hub-height control + hub profiles (cylinder / cone / dome). Fast, no CFD."""

from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path

import pytest

from fansim.geometry import build_impeller, export_stl, watertight_report
from fansim.geometry.blade import BladeParams, RadialStation, _hub_axial_range, _root_axial_span


def _swept(sweep_tip: float = 8.0) -> BladeParams:
    return BladeParams(n_blades=7, stations=[
        RadialStation(0.0, 34, 44, 0.08, 0.05, 0.4, 0.0, 0, 0.0),
        RadialStation(0.5, 44, 39, 0.05, 0.06, 0.4, 2.7, 0, 14.0),
        RadialStation(1.0, 38, 31, 0.03, 0.06, 0.4, sweep_tip, 0, 26.0)])


def _depth(params) -> float:
    d = Path(tempfile.mkdtemp()) / "m.stl"
    export_stl(build_impeller(params), d)
    r = watertight_report(d)
    assert r.ok, "impeller must be a single watertight body"
    (lo, hi) = r.bounds_mm
    return hi[2] - lo[2]


def test_auto_hub_covers_root_span():
    p = _swept()
    r_lo, r_hi = _root_axial_span(p)
    z0, z1 = _hub_axial_range(p, build_impeller(p).val())  # auto
    # auto hub height == root span + 2*margin, and it brackets the root
    assert (z1 - z0) == pytest.approx((r_hi - r_lo) + 2 * p.hub_axial_margin, abs=1e-6)


def test_explicit_hub_height_clamped_to_root_minimum():
    p = _swept()
    r_lo, r_hi = _root_axial_span(p)
    min_h = (r_hi - r_lo) + 2 * p.hub_axial_margin
    tiny = dataclasses.replace(p, hub_height_mm=1.0)  # below the minimum -> clamped up
    z0, z1 = _hub_axial_range(tiny, build_impeller(tiny).val())
    assert (z1 - z0) == pytest.approx(min_h, abs=1e-6)
    tall = dataclasses.replace(p, hub_height_mm=min_h + 8.0)
    z0, z1 = _hub_axial_range(tall, build_impeller(tall).val())
    assert (z1 - z0) == pytest.approx(min_h + 8.0, abs=1e-6)


def test_taller_hub_increases_depth():
    p = _swept(sweep_tip=2.0)  # mild sweep so the hub is the depth driver
    auto = _depth(p)
    tall = _depth(dataclasses.replace(p, hub_height_mm=auto + 6.0))
    assert tall > auto + 3.0, "a taller explicit hub must deepen the part"


@pytest.mark.parametrize("profile,nose", [("cone", 10.0), ("dome", 6.0), ("dome", 12.0)])
def test_nose_profiles_watertight_and_add_height(profile, nose):
    p = _swept(sweep_tip=2.0)
    flat_depth = _depth(p)
    nosed = _depth(dataclasses.replace(p, hub_profile=profile, hub_nose_mm=nose))
    assert nosed > flat_depth, f"{profile} nose should add axial height"


def test_blade_hub_z_shifts_hub_relative_to_roots():
    """Positive blade_hub_z_mm puts more hub below the roots (blades sit higher)."""
    p = _swept(sweep_tip=2.0)
    r_lo, r_hi = _root_axial_span(p)
    root_h = r_hi - r_lo
    tall = dataclasses.replace(p, hub_height_mm=root_h + 10.0, blade_hub_z_mm=0.0)
    z0, z1 = _hub_axial_range(tall)
    mid0 = 0.5 * (z0 + z1)
    high = dataclasses.replace(tall, blade_hub_z_mm=4.0)
    z0b, z1b = _hub_axial_range(high)
    mid_b = 0.5 * (z0b + z1b)
    # Hub shifts down → midpoint below root center → blades sit higher on hub
    assert mid_b < mid0 - 3.0
    assert z0b <= r_lo + 1e-6
    assert z1b >= r_hi - 1e-6


def test_blade_hub_z_clamped_to_hub_slack():
    p = _swept(sweep_tip=2.0)
    r_lo, r_hi = _root_axial_span(p)
    root_h = r_hi - r_lo
    # Auto hub has ~zero slack — large bias must clamp to no-op-ish
    auto = dataclasses.replace(p, blade_hub_z_mm=20.0)
    z0, z1 = _hub_axial_range(auto)
    assert z0 <= r_lo + 1e-6 and z1 >= r_hi - 1e-6
    assert (z1 - z0) == pytest.approx(root_h + 2 * p.hub_axial_margin, abs=1e-6)


def test_blade_hub_z_round_trip_flat():
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat, blade_to_flat

    p = _swept(sweep_tip=2.0)
    p.hub_height_mm = 20.0
    p.blade_hub_z_mm = 3.5
    flat = blade_to_flat(p)
    assert flat["blade_hub_z"] == pytest.approx(3.5)
    q = blade_from_flat(flat, Features())
    assert q.blade_hub_z_mm == pytest.approx(3.5)
