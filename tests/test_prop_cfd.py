from __future__ import annotations
import math
from pathlib import Path

import pytest

def test_parse_prop_metrics_from_forces(tmp_path):
    from fansim.propeller.cfd import parse_prop_metrics
    fo = tmp_path / "postProcessing" / "forces" / "100"
    fo.mkdir(parents=True)
    # time total(x y z) pressure... viscous...
    (fo / "force.dat").write_text(
        "#\n100  (0 0 12.5) (0 0 12) (0 0 0.5)\n", encoding="utf-8")
    (fo / "moment.dat").write_text(
        "#\n100  (0 0 -0.4) (0 0 -0.4) (0 0 0)\n", encoding="utf-8")
    m = parse_prop_metrics(tmp_path, omega_rad_s=1000.0)
    assert m["thrust_n"] == pytest.approx(12.5)
    assert m["thrust_g"] == pytest.approx(12.5 / 9.80665 * 1000.0, rel=1e-3)
    assert m["torque_nm"] == pytest.approx(0.4)
    assert m["shaft_power_w"] == pytest.approx(0.4 * 1000.0)


def test_prop_open_air_extents():
    from fansim.propeller.cfd import prop_open_air
    R = 0.0635  # 5-inch tip radius
    d = prop_open_air(R, z_lo_m=-0.01, z_hi_m=0.01, rpm=21000.0)
    assert d.domain_radius == pytest.approx(5.0 * R)
    assert d.z_min == pytest.approx(-0.01 - 2.0 * R)
    assert d.z_max == pytest.approx(0.01 + 4.0 * R)
    assert d.mrf_z_min < -0.01 and d.mrf_z_max > 0.01
    # Default spin=-1 (same handedness as ducted-fan MRF → +z thrust).
    assert d.omega_signed == pytest.approx(-21000.0 * 2.0 * math.pi / 60.0)
    assert d.u_freestream == pytest.approx(1.0)


def test_prop_templates_declare_rhosimple():
    from fansim.cfd import templates as T
    assert "rhoSimpleFoam" in T.PROP_CONTROL_DICT
    assert "hePsiThermo" in T.PROP_THERMO or "perfectGas" in T.PROP_THERMO
    assert "forces" in T.PROP_CONTROL_DICT
    assert "alphatWallFunction" in T.PROP_ALPHAT or "compressible::alphatWallFunction" in T.PROP_ALPHAT
    assert "alphatWallFunction" in T.PROP_ALPHAT or "compressible::alphatWallFunction" in T.PROP_ALPHAT
    assert "wallDist" in T.PROP_FV_SCHEMES and "meshWave" in T.PROP_FV_SCHEMES
    assert "div(phi,Ekp)" in T.PROP_FV_SCHEMES
    assert "div(phiMRF,p)" in T.PROP_FV_SCHEMES


def test_cli_evaluate_prop_cfd_declares_flags():
    from tests._cli_parsers import load_build_parser

    ap = load_build_parser("evaluate_prop_cfd.py")()
    args = ap.parse_args(["--dry-run", "--spec", "fpv_5inch"])
    assert args.dry_run is True
    assert args.spec == "fpv_5inch"
    help_text = ap.format_help()
    assert "rhoSimpleFoam" in help_text or "prop" in help_text.lower()


def test_evaluate_prop_cfd_auto_with_explicit_spin_raises(tmp_path):
    from fansim.prop_spec import get_prop_spec
    from fansim.propeller.cfd import evaluate_prop_cfd

    spec = get_prop_spec("fpv_5inch")
    with pytest.raises(ValueError, match="direction='manual'"):
        evaluate_prop_cfd(spec, tmp_path, spin=-1, direction="auto")


def test_evaluate_prop_cfd_invalid_direction_raises(tmp_path):
    from fansim.prop_spec import get_prop_spec
    from fansim.propeller.cfd import evaluate_prop_cfd

    spec = get_prop_spec("fpv_5inch")
    with pytest.raises(ValueError, match="direction"):
        evaluate_prop_cfd(spec, tmp_path, direction="sideways")


