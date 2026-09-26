"""build_case refuses rotors outside the MRF zone and frames/stators overlapping the rotor."""

from __future__ import annotations

import pytest
import trimesh

from fansim.cfd.domain import TestRig as _Rig
from fansim.cfd.openfoam_case import build_case, check_placement


def _rig(mrf=(-0.010, 0.010)) -> _Rig:
    return _Rig(duct_radius=0.06, tip_gap=0.0005, inlet_length=0.24, outlet_length=0.48,
                   impeller_z_min=-0.008, impeller_z_max=0.008, mrf_z_min=mrf[0], mrf_z_max=mrf[1],
                   rpm=2000.0, inlet_velocity=2.0)


def _box(z_lo_mm: float, z_hi_mm: float) -> trimesh.Trimesh:
    m = trimesh.creation.box(extents=(20.0, 20.0, z_hi_mm - z_lo_mm))
    m.apply_translation([0.0, 0.0, 0.5 * (z_lo_mm + z_hi_mm)])
    return m


def test_ok_when_inside_and_frame_downstream():
    check_placement(_box(-8.0, 8.4), _rig(), downstream_mm={"frame": _box(10.5, 18.5)})


def test_rotor_outside_mrf_raises():
    with pytest.raises(ValueError, match="MRF"):
        check_placement(_box(-8.1, 8.4), _rig(mrf=(-0.005, 0.005)))


def test_frame_overlapping_rotor_raises():
    with pytest.raises(ValueError, match="frame"):
        check_placement(_box(-8.0, 8.4), _rig(), downstream_mm={"frame": _box(5.5, 13.5)})


def test_dual_mrf_uses_front_to_rear_span():
    dual = {"front_z_min": -0.012, "front_z_max": 0.0, "rear_z_min": 0.0, "rear_z_max": 0.012,
            "omega_front": -200.0, "omega_rear": 200.0}
    check_placement(_box(-11.0, 11.0), _rig(mrf=(-0.001, 0.001)), dual_mrf=dual)
    with pytest.raises(ValueError, match="MRF"):
        check_placement(_box(-13.0, 11.0), _rig(), dual_mrf=dual)


def test_build_case_runs_the_check(tmp_path):
    stl = tmp_path / "rotor.stl"
    _box(-8.1, 8.4).export(str(stl))
    with pytest.raises(ValueError, match="MRF"):
        build_case(tmp_path / "case", stl, _rig(mrf=(-0.005, 0.005)), back_pressure_pa=0.0)
