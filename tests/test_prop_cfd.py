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
    src_bytes_before = src.read_bytes()

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

    # M3: the input STL is unchanged, and the working copy evaluate_prop_cfd made from it
    # (work/"prop.stl") is also never flipped in place -- the oriented copy for CFD goes to a
    # separate file (work/"prop_cfd.stl").
    assert src.read_bytes() == src_bytes_before
    assert (work / "prop.stl").read_bytes() == src_bytes_before
    assert (work / "prop_cfd.stl").is_file()

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


@pytest.mark.slow
def test_evaluate_prop_cfd_builder_geometry_never_raises_for_stubby_design(tmp_path, monkeypatch):
    # Regression for the Task 8 re-review bug: a random_prop_flat-style stubby/low-camber design
    # (built in-house via build_impeller) is expected to be INCONCLUSIVE under the direction
    # proof's section-quality guard, but that must NOT abort evaluate_prop_cfd -- the builder path
    # (direction="auto", no stl_mm) must resolve via BUILDER_DIRECTION regardless.
    import trimesh

    from fansim.audit.direction import prove_direction
    from fansim.geometry import build_impeller, export_stl
    from fansim.prop_spec import get_prop_spec
    from fansim.propeller import cfd as prop_cfd
    from fansim.propeller.geometry import prop_blade_params

    spec = get_prop_spec("fpv_5inch")
    # Since the builder's LE fix (3a577c6) random designs usually read CONCLUSIVE, so build a
    # deliberately unreadable one: zero camber has no concave side for the proof to read.
    blade = prop_blade_params(spec, camber=(0.0, 0.0, 0.0))
    check_stl = tmp_path / "check.stl"
    export_stl(build_impeller(blade), check_stl, tolerance=0.02, angular_tolerance=0.1)
    assert prove_direction(trimesh.load(str(check_stl), force="mesh")).verdict == "INCONCLUSIVE"

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

    out = prop_cfd.evaluate_prop_cfd(spec, tmp_path, params=blade, rpm=20000.0)
    assert out["orientation"] == "flipped"
    assert out["direction_source"] == "builder"
    assert out["spin"] == -1
    assert out["direction_crosscheck"]["verdict"] == "INCONCLUSIVE"


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


def _write_series(tmp_path, fz, mz):
    fo = tmp_path / "postProcessing" / "forces" / "0"
    fo.mkdir(parents=True, exist_ok=True)
    (fo / "force.dat").write_text("#\n" + "".join(
        f"{i}  (0 0 {v}) (0 0 {v}) (0 0 0)\n" for i, v in enumerate(fz, 1)), encoding="utf-8")
    (fo / "moment.dat").write_text("#\n" + "".join(
        f"{i}  (0 0 {v}) (0 0 {v}) (0 0 0)\n" for i, v in enumerate(mz, 1)), encoding="utf-8")


def test_parse_prop_metrics_tail_mean_and_convergence(tmp_path):
    from fansim.propeller.cfd import parse_prop_metrics

    # ramp then a +-0.2 N limit cycle around -4.0 N: tail mean, not the final phase sample
    fz = [-1.0 - 0.25 * i for i in range(12)] + [-3.8, -4.2] * 2
    mz = [0.05] * 16
    _write_series(tmp_path, fz, mz)
    m = parse_prop_metrics(tmp_path, omega_rad_s=600.0)
    assert m["thrust_n"] == pytest.approx(-4.0)      # mean of the last 25 %
    assert m["converged"] is True and m["thrust_oscillation_pct"] == pytest.approx(10.0)
    assert m["moment_z_nm"] == pytest.approx(0.05)


def test_parse_prop_metrics_unconverged_drift(tmp_path):
    from fansim.propeller.cfd import parse_prop_metrics

    _write_series(tmp_path, [-1.0 - 0.3 * i for i in range(16)], [0.05] * 16)
    assert parse_prop_metrics(tmp_path, omega_rad_s=600.0)["converged"] is False


