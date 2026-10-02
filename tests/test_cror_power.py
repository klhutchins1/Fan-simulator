"""CROR shaft power: each counter-rotating rotor's torque counts (Audit #7), not the net."""

from __future__ import annotations

from pathlib import Path

import pytest
import trimesh

from fansim.cfd.metrics import parse_fan_metrics
from fansim.cfd.openfoam_case import add_rear_forces, split_dual_rotor_surface
from fansim.cfd.sanity import _check_power_sign


def _write_pp(case: Path, fo: str, filename: str, rows: str) -> None:
    d = case / "postProcessing" / fo / "0"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text("# header\n" + rows, encoding="utf-8")


def _cror_case(tmp_path: Path, m_front: float, m_rear: float) -> Path:
    case = tmp_path / "case"
    _write_pp(case, "forces", "moment.dat", f"600  0 0 {m_front}  0 0 {m_front}  0 0 0\n")
    _write_pp(case, "forces", "force.dat", "600  0 0 -0.10  0 0 -0.10  0 0 0\n")
    _write_pp(case, "forcesRear", "moment.dat", f"600  0 0 {m_rear}  0 0 {m_rear}  0 0 0\n")
    _write_pp(case, "forcesRear", "force.dat", "600  0 0 -0.06  0 0 -0.06  0 0 0\n")
    _write_pp(case, "outletFlow", "surfaceFieldValue.dat", "600  0.02\n")
    _write_pp(case, "inletP", "surfaceFieldValue.dat", "600  0.0\n")
    _write_pp(case, "outletP", "surfaceFieldValue.dat", "600  0.0\n")
    (case / "constant").mkdir()
    (case / "constant" / "MRFProperties").write_text(
        "MRF1 { omega 209.44; }\nMRF2 { omega -209.44; }\n", encoding="utf-8")
    return case


def test_counter_rotating_torques_add_not_cancel(tmp_path):
    # Upstream turns +w (reaction Mz < 0), downstream -w (Mz > 0): net moment nearly cancels.
    case = _cror_case(tmp_path, m_front=-0.010, m_rear=+0.009)
    m = parse_fan_metrics(case, omega_rad_s=209.44)
    assert m.torque_nm == pytest.approx(0.019)                 # |-0.010| + |0.009|
    assert m.shaft_power_w == pytest.approx(0.019 * 209.44)    # was 0.001 * w with the net
    assert m.moment_z_nm == pytest.approx(-0.001) and m.moment_z_rear_nm == pytest.approx(0.009)
    assert m.thrust_n == pytest.approx(-0.16)


def test_power_sign_checks_each_rotor(tmp_path):
    ok = parse_fan_metrics(_cror_case(tmp_path, -0.010, +0.009), omega_rad_s=209.44)
    assert _check_power_sign(ok, None, tmp_path / "case").status == "PASS"
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    bad = parse_fan_metrics(_cror_case(bad_dir, -0.010, -0.002), omega_rad_s=209.44)
    # downstream rotor is being driven by the flow (windmilling): Mz * w > 0 -> FAIL
    assert _check_power_sign(bad, None, bad_dir / "case").status == "FAIL"


def test_split_dual_rotor_surface_at_gap():
    a = trimesh.creation.box(extents=(0.02, 0.02, 0.004))
    a.apply_translation((0, 0, -0.004))
    b = trimesh.creation.box(extents=(0.02, 0.02, 0.004))
    b.apply_translation((0, 0, +0.004))
    surf = trimesh.util.concatenate([a, b])
    dm = {"front_z_max": -0.001, "rear_z_min": 0.001}
    front, rear = split_dual_rotor_surface(surf, dm)
    assert front.bounds[1, 2] <= 0.0 < rear.bounds[0, 2]
    assert len(front.faces) + len(rear.faces) == len(surf.faces)
    with pytest.raises(ValueError, match="leaves one rotor empty"):
        split_dual_rotor_surface(a, dm)


def test_add_rear_forces_copies_settings(tmp_path):
    from fansim.cfd import templates as T

    cd = tmp_path / "controlDict"
    cd.write_text(T.render(T.CONTROL_DICT, {"HEADER": "", "ENDTIME": 10, "WRITEINT": 5,
                                            "FOINT": 3, "RHO": 1.2}), encoding="utf-8")
    add_rear_forces(cd)
    add_rear_forces(cd)   # idempotent
    text = cd.read_text(encoding="utf-8")
    assert text.count("forcesRear") == 1 and "patches         (impellerRear);" in text
    rear = text[text.index("forcesRear"):]
    assert "rhoInf          1.2;" in rear and "writeInterval   3;" in rear
