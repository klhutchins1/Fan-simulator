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


def test_cli_evaluate_prop_cfd_declares_flags():
    from tests._cli_parsers import load_build_parser

    ap = load_build_parser("evaluate_prop_cfd.py")()
    args = ap.parse_args(["--dry-run", "--spec", "fpv_5inch"])
    assert args.dry_run is True
    assert args.spec == "fpv_5inch"
    help_text = ap.format_help()
    assert "rhoSimpleFoam" in help_text or "prop" in help_text.lower()


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
