"""§19.4 CW ⇄ CCW handedness mirror — geometry + spin travel together."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from fansim.audit.synthetic import cambered_blade_fan
from fansim.audit.direction import prove_direction
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.geometry.handedness import (
    cfd_spin_for_omega,
    handedness_variants,
    mirror_blade_params,
    write_handedness_meta,
)


def test_mirror_negates_stagger_lean_and_skew():
    sts = [
        RadialStation(0.0, 20.0, 40.0, thickness=0.1, lean_deg=5.0, skew=1.0, le_skew=2.0),
        RadialStation(1.0, 30.0, 25.0, thickness=0.08, lean_deg=20.0, skew=3.0, le_skew=8.0),
    ]
    p = replace(BladeParams(), stations=sts, blade_angles_deg=[0.0, 40.0, 80.0])
    m = mirror_blade_params(p)
    assert [s.stagger_deg for s in m.stations] == [-40.0, -25.0]
    assert [s.lean_deg for s in m.stations] == [-5.0, -20.0]
    assert [s.skew for s in m.stations] == [-1.0, -3.0]
    assert [s.le_skew for s in m.stations] == [-2.0, -8.0]
    assert m.blade_angles_deg == [0.0, -40.0, -80.0]
    # original untouched
    assert p.stations[0].stagger_deg == 40.0


def test_mirror_twice_is_identity():
    p = BladeParams()
    assert mirror_blade_params(mirror_blade_params(p)).stations[0].stagger_deg == pytest.approx(
        p.stations[0].stagger_deg
    )


def test_cfd_spin_pairs_with_flipped_orientation():
    # Stock omega=+1 → flipped CFD spin −1 (AXIAL_BUILDER_DIRECTION)
    assert cfd_spin_for_omega(+1, orientation="flipped") == -1
    assert cfd_spin_for_omega(-1, orientation="flipped") == +1
    assert cfd_spin_for_omega(+1, orientation="as_built") == +1


def test_variants_flip_omega_and_spin_together():
    as_des, mir = handedness_variants(BladeParams(), designed_omega=+1)
    assert as_des.omega_sign == +1 and as_des.cfd_spin == -1
    assert mir.omega_sign == -1 and mir.cfd_spin == +1
    assert mir.params.stations[0].stagger_deg == pytest.approx(-as_des.params.stations[0].stagger_deg)


def test_mirrored_stagger_flips_omega_on_synthetic_mesh():
    """Known-answer table: +stagger → omega +1; −stagger → omega −1 (same camber)."""
    fwd = prove_direction(cambered_blade_fan(stagger_deg=60.0, camber=0.06))
    rev = prove_direction(cambered_blade_fan(stagger_deg=-60.0, camber=0.06))
    assert fwd.verdict == "CONCLUSIVE" and rev.verdict == "CONCLUSIVE"
    assert fwd.omega_sign == +1
    assert rev.omega_sign == -1
    assert fwd.pump_sign == rev.pump_sign == -1


def test_write_handedness_meta(tmp_path):
    _, mir = handedness_variants(BladeParams())
    path = write_handedness_meta(mir, tmp_path / "x.handedness.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["handedness"] == "mirrored"
    assert data["omega_sign_designed"] == -1
    assert data["cfd_spin"] == +1
    assert "same spin" in data["note"]
