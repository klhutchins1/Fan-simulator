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
_DRONE_DIR = _REPO_ROOT / "validation" / "reference" / "drone_radial"
_OBJ_1 = _DRONE_DIR / "obj_1_ccw_impeller.stl"
_OBJ_2 = _DRONE_DIR / "obj_2_ccw.stl"
_OBJ_6 = _DRONE_DIR / "obj_6_cw.stl"
_OBJ_7 = _DRONE_DIR / "obj_7_ccw.stl"
_OBJ_8 = _DRONE_DIR / "obj_8_cw.stl"

from fansim.audit.direction import (
    DEFAULT_R_FRACS,
    MIN_CAMBER_RATIO,
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
    m = cambered_blade_fan(n_blades=9, chord=30.0, sweep_deg=0.0, chord_gamma=3.5)
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


@pytest.mark.parametrize("side", [+1, -1])
def test_motor_side_with_realistic_centre_bore(side):
    # bore_r = 0.18*r_tip is closer to the real A12x25's ~10 mm bore on a 55 mm tip.
    fan = cambered_blade_fan(cup_side=side, bore_r=0.18 * 50.0)
    assert motor_side(fan) == side


@pytest.mark.parametrize("offset", [+3.0, -3.0])
def test_motor_side_none_for_offset_solid_hub(offset):
    # E9: a solid hub (no cup) merely shifted in z relative to the blades must not look like a
    # cup -- motor_side must measure depth relative to the hub's OWN end faces, not whole-mesh
    # bounds (which this offset would otherwise skew).
    fan = cambered_blade_fan(cup_side=None, hub_z_offset=offset)
    assert motor_side(fan) is None


def test_motor_side_none_for_low_hub_ratio_solid_hub():
    # E8: with hub/tip ~= 0.22, naive near-axis probe bands can reach into the blades and a
    # solid hub would misread as a cup. Bands must stay below the blade roots.
    fan = cambered_blade_fan(r_hub=12.0, r_tip=55.0, cup_side=None)
    assert motor_side(fan) is None


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


@pytest.mark.skipif(not _A12X25_STL.exists(), reason="reference STL not present")
def test_real_a12x25_direction_is_robust_to_unwelded_input():
    # The project builds process=False meshes (fansim/geometry/blade.py:799); prove_direction
    # must weld internally rather than silently going INCONCLUSIVE on duplicate vertices.
    mesh = trimesh.load(_A12X25_STL, process=False)
    p = prove_direction(mesh)
    assert p.verdict == "CONCLUSIVE", p.note
    assert (p.omega_sign, p.pump_sign, p.chirality) == (+1, -1, -1)


# --- Section-quality guard (thickness / midline-fit / min-radii rejections) ---
#
# A cylinder cut through a thick, non-airfoil "section" (e.g. a backward-curved centrifugal
# blower blade) can still fit *a* quadratic and *a* sign; that sign is not evidence of the
# designed rotation. Because the CFD spin is always derived from chirality, a wrong reading here
# means the prop can be built/solved leading-edge-reversed while the thrust sign still comes out
# "correct" (Fz < 0) -- see docs on fansim.propeller.direction.prop_direction.


def test_thick_non_airfoil_section_is_rejected():
    # A blade far thicker than any real airfoil (t/c well above MAX_THICKNESS_RATIO) must not
    # produce a CONCLUSIVE reading even though it is technically "cambered".
    thick_blade = cambered_blade_fan(
        n_blades=5, r_hub=15.0, r_tip=50.0, chord=20.0, stagger_deg=60.0, camber=0.06, thick=12.0,
    )
    p = prove_direction(thick_blade)
    assert p.verdict == "INCONCLUSIVE", p.note
    assert "low-quality" in p.note


def test_low_camber_below_raised_threshold_is_inconclusive():
    # MIN_CAMBER_RATIO was raised from 0.01 to 0.02 specifically to reject weakly-cambered
    # sections (like the real obj_1/3/4/5 drone impellers, which sit at 0.010-0.014) that the old
    # threshold let through on too little evidence.
    camber = 0.014  # inside the measured real-file band, below the new MIN_CAMBER_RATIO
    assert camber < MIN_CAMBER_RATIO
    weak = cambered_blade_fan(stagger_deg=60.0, camber=camber)
    p = prove_direction(weak)
    assert p.verdict == "INCONCLUSIVE", p.note
    assert "flat" in p.note


def test_single_radius_is_inconclusive_even_if_cambered():
    # A proof that only ever sampled one cut radius cannot corroborate itself across the span.
    good = cambered_blade_fan(stagger_deg=60.0, camber=0.06)
    p = prove_direction(good, r_fracs=(0.7,))
    assert p.verdict == "INCONCLUSIVE", p.note
    assert "radius" in p.note


def test_default_r_fracs_include_outer_tip_station():
    # Tip lead is the independent rotation check; default cuts must reach an outer station so
    # mid-span-only false CONCLUSIVE votes cannot stand alone (opt_run1_t9012 regression).
    assert 0.90 in DEFAULT_R_FRACS
    assert DEFAULT_R_FRACS == prove_direction.__defaults__[0]


def test_mid_only_false_mirror_becomes_inconclusive_with_tip_station():
    # Low-camber / high-chord optimizer trial: stations ≤0.85 vote (−1,+1) while the tip votes
    # Stock (+1,−1). Extending the default cuts to 0.90 must surface the disagreement as
    # INCONCLUSIVE (builder CFD then keeps AXIAL_BUILDER_DIRECTION) rather than a false mirror.
    stl = _REPO_ROOT / "runs" / "_dir_diag" / "opt_run1_t9012_rebuild.stl"
    if not stl.is_file():
        pytest.skip("t9012 rebuild fixture not present (runs/_dir_diag/opt_run1_t9012_rebuild.stl)")
    mesh = trimesh.load(str(stl), force="mesh")
    mid_only = prove_direction(mesh, r_fracs=(0.55, 0.65, 0.75, 0.85))
    assert mid_only.verdict == "CONCLUSIVE", mid_only.note
    assert (mid_only.omega_sign, mid_only.pump_sign) == (-1, +1)
    full = prove_direction(mesh)
    assert full.verdict == "INCONCLUSIVE", full.note
    assert "disagree" in full.note


def test_good_synthetic_section_survives_quality_guard():
    # Sanity: the default synthetic oracle keeps working under the new thresholds (thin airfoil,
    # exact parabolic camber midline -> ~0 residual, t/c well under the cap).
    good = cambered_blade_fan(stagger_deg=60.0, camber=0.06)
    p = prove_direction(good)
    assert p.verdict == "CONCLUSIVE", p.note
    assert "0 low-quality skipped" in p.note


@pytest.mark.skipif(not _OBJ_1.exists(), reason="drone reference STL not present")
def test_real_obj1_low_camber_is_inconclusive_under_raised_threshold():
    # obj_1's real camber sits at ~0.010-0.014 (well documented in the review); the raised
    # MIN_CAMBER_RATIO (0.02) must now reject it outright, rather than accept a marginal signal.
    mesh = trimesh.load(str(_OBJ_1), force="mesh")
    p = prove_direction(mesh)
    assert p.verdict == "INCONCLUSIVE", p.note


@pytest.mark.skipif(not _OBJ_2.exists(), reason="drone reference STL not present")
def test_real_obj2_radial_impeller_is_inconclusive():
    # obj_2 is a thin backward-curved centrifugal (radial) blower blade, not an axial airfoil:
    # t/c ~0.475 and a midline residual ~7x the camber height. It used to read CONCLUSIVE (with
    # ambiguous ω) purely because a quadratic can always be fit to *something*; the section
    # quality guard must now refuse it.
    mesh = trimesh.load(str(_OBJ_2), force="mesh")
    p = prove_direction(mesh)
    assert p.verdict == "INCONCLUSIVE", p.note
    assert "low-quality" in p.note


@pytest.mark.skipif(
    not (_OBJ_6.exists() and _OBJ_7.exists() and _OBJ_8.exists()),
    reason="drone reference STL not present",
)
@pytest.mark.parametrize("stl", [_OBJ_6, _OBJ_7, _OBJ_8])
def test_real_obj6_7_8_radial_impellers_are_inconclusive(stl):
    mesh = trimesh.load(str(stl), force="mesh")
    p = prove_direction(mesh)
    assert p.verdict == "INCONCLUSIVE", p.note


@pytest.mark.parametrize("side", [+1, -1])
def test_motor_side_when_first_probe_lands_on_the_bore_wall(side, monkeypatch):
    # QA 2026-10-08 (roadmap §23.6): on Linux the tip radius came out 50.00000000000001, so the
    # first probe (0.1*tip) sat exactly on the 5 mm bore wall, the cut returned spurious loops,
    # r_root was taken there and every band fell inside the empty bore -> None. Force that case.
    from fansim.audit import direction

    monkeypatch.setattr(direction, "_tip_radius", lambda mesh: 50.00000000000001)
    assert motor_side(cambered_blade_fan(cup_side=side, bore_r=5.000000000000001)) == side
