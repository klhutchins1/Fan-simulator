"""CFD orientation convention (Audit #1): rotor flipped 180° about X, rig fitted to the real STL."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import trimesh

from fansim.audit.direction import prove_direction
from fansim.audit.synthetic import cambered_blade_fan
from fansim.cfd.domain import MM_TO_M, TestRig as _Rig
from fansim.cfd.orientation import (
    AXIAL_CFD_ORIENTATION,
    fit_rig_to_stl,
    flip_about_x,
    orient_impeller_for_cfd,
    orientation_from_proof,
    prepare_axial_cfd,
)


def _rig() -> _Rig:
    return _Rig(duct_radius=0.056, tip_gap=0.0005, inlet_length=0.224, outlet_length=0.448,
                   impeller_z_min=-0.003, impeller_z_max=0.003, mrf_z_min=-0.005, mrf_z_max=0.005,
                   rpm=2000.0, inlet_velocity=2.0)


def _asym_box(tmp_path: Path) -> Path:
    # z from -8 to +2 mm: asymmetric so a flip is visible in the bounds.
    m = trimesh.creation.box(extents=(20.0, 10.0, 10.0))
    m.apply_translation([0.0, 0.0, -3.0])
    p = tmp_path / "asym.stl"
    m.export(str(p))
    return p


def test_convention_constant():
    assert AXIAL_CFD_ORIENTATION == "flipped"


def test_flip_is_proper_rotation_about_x():
    m = trimesh.creation.box(extents=(1.0, 2.0, 3.0))
    m.apply_translation([1.0, 2.0, 3.0])
    f = flip_about_x(m)
    assert np.allclose(f.bounds, [[0.5, -3.0, -4.5], [1.5, -1.0, -1.5]])
    assert np.isclose(abs(f.volume), abs(m.volume))
    assert np.allclose(m.bounds, [[0.5, 1.0, 1.5], [1.5, 3.0, 4.5]])  # input untouched


def test_orient_writes_flipped_copy_and_returns_bounds(tmp_path):
    src = _asym_box(tmp_path)
    before = src.read_bytes()
    z0, z1 = orient_impeller_for_cfd(src, tmp_path / "out.stl")
    assert (z0, z1) == pytest.approx((-2.0, 8.0))
    assert src.read_bytes() == before
    z0b, z1b = orient_impeller_for_cfd(src, tmp_path / "same.stl", orientation="as_built")
    assert (z0b, z1b) == pytest.approx((-8.0, 2.0))


def test_orient_rejects_unknown(tmp_path):
    with pytest.raises(ValueError, match="orientation"):
        orient_impeller_for_cfd(_asym_box(tmp_path), tmp_path / "x.stl", orientation="flip")


def test_fit_rig_to_stl_contains_rotor(tmp_path):
    src = _asym_box(tmp_path)
    rig = fit_rig_to_stl(_rig(), src, mrf_margin_mm=2.0)
    assert rig.impeller_z_min == pytest.approx(-8.0 * MM_TO_M)
    assert rig.impeller_z_max == pytest.approx(2.0 * MM_TO_M)
    assert rig.mrf_z_min == pytest.approx(-10.0 * MM_TO_M)
    assert rig.mrf_z_max == pytest.approx(4.0 * MM_TO_M)
    # Everything else is unchanged.
    assert replace(rig, impeller_z_min=-0.003, impeller_z_max=0.003,
                   mrf_z_min=-0.005, mrf_z_max=0.005) == _rig()


def test_prepare_axial_cfd(tmp_path):
    src = _asym_box(tmp_path)
    stl, rig = prepare_axial_cfd(src, _rig(), tmp_path)
    assert stl == tmp_path / "impeller_cfd.stl" and stl.is_file()
    assert rig.impeller_z_min == pytest.approx(-2.0 * MM_TO_M)
    assert rig.impeller_z_max == pytest.approx(8.0 * MM_TO_M)
    assert rig.spin == -1


def test_orientation_from_proof_stock_handed_is_flipped():
    # NF-A12x25 handedness: omega=+1, pump=-1, chirality=-1 -- must flip to pump +Z at spin=-1.
    p = prove_direction(cambered_blade_fan(stagger_deg=60.0, camber=0.06))
    assert p.verdict == "CONCLUSIVE" and (p.omega_sign, p.pump_sign) == (1, -1)
    assert orientation_from_proof(p) == ("flipped", -1)


def test_orientation_from_proof_fan01_handed_is_as_built():
    # FAN-01 handedness (opposite chirality to the Noctua): omega=+1, pump=+1, chirality=+1.
    p = prove_direction(cambered_blade_fan(stagger_deg=-60.0, camber=-0.06))
    assert p.verdict == "CONCLUSIVE" and (p.omega_sign, p.pump_sign) == (1, 1)
    assert orientation_from_proof(p) == ("as_built", 1)


def test_orientation_from_proof_rejects_inconclusive():
    p = prove_direction(cambered_blade_fan(camber=0.0))  # flat plate -> INCONCLUSIVE
    assert p.verdict == "INCONCLUSIVE"
    with pytest.raises(ValueError, match="CONCLUSIVE"):
        orientation_from_proof(p)


def test_audit_reexports_same_flip():
    from fansim.audit import direction
    from fansim.cfd import orientation
    from fansim.geometry import rotate
    assert direction.flip_about_x is orientation.flip_about_x
    assert direction.flip_about_x is rotate.flip_about_x
