"""Known-answer checks for the geometric direction proof (Audit #1, proof 1).

Oracle (pressure face = concave face, faces the rotation, pushes air along its normal):
the synthetic section is chord c=(cos g, sin g), normal e=(-sin g, cos g) in (s, z), with camber
bulging toward +e when camber > 0, so the pressure normal is -e = (sin g, -cos g).
  g=+60, camber>0 -> n_p=(+0.87,-0.5): rotation +1 (CCW from +Z), pumps -Z
  g=-60, camber>0 -> n_p=(-0.87,-0.5): rotation -1,              pumps -Z
  g=+60, camber<0 -> n_p=(-0.87,+0.5): rotation -1,              pumps +Z

Note on chirality: chi = sign(sum A * n_theta * n_z) always algebraically equals
rotation * delivery (both reduce to sign(e_s . e_z) of the same section frame), so it is not an
independent proof of designed rotation -- it only checks chord/normal consistency and handedness.
The independent checks used elsewhere are tip lead and motor side (see test_direction_geometry
below and Task 6).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import trimesh

_REPO_ROOT = Path(__file__).resolve().parents[2]
_A12X25_STL = _REPO_ROOT / "validation" / "reference" / "a12x25_impeller.stl"

from fansim.audit.direction import (
    REAL_FAN_CHIRALITY,
    flip_about_x,
    motor_side,
    prove_direction,
    tip_lead_sign,
)
from fansim.audit.synthetic import cambered_blade_fan


def _mirror_x(mesh):
    m = mesh.copy()
    m.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
    m.fix_normals()
    return m


@pytest.mark.parametrize("stagger, camber, omega, pump", [
    (60.0, 0.06, +1, -1),
    (-60.0, 0.06, -1, -1),
    (60.0, -0.06, -1, +1),
    (30.0, 0.06, +1, -1),
])
def test_known_answers(stagger, camber, omega, pump):
    p = prove_direction(cambered_blade_fan(stagger_deg=stagger, camber=camber))
    assert p.verdict == "CONCLUSIVE", p.note
    assert (p.omega_sign, p.pump_sign) == (omega, pump)
    assert p.chirality == omega * pump
    assert p.agreement == 1.0


def test_known_answer_is_invariant_under_rotation_about_z():
    # A proper rotation about the spin axis must not change the reading (same physical fan).
    m = cambered_blade_fan(stagger_deg=60.0, camber=0.06)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(37.0), [0.0, 0.0, 1.0]))
    p = prove_direction(m)
    assert p.verdict == "CONCLUSIVE", p.note
    assert (p.omega_sign, p.pump_sign) == (+1, -1)
    assert p.chirality == -1


def test_overlapping_high_solidity_blades():
    # 9 long blades overlap in theta at mid-span (like the A12x25); loops must still separate.
    p = prove_direction(cambered_blade_fan(n_blades=9, chord=40.0, stagger_deg=55.0))
    assert p.verdict == "CONCLUSIVE" and (p.omega_sign, p.pump_sign) == (+1, -1)


def test_proper_rotation_keeps_chirality_mirror_flips_it():
    base = cambered_blade_fan()
    flipped = prove_direction(flip_about_x(base))
    assert (flipped.omega_sign, flipped.pump_sign) == (-1, +1)   # same physical fan, turned over
    assert flipped.chirality == prove_direction(base).chirality
    mirrored = prove_direction(_mirror_x(base))
    assert mirrored.chirality == -prove_direction(base).chirality


def test_face_winding_does_not_matter():
    m = cambered_blade_fan()
    m.invert()
    p = prove_direction(m)
    assert (p.omega_sign, p.pump_sign) == (+1, -1)


def test_flat_plate_is_inconclusive():
    p = prove_direction(cambered_blade_fan(camber=0.0))
    assert p.verdict == "INCONCLUSIVE" and p.omega_sign is None


@pytest.mark.parametrize("sweep, expected", [(25.0, +1), (-25.0, -1), (0.0, None)])
def test_tip_lead_sign(sweep, expected):
    assert tip_lead_sign(cambered_blade_fan(n_blades=9, chord=30.0, sweep_deg=sweep)) == expected


def test_tip_lead_sign_ignores_uneven_chordwise_vertex_density():
    # Squeezing chordwise stations toward the ends (chord_gamma != 1) skews a raw vertex-mean
    # centroid without moving the loop's actual shape; the arc-length-resampled centroid must
    # see through it and report no sweep at all.
    m = cambered_blade_fan(n_blades=9, chord=30.0, sweep_deg=0.0, chord_gamma=2.5)
    assert tip_lead_sign(m) is None


def test_tip_lead_follows_the_part_when_turned_over():
    # Turning the fan over reverses theta, so the tip-lead sign flips together with omega.
    m = cambered_blade_fan(sweep_deg=25.0)
    assert tip_lead_sign(flip_about_x(m)) == -1


def test_real_fan_chirality_constant():
    # CCW seen from the intake (+Z viewer => omega_z > 0) pushing air away (-Z): (+1)*(-1).
    assert REAL_FAN_CHIRALITY == -1


@pytest.mark.parametrize("side", [+1, -1])
def test_motor_side(side):
    assert motor_side(cambered_blade_fan(cup_side=side)) == side


def test_motor_side_unclear_without_cup():
    assert motor_side(cambered_blade_fan(cup_side=None)) is None


@pytest.mark.parametrize("side", [+1, -1])
def test_motor_side_with_centre_bore(side):
    # A through-bore (like the real A12x25's ~10 mm centre hole) leaves the r < 0.3*tip band
    # empty of material near the axis; motor_side must still find the cup from other bands.
    assert motor_side(cambered_blade_fan(cup_side=side, bore_r=5.0)) == side


def test_synthetic_blades_are_watertight():
    for b in cambered_blade_fan().split(only_watertight=False):
        assert isinstance(b, trimesh.Trimesh) and b.is_watertight


@pytest.mark.skipif(not _A12X25_STL.exists(), reason="reference STL not present")
def test_real_a12x25_direction_and_motor_side():
    # Regression pin on the real rotor mesh (read-only; never rewritten by this test).
    mesh = trimesh.load(_A12X25_STL)  # default processing (in-memory only; never writes the file)
    p = prove_direction(mesh)
    assert p.verdict == "CONCLUSIVE", p.note
    assert (p.omega_sign, p.pump_sign, p.chirality) == (+1, -1, -1)
    assert tip_lead_sign(mesh) == +1
    assert motor_side(mesh) == -1
