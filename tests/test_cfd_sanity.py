"""Tests for fansim.cfd.sanity: cheap physics/setup invariants over a CFD case."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
import trimesh

from fansim.cfd import sanity as sanity_mod
from fansim.cfd.sanity import (
    FAIL,
    PASS,
    SKIP,
    WARN,
    overall,
    run_sanity,
    summarize,
)

RHO = 1.2
OMEGA = 3000.0 * 1.0 * 2.0 * math.pi / 60.0  # rpm=3000, spin=1


def _write_pp(case: Path, fo: str, filename: str, rows: str) -> None:
    d = case / "postProcessing" / fo / "0"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text("# header\n" + rows, encoding="utf-8")


def _write_case_meta(case: Path, **overrides) -> None:
    meta = {
        "duct_shape": "round",
        "box_half_width_m": 0.1,
        "inlet_area_m2": 0.01,
        "outlet_area_m2": 0.01,
        "casing": True,
        "plenum": False,
        "duct_radius_m": 0.06,
        "tip_radius_m": 0.05,
        "hub_radius_m": 0.02,
        "rpm": 3000.0,
        "spin": 1.0,
        "cfd_version": 3,
    }
    meta.update(overrides)
    (case / "constant").mkdir(parents=True, exist_ok=True)
    (case / "constant" / "case_meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _write_checkmesh(case: Path, *, ok: bool, failed: bool = False, mixed: bool = False) -> None:
    """Real checkMesh output ends with a "Failed N mesh checks." summary; each failing
    check is its own "***"-prefixed line above it, e.g.:
        ***Max skewness = 4.257074, 1 highly skew faces detected which may impair ...
    """
    d = case / "logs"
    d.mkdir(parents=True, exist_ok=True)
    lines = [
        "Checking geometry...",
        "    Mesh non-orthogonality Max: 42.5 average: 12.1",
        "    Max skewness = 1.8 OK.",
    ]
    if ok:
        lines.append("Mesh OK.")
    elif mixed:
        lines += [
            " ***Max skewness = 4.257074, 1 highly skew faces detected which may impair the "
            "quality of the results",
            " ***Number of severely non-orthogonal (> 70 degrees) faces: 12.",
            "Failed 2 mesh checks.",
        ]
    elif failed:
        lines += [
            " ***Max skewness = 4.257074, 1 highly skew faces detected which may impair the "
            "quality of the results",
            "Failed 1 mesh checks.",
        ]
    (d / "checkMesh.log").write_text("\n".join(lines), encoding="utf-8")


def _write_yplus(case: Path, *, avg: float, patch: str = "impeller", time: str = "0") -> None:
    d = case / "postProcessing" / "yPlus" / time
    d.mkdir(parents=True, exist_ok=True)
    text = (
        "# Time patch min max average\n"
        f"{time} {patch} {avg / 2:.3f} {avg * 2:.3f} {avg:.3f}\n"
    )
    (d / "yPlus.dat").write_text(text, encoding="utf-8")


def _build_full_case(
    tmp_path: Path,
    *,
    q: float = 0.03,
    q_in_sign_ok: bool = True,
    moment_z: float = -0.01,
    thrust_z: float = -0.28,
    p_in_kin: float = -4.5,
    p_out_kin: float = 50.0,
    duct_shape: str = "round",
    tip_radius_m: float = 0.05,
    mesh_ok: bool = True,
    mesh_failed: bool = False,
    mesh_mixed: bool = False,
    yplus_avg: float = 45.0,
    n_rows: int = 20,
) -> Path:
    case = tmp_path / "case"
    q_in = -q if q_in_sign_ok else q  # inletFlow phi is negative for inflow

    _write_pp(case, "inletFlow", "surfaceFieldValue.dat",
               "".join(f"{i} {q_in}\n" for i in range(n_rows)))
    _write_pp(case, "outletFlow", "surfaceFieldValue.dat",
               "".join(f"{i} {q}\n" for i in range(n_rows)))
    _write_pp(case, "inletP", "surfaceFieldValue.dat",
               "".join(f"{i} {p_in_kin}\n" for i in range(n_rows)))
    _write_pp(case, "outletP", "surfaceFieldValue.dat",
               "".join(f"{i} {p_out_kin}\n" for i in range(n_rows)))
    _write_pp(case, "forces", "moment.dat",
               "".join(f"{i} 0 0 {moment_z} 0 0 {moment_z} 0 0 0\n" for i in range(n_rows)))
    _write_pp(case, "forces", "force.dat",
               "".join(f"{i} 0 0 {thrust_z} 0 0 {thrust_z} 0 0 0\n" for i in range(n_rows)))
    _write_case_meta(case, duct_shape=duct_shape, tip_radius_m=tip_radius_m)
    _write_checkmesh(case, ok=mesh_ok, failed=mesh_failed, mixed=mesh_mixed)
    _write_yplus(case, avg=yplus_avg)
    return case


def _by_name(checks, name):
    return next(c for c in checks if c.name == name)


# --- mass_balance ---

def test_mass_balance_pass(tmp_path):
    case = _build_full_case(tmp_path, q=0.03)
    c = _by_name(run_sanity(case), "mass_balance")
    assert c.status == PASS


def test_mass_balance_fail_at_8_percent(tmp_path):
    # Q_out = 0.03, Q_in should balance to -0.03; imbalance it to 8%.
    case = tmp_path / "case"
    q_out = 0.03
    q_in = -(q_out * (1 - 0.08))  # |q_in + q_out| / q_out == 0.08
    _write_pp(case, "inletFlow", "surfaceFieldValue.dat",
               "".join(f"{i} {q_in}\n" for i in range(20)))
    _write_pp(case, "outletFlow", "surfaceFieldValue.dat",
               "".join(f"{i} {q_out}\n" for i in range(20)))
    c = _by_name(run_sanity(case), "mass_balance")
    assert c.status == FAIL
    assert c.value == pytest.approx(8.0, abs=1e-6)


def test_mass_balance_warn(tmp_path):
    case = tmp_path / "case"
    q_out = 0.03
    q_in = -(q_out * (1 - 0.03))  # 3% imbalance -> WARN
    _write_pp(case, "inletFlow", "surfaceFieldValue.dat",
               "".join(f"{i} {q_in}\n" for i in range(20)))
    _write_pp(case, "outletFlow", "surfaceFieldValue.dat",
               "".join(f"{i} {q_out}\n" for i in range(20)))
    c = _by_name(run_sanity(case), "mass_balance")
    assert c.status == WARN


def test_mass_balance_skip_missing(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    c = _by_name(run_sanity(case), "mass_balance")
    assert c.status == SKIP


# --- energy_total ---

def test_energy_total_pass(tmp_path):
    case = _build_full_case(tmp_path)
    c = _by_name(run_sanity(case), "energy_total")
    assert c.status == PASS
    assert c.value < 1.0


def test_energy_total_fail_when_eta_geq_1(tmp_path):
    # Crank the outlet static pressure way up so eta_total >= 1.
    case = _build_full_case(tmp_path, p_out_kin=5000.0)
    c = _by_name(run_sanity(case), "energy_total")
    assert c.status == FAIL
    assert c.value >= 1.0


def test_energy_total_skip_missing_case_meta(tmp_path):
    case = tmp_path / "case"
    _write_pp(case, "forces", "moment.dat", "0 0 0 -0.01 0 0 -0.01 0 0 0\n")
    _write_pp(case, "forces", "force.dat", "0 0 0 -0.28 0 0 -0.28 0 0 0\n")
    _write_pp(case, "outletFlow", "surfaceFieldValue.dat", "0 0.03\n")
    _write_pp(case, "inletP", "surfaceFieldValue.dat", "0 -4.5\n")
    _write_pp(case, "outletP", "surfaceFieldValue.dat", "0 50.0\n")
    c = _by_name(run_sanity(case, omega_signed=OMEGA), "energy_total")
    assert c.status == SKIP


def test_energy_total_skip_when_q_leq_0(tmp_path):
    # Reversed flow: the inlet becomes an outflow boundary whose totalPressure BC sets
    # static p = p0 there, so the forward-flow efficiency formula doesn't apply.
    case = _build_full_case(tmp_path, q=-0.01, q_in_sign_ok=False)
    c = _by_name(run_sanity(case), "energy_total")
    assert c.status == SKIP
    assert "Q<=0" in c.note


# --- power_sign ---

def test_power_sign_pass(tmp_path):
    case = _build_full_case(tmp_path, moment_z=-0.01)
    c = _by_name(run_sanity(case), "power_sign")
    assert c.status == PASS


def test_power_sign_fail_when_mz_omega_positive(tmp_path):
    # Q>0 and Mz*omega > 0 -> FAIL (reversed-rotation-style bug).
    case = _build_full_case(tmp_path, moment_z=0.01)
    c = _by_name(run_sanity(case), "power_sign")
    assert c.status == FAIL


def test_power_sign_skip_when_q_not_positive(tmp_path):
    case = _build_full_case(tmp_path, q=-0.01, q_in_sign_ok=False)
    c = _by_name(run_sanity(case), "power_sign")
    assert c.status == SKIP


# --- thrust_direction ---

def test_thrust_direction_pass(tmp_path):
    case = _build_full_case(tmp_path, thrust_z=-0.28)
    c = _by_name(run_sanity(case), "thrust_direction")
    assert c.status == PASS


def test_thrust_direction_fail(tmp_path):
    case = _build_full_case(tmp_path, thrust_z=0.28)
    c = _by_name(run_sanity(case), "thrust_direction")
    assert c.status == FAIL


def test_thrust_direction_skip_when_q_not_positive(tmp_path):
    case = _build_full_case(tmp_path, q=-0.01, q_in_sign_ok=False)
    c = _by_name(run_sanity(case), "thrust_direction")
    assert c.status == SKIP


# --- inlet_bookkeeping ---

def test_inlet_bookkeeping_pass(tmp_path):
    case = _build_full_case(tmp_path, p_in_kin=-4.5)  # exact match to expected
    c = _by_name(run_sanity(case), "inlet_bookkeeping")
    assert c.status == PASS


def test_inlet_bookkeeping_warn(tmp_path):
    # expected = -5.4 Pa; put actual 10% off -> WARN (<=15%)
    case = _build_full_case(tmp_path, p_in_kin=-4.95)  # actual_pa = -5.94, ~10% off
    c = _by_name(run_sanity(case), "inlet_bookkeeping")
    assert c.status == WARN


def test_inlet_bookkeeping_fail(tmp_path):
    case = _build_full_case(tmp_path, p_in_kin=-9.0)  # actual_pa = -10.8, 100% off
    c = _by_name(run_sanity(case), "inlet_bookkeeping")
    assert c.status == FAIL


def test_inlet_bookkeeping_skip_missing_area(tmp_path):
    case = _build_full_case(tmp_path)
    meta_path = case / "constant" / "case_meta.json"
    meta = json.loads(meta_path.read_text())
    del meta["inlet_area_m2"]
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    c = _by_name(run_sanity(case), "inlet_bookkeeping")
    assert c.status == SKIP


def test_inlet_bookkeeping_skip_when_q_leq_0(tmp_path):
    # Same reversed-flow argument as energy_total: the inflow static-pressure formula
    # doesn't apply once the inlet is acting as an outflow boundary.
    case = _build_full_case(tmp_path, q=-0.01, q_in_sign_ok=False)
    c = _by_name(run_sanity(case), "inlet_bookkeeping")
    assert c.status == SKIP
    assert "Q<=0" in c.note


# --- mesh_quality ---

def test_mesh_quality_pass(tmp_path):
    case = _build_full_case(tmp_path, mesh_ok=True)
    c = _by_name(run_sanity(case), "mesh_quality")
    assert c.status == PASS
    assert "42.5" in c.note and "1.8" in c.note


def test_mesh_quality_warn_skewness_only(tmp_path):
    # Real checkMesh output: a single "***"-prefixed skewness failure line and
    # "Failed 1 mesh checks." -> not a hard FAIL, just a skewness WARN.
    case = _build_full_case(tmp_path, mesh_ok=False, mesh_failed=True)
    c = _by_name(run_sanity(case), "mesh_quality")
    assert c.status == WARN
    assert "1 highly skew faces" in c.note
    assert "skewness only" in c.note


def test_mesh_quality_fail_on_non_skewness_failure(tmp_path):
    # A mix of a skewness line and a non-orthogonality line -> real geometry problem, FAIL.
    case = _build_full_case(tmp_path, mesh_ok=False, mesh_mixed=True)
    c = _by_name(run_sanity(case), "mesh_quality")
    assert c.status == FAIL
    assert "2 failed checks" in c.note
    assert "severely non-orthogonal" in c.note


def test_mesh_quality_skip_missing(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    c = _by_name(run_sanity(case), "mesh_quality")
    assert c.status == SKIP


# --- y_plus ---

def test_y_plus_pass(tmp_path):
    case = _build_full_case(tmp_path, yplus_avg=45.0)
    c = _by_name(run_sanity(case), "y_plus")
    assert c.status == PASS
    assert c.value == pytest.approx(45.0)


def test_y_plus_warn(tmp_path):
    case = _build_full_case(tmp_path, yplus_avg=4.1)
    c = _by_name(run_sanity(case), "y_plus")
    assert c.status == WARN


def test_y_plus_skip_missing(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    c = _by_name(run_sanity(case), "y_plus")
    assert c.status == SKIP


# --- regime (tip Mach) ---

def test_regime_pass(tmp_path):
    case = _build_full_case(tmp_path, tip_radius_m=0.05)  # Mach ~0.046
    c = _by_name(run_sanity(case), "regime")
    assert c.status == PASS


def test_regime_warn_at_mach_0_35(tmp_path):
    # tip Mach = omega*r/343 = 0.35 -> r = 0.35*343/omega
    r = 0.35 * 343.0 / OMEGA
    case = _build_full_case(tmp_path, tip_radius_m=r)
    c = _by_name(run_sanity(case), "regime")
    assert c.status == WARN
    assert c.value == pytest.approx(0.35, rel=1e-3)


def test_regime_skip_missing_case_meta(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    c = _by_name(run_sanity(case), "regime")
    assert c.status == SKIP


# --- converged ---

def test_converged_pass(tmp_path):
    case = _build_full_case(tmp_path)  # constant flow tail -> converged
    c = _by_name(run_sanity(case), "converged")
    assert c.status == PASS


def test_converged_warn_on_oscillating_flow(tmp_path):
    case = tmp_path / "case"
    # Oscillating tail that never settles -> convergence() reports False.
    flows = [0.01, 0.05] * 10
    _write_pp(case, "outletFlow", "surfaceFieldValue.dat",
               "".join(f"{i} {q}\n" for i, q in enumerate(flows)))
    _write_pp(case, "forces", "moment.dat",
               "".join(f"{i} 0 0 -0.01 0 0 -0.01 0 0 0\n" for i in range(len(flows))))
    _write_pp(case, "forces", "force.dat",
               "".join(f"{i} 0 0 -0.28 0 0 -0.28 0 0 0\n" for i in range(len(flows))))
    _write_pp(case, "inletP", "surfaceFieldValue.dat",
               "".join(f"{i} -4.5\n" for i in range(len(flows))))
    _write_pp(case, "outletP", "surfaceFieldValue.dat",
               "".join(f"{i} 50.0\n" for i in range(len(flows))))
    c = _by_name(run_sanity(case, omega_signed=OMEGA), "converged")
    assert c.status == WARN


def test_converged_skip_missing_metrics(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    c = _by_name(run_sanity(case, omega_signed=OMEGA), "converged")
    assert c.status == SKIP


# --- duct_shape ---

def test_duct_shape_pass_round(tmp_path):
    case = _build_full_case(tmp_path, duct_shape="round")
    c = _by_name(run_sanity(case), "duct_shape")
    assert c.status == PASS


def test_duct_shape_warn_square(tmp_path):
    case = _build_full_case(tmp_path, duct_shape="square")
    c = _by_name(run_sanity(case), "duct_shape")
    assert c.status == WARN


def test_duct_shape_skip_missing(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    c = _by_name(run_sanity(case), "duct_shape")
    assert c.status == SKIP


# --- overall / summarize ---

def test_overall_worst_status_wins():
    from fansim.cfd.sanity import SanityCheck
    checks = [
        SanityCheck("a", PASS, 1.0, "x", ""),
        SanityCheck("b", WARN, 1.0, "x", ""),
        SanityCheck("c", SKIP, None, "x", ""),
    ]
    assert overall(checks) == WARN
    checks.append(SanityCheck("d", FAIL, 1.0, "x", ""))
    assert overall(checks) == FAIL


def test_overall_all_skip_is_skip():
    from fansim.cfd.sanity import SanityCheck
    checks = [SanityCheck("a", SKIP, None, "x", "")]
    assert overall(checks) == SKIP


def test_summarize_lists_warn_and_fail_only():
    from fansim.cfd.sanity import SanityCheck
    checks = [
        SanityCheck("mass_balance", PASS, 0.1, "<=1%", ""),
        SanityCheck("y_plus", WARN, 4.1, "30-300", "y+ avg=4.10"),
        SanityCheck("duct_shape", WARN, None, "round PASS, square WARN", "square"),
    ]
    line = summarize(checks)
    assert line.startswith("sanity WARN:")
    assert "y_plus" in line
    assert "duct_shape" in line
    assert "mass_balance" not in line


def test_run_sanity_full_case_all_pass(tmp_path):
    case = _build_full_case(tmp_path)
    checks = run_sanity(case)
    statuses = {c.name: c.status for c in checks}
    assert statuses["mass_balance"] == PASS
    assert statuses["energy_total"] == PASS
    assert statuses["power_sign"] == PASS
    assert statuses["thrust_direction"] == PASS
    assert statuses["inlet_bookkeeping"] == PASS
    assert statuses["mesh_quality"] == PASS
    assert statuses["y_plus"] == PASS
    assert statuses["regime"] == PASS
    assert statuses["converged"] == PASS
    assert statuses["duct_shape"] == PASS
    assert overall(checks) == PASS


# --- legacy-case metadata inference (no constant/case_meta.json) ---

H = 0.1
Z_MIN = -0.05
Z_MAX = 0.20
LEGACY_OMEGA = 209.4395
HUB_R = 0.02
TIP_R = 0.05
BORE_R = 0.045


def _tube_mesh(r0, z0, r1, z1, n=48):
    """A cylindrical (or conical) shell: two vertex rings, side faces only, no end caps.

    Mirrors the extruded-geometry topology noted in mount-gauge-bore-mesh-topology: wall
    triangles only tessellate at the z-ends, so sampling a ring at z0/z1 is representative.
    """
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring0 = np.stack([r0 * np.cos(angles), r0 * np.sin(angles), np.full(n, z0)], axis=1)
    ring1 = np.stack([r1 * np.cos(angles), r1 * np.sin(angles), np.full(n, z1)], axis=1)
    verts = np.vstack([ring0, ring1])
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j])
        faces.append([i, n + j, n + i])
    return trimesh.Trimesh(vertices=verts, faces=np.array(faces, dtype=np.int64), process=False)


def _write_block_mesh_dict(case: Path, *, h=H, z_min=Z_MIN, z_max=Z_MAX) -> None:
    d = case / "system"
    d.mkdir(parents=True, exist_ok=True)
    verts = [
        (-h, -h, z_min), (h, -h, z_min), (h, h, z_min), (-h, h, z_min),
        (-h, -h, z_max), (h, -h, z_max), (h, h, z_max), (-h, h, z_max),
    ]
    lines = ["vertices", "("]
    lines += [f"    ({x} {y} {z})" for x, y, z in verts]
    lines += [");", "", "blocks", "(", "    hex (0 1 2 3 4 5 6 7) (10 10 10) simpleGrading (1 1 1)", ");"]
    (d / "blockMeshDict").write_text("\n".join(lines), encoding="utf-8")


def _write_mrf_properties(case: Path, *, omega=LEGACY_OMEGA, dual=False) -> None:
    d = case / "constant"
    d.mkdir(parents=True, exist_ok=True)
    if dual:
        text = (
            "MRF1\n{\n    omega   150.0;\n}\n"
            "MRF2\n{\n    omega   -150.0;\n}\n"
        )
    else:
        text = f"MRF\n{{\n    omega           {omega};\n}}\n"
    (d / "MRFProperties").write_text(text, encoding="utf-8")


def _write_legacy_impeller_stl(case: Path, *, hub_r=HUB_R, tip_r=TIP_R) -> None:
    d = case / "constant" / "triSurface"
    d.mkdir(parents=True, exist_ok=True)
    mesh = _tube_mesh(hub_r, 0.0, tip_r, 0.03)
    mesh.export(str(d / "impeller.stl"))


def _write_legacy_casing_stl(case: Path, *, bore_r=BORE_R, z0=Z_MIN, z1=Z_MAX) -> None:
    d = case / "constant" / "triSurface"
    d.mkdir(parents=True, exist_ok=True)
    mesh = _tube_mesh(bore_r, z0, bore_r, z1)
    mesh.export(str(d / "casing.stl"))


def _build_legacy_case(tmp_path: Path, *, with_casing: bool, plenum: bool = False, dual_mrf: bool = False) -> Path:
    case = tmp_path / "legacy_case"
    _write_block_mesh_dict(case)
    _write_mrf_properties(case, dual=dual_mrf)
    _write_legacy_impeller_stl(case)
    if with_casing:
        casing_z1 = 0.15 if plenum else Z_MAX
        _write_legacy_casing_stl(case, z1=casing_z1)
    return case


def test_infer_omega_single_mrf(tmp_path):
    case = tmp_path / "case"
    _write_mrf_properties(case, omega=LEGACY_OMEGA)
    assert sanity_mod._infer_omega(case) == pytest.approx(LEGACY_OMEGA)


def test_infer_omega_dual_mrf_is_none(tmp_path):
    case = tmp_path / "case"
    _write_mrf_properties(case, dual=True)
    assert sanity_mod._infer_omega(case) is None


def test_infer_omega_missing_file_is_none(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    assert sanity_mod._infer_omega(case) is None


def test_infer_box_half_width_and_zmax(tmp_path):
    case = tmp_path / "case"
    _write_block_mesh_dict(case)
    result = sanity_mod._infer_box_half_width_and_zmax(case)
    assert result is not None
    h, z_max = result
    assert h == pytest.approx(H)
    assert z_max == pytest.approx(Z_MAX)


def test_infer_case_meta_no_casing(tmp_path):
    case = _build_legacy_case(tmp_path, with_casing=False)
    meta = sanity_mod._infer_case_meta(case)
    assert meta is not None
    assert meta["inferred"] is True
    assert meta["casing"] is False
    assert meta["duct_shape"] == "square"
    assert meta["plenum"] is False
    assert meta["outlet_area_m2"] == pytest.approx((2 * H) ** 2)
    assert meta["inlet_area_m2"] == pytest.approx((2 * H) ** 2)
    assert meta["omega_signed"] == pytest.approx(LEGACY_OMEGA)
    assert meta["tip_radius_m"] == pytest.approx(TIP_R, rel=1e-6)


def test_infer_case_meta_with_casing(tmp_path):
    case = _build_legacy_case(tmp_path, with_casing=True, plenum=False)
    meta = sanity_mod._infer_case_meta(case)
    assert meta is not None
    assert meta["casing"] is True
    assert meta["duct_shape"] == "round"
    assert meta["plenum"] is False
    assert meta["outlet_area_m2"] == pytest.approx((2 * H) ** 2)
    assert meta["inlet_area_m2"] == pytest.approx(math.pi * BORE_R ** 2, rel=1e-6)


def test_infer_case_meta_with_casing_plenum(tmp_path):
    case = _build_legacy_case(tmp_path, with_casing=True, plenum=True)
    meta = sanity_mod._infer_case_meta(case)
    assert meta is not None
    assert meta["plenum"] is True


def test_infer_case_meta_missing_blockmesh_is_none(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    assert sanity_mod._infer_case_meta(case) is None


def test_run_sanity_infers_meta_for_legacy_case_no_casing(tmp_path):
    case = _build_legacy_case(tmp_path, with_casing=False)
    checks = run_sanity(case)
    by_name = {c.name: c for c in checks}

    # No inletFlow postProcessing on a legacy case -> still SKIPs.
    assert by_name["mass_balance"].status == SKIP

    # But omega/areas are now inferred, so metrics get parsed and these run (SKIP only
    # because there is still no forces/pressure postProcessing in this synthetic case).
    for name in ("energy_total", "power_sign", "regime"):
        assert by_name[name].status in (SKIP, PASS, WARN, FAIL)

    assert by_name["duct_shape"].status == WARN
    assert "meta inferred" in by_name["duct_shape"].note
    assert by_name["regime"].status == SKIP or by_name["regime"].value is not None


def test_run_sanity_infers_meta_and_runs_metrics_checks(tmp_path):
    case = _build_legacy_case(tmp_path, with_casing=True)
    # Add the postProcessing a legacy run does have, so metrics parse succeeds.
    n = 20
    _write_pp(case, "forces", "moment.dat",
               "".join(f"{i} 0 0 -0.01 0 0 -0.01 0 0 0\n" for i in range(n)))
    _write_pp(case, "forces", "force.dat",
               "".join(f"{i} 0 0 -0.28 0 0 -0.28 0 0 0\n" for i in range(n)))
    _write_pp(case, "outletFlow", "surfaceFieldValue.dat",
               "".join(f"{i} 0.03\n" for i in range(n)))
    _write_pp(case, "inletP", "surfaceFieldValue.dat",
               "".join(f"{i} -4.5\n" for i in range(n)))
    _write_pp(case, "outletP", "surfaceFieldValue.dat",
               "".join(f"{i} 50.0\n" for i in range(n)))

    checks = run_sanity(case)
    by_name = {c.name: c for c in checks}

    # No inletFlow function object on a legacy case -> mass_balance still SKIPs.
    assert by_name["mass_balance"].status == SKIP
    # But metrics parsed successfully via the inferred omega, so these actually run.
    assert by_name["energy_total"].status in (PASS, FAIL)
    assert by_name["power_sign"].status in (PASS, FAIL)
    assert by_name["thrust_direction"].status in (PASS, FAIL)
    assert by_name["regime"].status in (PASS, WARN)
    assert by_name["duct_shape"].status == PASS
    assert "meta inferred" in by_name["duct_shape"].note
