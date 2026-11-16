"""Plate blade height: a rigid Z shift of the sections, hub left where it is."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from fansim.geometry.blade import (
    BladeParams,
    _hub_axial_range,
    _section_points_3d,
    _thick_scale_kw,
    plate_blade_z_mm,
)
from fansim.geometry.config import load_blade_params
from fansim.optimize.search_space import blade_from_flat, blade_to_flat

ROOT = Path(__file__).resolve().parents[1]


def _section_z(params: BladeParams) -> list[float]:
    """Root-section Z the blade builder uses (plate shift included, hub sizing is not)."""
    st = min(params.stations, key=lambda s: s.r_frac)
    kw = _thick_scale_kw(params)
    pts = _section_points_3d(
        r=params.hub_radius - params.root_embed,
        r_frac=st.r_frac,
        chord=st.chord,
        stagger_deg=st.stagger_deg,
        thickness=st.thickness,
        max_camber=st.max_camber,
        camber_pos=st.camber_pos,
        sweep=st.sweep,
        skew=st.skew,
        le_sweep=st.le_sweep,
        lean_deg=st.lean_deg,
        n_chord=params.n_chord,
        features=params.features,
        le_skew=st.le_skew,
        te_face=st.te_face,
        le_face=st.le_face,
        blade_z_mm=plate_blade_z_mm(params),
        **kw,
    )
    return [float(p.z) for p in pts]


def test_blade_z_shifts_plate_section_and_zero_does_not():
    base = BladeParams(section_family="plate", hub_height_mm=20.0, blade_z_mm=0.0)
    z0 = _section_z(base)
    assert plate_blade_z_mm(base) == pytest.approx(0.0)
    assert _section_z(dataclasses.replace(base, blade_z_mm=0.0)) == pytest.approx(z0)

    dropped = dataclasses.replace(base, blade_z_mm=-2.5)
    assert _section_z(dropped) == pytest.approx([z - 2.5 for z in z0])

    raised = dataclasses.replace(base, blade_z_mm=1.25)
    assert _section_z(raised) == pytest.approx([z + 1.25 for z in z0])


def test_blade_z_does_not_move_the_hub_or_naca():
    base = BladeParams(section_family="plate", hub_height_mm=20.0, blade_z_mm=0.0)
    moved = dataclasses.replace(base, blade_z_mm=-2.5)
    assert _hub_axial_range(moved) == pytest.approx(_hub_axial_range(base))

    naca = dataclasses.replace(base, section_family="naca", blade_z_mm=-2.5)
    assert plate_blade_z_mm(naca) == pytest.approx(0.0)
    z_naca = _section_z(dataclasses.replace(naca, blade_z_mm=0.0))
    assert _section_z(naca) == pytest.approx(z_naca)


def test_blade_z_round_trips_and_outline_root_drops_onto_the_hub():
    p = BladeParams(section_family="plate", hub_height_mm=16.5, blade_z_mm=-1.5)
    flat = blade_to_flat(p)
    assert flat["blade_z"] == pytest.approx(-1.5)
    assert blade_from_flat(flat).blade_z_mm == pytest.approx(-1.5)
    assert blade_from_flat({**flat, "blade_z": 0.0}).blade_z_mm == pytest.approx(0.0)

    outline_path = ROOT / "config" / "problems" / "a12x25_outline.yaml"
    outline = load_blade_params(outline_path)
    assert outline.section_family == "plate"
    # Gap on outline_copy_20261115.stl: root bottom -9.85 mm, hub bottom -12.22 mm.
    assert outline.blade_z_mm == pytest.approx(-2.37)
    assert "blade_z_mm: -2.37" in outline_path.read_text(encoding="utf-8")

    parked = dataclasses.replace(outline, blade_z_mm=0.0)
    assert min(_section_z(outline)) == pytest.approx(min(_section_z(parked)) - 2.37)
    assert _hub_axial_range(outline) == pytest.approx(_hub_axial_range(parked))


def test_design_tab_exposes_blade_height_slider():
    from fansim.cockpit.fan_copy import CONTROL_DESC
    from fansim.cockpit.fan_editor import EDITOR_VARS

    assert "e_blade_z" in EDITOR_VARS
    help_text = CONTROL_DESC["e_blade_z"].lower()
    assert "up" in help_text and "down" in help_text and "hub" in help_text
    ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "Blade height" in ui
    assert "e_blade_z" in ui
