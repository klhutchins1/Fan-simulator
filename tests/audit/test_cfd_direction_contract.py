"""Pins the CFD direction *meanings* (not their correctness — that is Audit #1's verdict)."""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest
import trimesh

from fansim.cfd.domain import TestRig as _Rig
from fansim.cfd.metrics import parse_fan_metrics
from fansim.cfd.openfoam_case import build_case


def _rig(spin: int) -> _Rig:
    return _Rig(duct_radius=0.06, tip_gap=0.0005, inlet_length=0.24, outlet_length=0.48,
                   impeller_z_min=-0.008, impeller_z_max=0.008, mrf_z_min=-0.01, mrf_z_max=0.01,
                   rpm=2000.0, inlet_velocity=2.0, spin=spin)


def _case(tmp_path: Path, spin: int) -> Path:
    stl = tmp_path / "box.stl"
    trimesh.creation.box(extents=(20.0, 20.0, 5.0)).export(str(stl))
    return build_case(tmp_path / f"case_{spin}", stl, _rig(spin), back_pressure_pa=0.0)


def test_mrf_is_right_handed_about_plus_z_with_signed_omega(tmp_path):
    for spin in (-1, 1):
        text = (_case(tmp_path, spin) / "constant/MRFProperties").read_text(encoding="utf-8")
        assert re.search(r"axis\s+\(0 0 1\);", text)
        omega = float(re.search(r"omega\s+([-+\d.eE]+);", text).group(1))
        assert omega == pytest.approx(spin * 2000.0 * 2.0 * math.pi / 60.0, rel=1e-12)


def test_inlet_is_min_z_outlet_is_max_z(tmp_path):
    text = (_case(tmp_path, -1) / "system/blockMeshDict").read_text(encoding="utf-8")
    verts = re.findall(r"\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)", text.split("blocks")[0])
    zs = [float(z) for _, _, z in verts[:8]]
    assert zs[:4] == [min(zs)] * 4 and zs[4:] == [max(zs)] * 4
    assert "inlet  { type patch; faces ((0 3 2 1)); }" in text
    assert "outlet { type patch; faces ((4 5 6 7)); }" in text


def test_free_air_bcs_are_asymmetric(tmp_path):
    """Total-pressure inlet (-Z), static outlet (+Z): reversed through-flow gets easier BCs.

    This is why Audit #1 judges each rotation only in the orientation where it pumps +Z.
    """
    p = (_case(tmp_path, -1) / "0/p").read_text(encoding="utf-8")
    assert re.search(r"inlet\s+\{\s*type totalPressure; p0 uniform 0;", p)
    assert re.search(r"outlet\s+\{\s*type fixedValue; value uniform 0", p)


def test_outlet_flow_is_signed_phi_sum_on_plus_z_outlet(tmp_path):
    text = (_case(tmp_path, -1) / "system/controlDict").read_text(encoding="utf-8")
    block = text[text.index("outletFlow"):]
    block = block[:block.index("}") + 1]
    assert "name            outlet;" in block
    assert "operation       sum;" in block and "fields          (phi);" in block


def _write_pp(case: Path, flow: float, mz: float) -> None:
    def put(fo, fname, row):
        d = case / "postProcessing" / fo / "0"
        d.mkdir(parents=True, exist_ok=True)
        (d / fname).write_text("\n".join(row for _ in range(10)) + "\n", encoding="utf-8")
    put("forces", "moment.dat", f"1 (0 0 {mz}) (0 0 0) (0 0 0)")
    put("forces", "force.dat", "1 (0 0 0.05) (0 0 0) (0 0 0)")
    put("outletFlow", "surfaceFieldValue.dat", f"1 {flow}")
    put("inletP", "surfaceFieldValue.dat", "1 0.0")
    put("outletP", "surfaceFieldValue.dat", "1 0.0")


def test_metrics_keep_flow_and_moment_signed(tmp_path):
    # Negative moment_z with distinct x/y/z to prove we're reading the z-component.
    _write_pp(tmp_path, flow=-0.02, mz=-0.003)
    d = tmp_path / "postProcessing" / "forces" / "0"
    (d / "moment.dat").write_text("\n".join("1 (0.111 0.222 -0.003) (0 0 0) (0 0 0)" for _ in range(10)) + "\n", encoding="utf-8")
    m = parse_fan_metrics(tmp_path, omega_rad_s=209.4)
    assert m.flow_m3s < 0 and m.cfm < 0          # reverse flow reads negative, never abs()
    assert m.moment_z_nm == pytest.approx(-0.003) # signed z-component
    assert m.torque_nm == pytest.approx(0.003)    # torque is |Mz|


def test_metrics_read_the_numerically_newest_time_folder(tmp_path):
    """QA-39 (957a483): a restarted case has time folders 20 and 100. CFM must come from 100.

    Sorting folder names as text puts "100" before "20", so the old code read the stale run.
    """
    _write_pp(tmp_path, flow=0.01, mz=0.002)
    pp = tmp_path / "postProcessing"
    for fo in ("forces", "outletFlow", "inletP", "outletP"):
        (pp / fo / "0").rename(pp / fo / "20")
    d = pp / "outletFlow" / "100"
    d.mkdir()
    (d / "surfaceFieldValue.dat").write_text("\n".join("101 0.03" for _ in range(10)) + "\n",
                                             encoding="utf-8")
    m = parse_fan_metrics(tmp_path, omega_rad_s=209.4)
    assert m.flow_m3s == pytest.approx(0.03)
    assert m.cfm == pytest.approx(0.03 * (60.0 / (0.3048**3)), rel=1e-12)


def test_axial_convention_is_flipped_at_spin_minus_one():
    from fansim.cfd.orientation import AXIAL_CFD_ORIENTATION
    assert AXIAL_CFD_ORIENTATION == "flipped"
    assert _Rig.__dataclass_fields__["spin"].default == -1


def test_rig_spin_matches_geometry_derived_orientation():
    """Derive the production spin from Audit #1's measured geometry evidence, not a literal.

    docs/validation/audits/direction_geometry.json records the designed omega sign (as built) for
    each rotor from real geometric measurement. Both rotors must agree, and the production spin
    must equal orientation_sign * designed, where orientation_sign flips the sign iff the CFD copy
    is oriented "flipped" relative to as-built.
    """
    import json

    from fansim.cfd.orientation import AXIAL_CFD_ORIENTATION

    geom_path = (Path(__file__).resolve().parents[2]
                / "docs" / "validation" / "audits" / "direction_geometry.json")
    data = json.loads(geom_path.read_text(encoding="utf-8"))
    designed = data["rotors"]["stock"]["omega_sign"]
    assert designed == data["rotors"]["reference_stl"]["omega_sign"]
    orientation_sign = -1 if AXIAL_CFD_ORIENTATION == "flipped" else +1
    rig = _rig(_Rig.__dataclass_fields__["spin"].default)
    assert rig.spin == orientation_sign * designed