def _prop_result(thrust_n, power_w, mz, sign_ok=True, conv=True):
    return {"thrust_n": thrust_n, "thrust_n_raw": -thrust_n, "thrust_sign_ok": sign_ok,
            "shaft_power_w": power_w, "moment_z_nm": mz, "converged": conv,
            "thrust_shift_pct": 0.5, "thrust_oscillation_pct": 2.0, "torque_shift_pct": 0.4}


def test_prop_sanity_momentum_bound():
    from fansim.cfd.sanity import run_prop_sanity

    R, rho, w = 0.1143, 1.177, -631.0           # 9 in prop at ~6026 rpm (oriented spin -1)
    # UIUC APC SF 9x4.7 static: ~3.94 N at ~36.7 W -> FM ~0.6, plausible
    good = {c.name: c for c in run_prop_sanity(_prop_result(3.94, 36.7, 0.058), omega_signed=w,
                                               tip_radius_m=R, rho=rho)}
    assert good["momentum_fm"].status == "PASS" and 0.4 < good["momentum_fm"].value < 0.8
    assert good["power_sign"].status == "PASS" and good["thrust_direction"].status == "PASS"
    # more thrust than momentum theory allows for that power -> FAIL (energy from nowhere)
    over = {c.name: c for c in run_prop_sanity(_prop_result(3.94, 10.0, 0.016), omega_signed=w,
                                               tip_radius_m=R, rho=rho)}
    assert over["momentum_fm"].status == "FAIL"
    # the 2026-09-22 drone obj_2 numbers (9.2 N on 2034 W, D 90 mm) read FM ~0.11 -> WARN
    drone = {c.name: c for c in run_prop_sanity(_prop_result(9.2, 2034.0, 0.77),
                                                omega_signed=-2645.0, tip_radius_m=0.045, rho=rho)}
    assert drone["momentum_fm"].status == "WARN"


def test_prop_sanity_wrong_way():
    from fansim.cfd.sanity import run_prop_sanity

    bad = {c.name: c for c in run_prop_sanity(_prop_result(-2.0, 30.0, -0.05, sign_ok=False),
                                              omega_signed=-631.0, tip_radius_m=0.1143,
                                              rho=1.177)}
    assert bad["thrust_direction"].status == "FAIL"
    assert bad["power_sign"].status == "FAIL"      # Mz*w > 0: the air is driving the rotor
    assert bad["momentum_fm"].status == "SKIP"


def test_build_prop_case_entrain_boundaries(tmp_path):
    """Static-prop entrainment: ambient total pressure on upstream + sides, sides retyped patch."""
    import trimesh

    from fansim.propeller.cfd import build_prop_case, prop_open_air

    stl = tmp_path / "p.stl"
    trimesh.creation.cylinder(radius=50.0, height=8.0, sections=24).export(str(stl))
    dom = prop_open_air(0.05, -0.004, 0.004, rpm=6000.0)
    case = build_prop_case(tmp_path / "c", stl, dom, n_iters=10, n_subdomains=1, bc="entrain")
    p = (case / "0/p").read_text(encoding="utf-8")
    u = (case / "0/U").read_text(encoding="utf-8")
    assert p.count("totalPressure") == 2 and "outlet   { type fixedValue" in p
    assert u.count("pressureInletOutletVelocity") == 2 and "freestreamVelocity" not in u
    assert "walls  { type patch;" in (case / "system/blockMeshDict").read_text(encoding="utf-8")
    # default stays the freestream set used by forward-flight polars
    case2 = build_prop_case(tmp_path / "c2", stl, dom, n_iters=10, n_subdomains=1)
    assert "freestreamVelocity" in (case2 / "0/U").read_text(encoding="utf-8")
    assert "walls  { type wall;" in (case2 / "system/blockMeshDict").read_text(encoding="utf-8")
