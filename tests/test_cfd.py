# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""CFD tests: domain sizing, metric parsing (fast fixtures), and a docker-gated case build."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.cfd.domain import rig_for_impeller
from fansim.cfd.metrics import parse_fan_metrics
from fansim.geometry import BladeParams


def test_rig_dimensions_and_operating_point():
    import math

    rig = rig_for_impeller(BladeParams(), tip_gap_mm=1.0, inlet_velocity=2.0)
    assert rig.duct_radius == pytest.approx((56.5 + 1.0) / 1000.0)
    assert rig.omega_rad_s == pytest.approx(2000.0 * 2 * 3.141592653589793 / 60.0)
    assert rig.domain_z_max > rig.impeller_z_max > rig.impeller_z_min > rig.domain_z_min
    assert (rig.impeller_z_min - rig.domain_z_min) == pytest.approx(rig.inlet_length)
    assert (rig.domain_z_max - rig.impeller_z_max) == pytest.approx(rig.outlet_length)
    assert rig.mrf_z_min < rig.impeller_z_min and rig.mrf_z_max > rig.impeller_z_max
    assert rig.u_axial > 0.0
    assert rig.spin == -1
    assert rig.hub_radius > 0.0
    # CFM from velocity uses annulus (duct − hub), not the full disk.
    annulus = math.pi * (rig.duct_radius**2 - rig.hub_radius**2)
    assert rig.flow_area == pytest.approx(annulus)
    assert rig.flow_area < rig.frontal_area
    assert rig.inlet_flow_cfm > 0


def _write_pp(case: Path, fo: str, filename: str, rows: str) -> None:
    d = case / "postProcessing" / fo / "0"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text("# header\n" + rows, encoding="utf-8")


def test_parse_fan_metrics(tmp_path):
    case = tmp_path / "case"
    # time  total(x y z)  pressure(x y z)  viscous(x y z)
    _write_pp(case, "forces", "moment.dat",
              "600  1e-5 -2e-5 -0.010  1e-5 -2e-5 -0.0099  0 0 -1e-4\n")
    _write_pp(case, "forces", "force.dat",
              "600  -0.003 -0.0002 0.28  -0.003 -0.0003 0.281  0 0 -2e-4\n")
    _write_pp(case, "outletFlow", "surfaceFieldValue.dat", "600  0.02645\n")
    _write_pp(case, "inletP", "surfaceFieldValue.dat", "600  39.7\n")
    _write_pp(case, "outletP", "surfaceFieldValue.dat", "600  0.0\n")

    m = parse_fan_metrics(case, omega_rad_s=209.44)
    assert m.cfm == pytest.approx(0.02645 * 2118.882, rel=1e-6)
    assert m.torque_nm == pytest.approx(0.010, abs=1e-6)
    assert m.shaft_power_w == pytest.approx(0.010 * 209.44, rel=1e-3)
    # Fixed-velocity inlet over-driving the fan -> negative static rise at this point.
    assert m.static_pressure_rise_pa == pytest.approx((0.0 - 39.7) * 1.2, rel=1e-6)
    assert m.thrust_n == pytest.approx(0.28, abs=1e-6)


def test_kinematic_pressure_contract_once_times_rho():
    """FO ``inletP``/``outletP`` are kinematic p; parse must ×ρ exactly once (§12.11)."""
    from fansim.cfd import templates
    from fansim.cfd.metrics import RHO_AIR
    from fansim.cfd.openfoam_case import RHO_AIR as CASE_RHO

    assert RHO_AIR == CASE_RHO == 1.2
    blob = templates.CONTROL_DICT
    assert "inletP" in blob and "outletP" in blob
    # Both FOs average field ``p`` (incompressible OF = kinematic m²/s²).
    assert blob.count("fields          (p);") >= 2
    # Guard against accidental double-conversion fields.
    assert "pStatic" not in blob and "p_rgh" not in blob.split("functions")[-1]


@pytest.mark.docker
def test_case_build_files(tmp_path):
    """Case assembly writes a valid directory structure (no meshing/solving)."""
    from fansim.geometry import build_impeller, export_stl
    from fansim.cfd.openfoam_case import build_case, MeshResolution

    params = BladeParams()
    stl = export_stl(build_impeller(params), tmp_path / "imp.stl")
    rig = rig_for_impeller(params)
    case = build_case(tmp_path / "case", stl, rig, mesh=MeshResolution(), n_iters=10)
    for f in ["system/blockMeshDict", "system/snappyHexMeshDict", "system/controlDict",
              "constant/MRFProperties", "constant/triSurface/impeller.stl",
              "0/U", "0/p", "0/k", "0/omega", "0/nut"]:
        assert (case / f).exists(), f"missing {f}"