def test_evaluate_prop_cfd_auto_direction_orients_case(tmp_path, monkeypatch):
    import re

    import trimesh

    from fansim.audit.synthetic import cambered_blade_fan
    from fansim.prop_spec import get_prop_spec
    from fansim.propeller import cfd as prop_cfd

    mesh = cambered_blade_fan(
        n_blades=2, r_hub=6.0, r_tip=60.0, chord=15.0, stagger_deg=60.0, camber=0.06,
    )  # geometry proof: pump_sign=-1 -> orientation "flipped", spin -1 (see test_prop_thrust_sign)
    src = tmp_path / "prop.stl"
    mesh.export(str(src))
    asbuilt = trimesh.load(str(src), force="mesh")
    z0_before, z1_before = float(asbuilt.bounds[0, 2]), float(asbuilt.bounds[1, 2])

    work = tmp_path / "case"
    monkeypatch.setattr(prop_cfd, "run_mesh", lambda *_a, **_k: None)
    monkeypatch.setattr(prop_cfd, "run_solve_prop", lambda *_a, **_k: None)
    monkeypatch.setattr(
        prop_cfd,
        "parse_prop_metrics",
        lambda *_a, **_k: {
            "thrust_n": -0.5, "thrust_g": 51.0, "torque_nm": 0.01, "shaft_power_w": 5.0,
        },
    )
    import fansim.cfd.runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "OpenFOAMRunner",
        lambda workdir: type("R", (), {"run": staticmethod(lambda *a, **k: None)})(),
    )

    out = prop_cfd.evaluate_prop_cfd(
        get_prop_spec("cine_3inch"),
        work,
        rpm=20000.0,
        stl_mm=src,
        prepare_stl=False,
    )
    assert out["orientation"] == "flipped"
    assert out["direction_source"] == "geometry"
    assert out["spin"] == -1

    mrf = (work / "constant/MRFProperties").read_text(encoding="utf-8")
    m = re.search(r"omega\s+([-\d.eE]+);", mrf)
    assert m is not None and float(m.group(1)) < 0.0  # spin=-1 -> negative omega_signed

    toposet = (work / "system/topoSetDict").read_text(encoding="utf-8")
    zmin_used = float(re.search(r"point1\s+\(0 0 ([-\d.eE]+)\)", toposet).group(1))
    zmax_used = float(re.search(r"point2\s+\(0 0 ([-\d.eE]+)\)", toposet).group(1))
    # The MRF z-range must contain the FLIPPED (mirrored) bounds, not the as-built ones.
    z0_flipped, z1_flipped = -z1_before / 1000.0, -z0_before / 1000.0
    assert zmin_used <= z0_flipped + 1e-9
    assert zmax_used >= z1_flipped - 1e-9


def test_default_rpm_tip_mach_compressible():
    from fansim.prop_spec import get_prop_spec

    spec = get_prop_spec("fpv_5inch")
    rpm = 0.7 * spec.rpm_max
    assert spec.tip_mach(rpm) > 0.3


def test_build_prop_case_writes_compressible(tmp_path):
    from fansim.propeller.cfd import prop_open_air, build_prop_case
    from fansim.propeller.geometry import build_prop
    from fansim.prop_spec import get_prop_spec
    from fansim.cfd.openfoam_case import MeshResolution

    spec = get_prop_spec("fpv_5inch")
    stl = tmp_path / "prop.stl"
    build_prop(spec, stl)

    # bounds from report
    from fansim.geometry import watertight_report
    rep = watertight_report(stl)
    (_, _, z0), (_, _, z1) = rep.bounds_mm
    R = spec.diameter_mm / 2000.0
    dom = prop_open_air(R, z0 / 1000.0, z1 / 1000.0, rpm=0.7 * spec.rpm_max)

    case = tmp_path / "case"
    build_prop_case(case, stl, dom, mesh=MeshResolution(base_cell=0.01), n_iters=10, n_subdomains=2)

    ctrl = (case / "system/controlDict").read_text(encoding="utf-8")
    assert "rhoSimpleFoam" in ctrl
    assert (case / "constant/thermophysicalProperties").is_file()
    assert (case / "0/T").is_file()
    assert (case / "0/alphat").is_file()

    mrf = (case / "constant/MRFProperties").read_text(encoding="utf-8")
    assert "rotor" in mrf
    assert "omega" in mrf.lower() or str(int(dom.omega_signed))[:4] in mrf or "omega" in mrf
