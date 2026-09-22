# tests/test_prop_cfd_fixture.py
from __future__ import annotations

from pathlib import Path

import pytest


def _write_force_dat(case_dir: Path, zs: list[float]) -> None:
    pp = case_dir / "postProcessing" / "forces" / "0"
    pp.mkdir(parents=True)
    lines = ["# Time total(x y z) pressure(x y z) viscous(x y z)\n"]
    for i, z in enumerate(zs):
        # total z = z; other components 0
        lines.append(
            f"{float(i)} (0 0 {z}) (0 0 0) (0 0 0)\n"
        )
    (pp / "force.dat").write_text("".join(lines), encoding="utf-8")


def test_force_z_tail_drift_pct_stable(tmp_path: Path):
    from fansim.propeller.cfd_fixture import force_z_tail_drift_pct

    # 20 samples ~100 ± 1 → drift well under 10%
    zs = [100.0 + (0.5 if i % 2 else -0.5) for i in range(20)]
    _write_force_dat(tmp_path, zs)
    drift = force_z_tail_drift_pct(tmp_path)
    assert drift < 5.0


def test_force_z_tail_drift_pct_unstable(tmp_path: Path):
    from fansim.propeller.cfd_fixture import force_z_tail_drift_pct

    zs = [10.0 + 50.0 * (i / 19.0) for i in range(20)]  # large ramp
    _write_force_dat(tmp_path, zs)
    drift = force_z_tail_drift_pct(tmp_path)
    assert drift >= 10.0


def test_prop_cfd_smoke_gate_pass_without_case():
    from fansim.propeller.cfd_fixture import prop_cfd_smoke_gate

    result = {
        "thrust_n": 1.0,
        "thrust_g": 100.0,
        "torque_nm": 0.05,
        "shaft_power_w": 200.0,
    }
    ok, reasons = prop_cfd_smoke_gate(result, case_dir=None)
    assert ok and reasons == []


def test_prop_cfd_smoke_gate_fails_low_thrust():
    from fansim.propeller.cfd_fixture import prop_cfd_smoke_gate

    result = {
        "thrust_n": 0.01,
        "thrust_g": 1.0,
        "torque_nm": 0.001,
        "shaft_power_w": 1.0,
    }
    ok, reasons = prop_cfd_smoke_gate(result, case_dir=None)
    assert not ok
    assert any("thrust" in r.lower() for r in reasons)


def test_prop_cfd_smoke_gate_fails_nonfinite():
    from fansim.propeller.cfd_fixture import prop_cfd_smoke_gate

    result = {
        "thrust_n": float("nan"),
        "thrust_g": float("nan"),
        "torque_nm": 0.05,
        "shaft_power_w": 200.0,
    }
    ok, reasons = prop_cfd_smoke_gate(result, case_dir=None)
    assert not ok


def test_build_and_write_prop_cfd_fixture(tmp_path: Path):
    import json

    from fansim.propeller.cfd_fixture import (
        REQUIRED_FIXTURE_KEYS,
        build_prop_cfd_fixture,
        write_prop_cfd_fixture,
    )

    result = {
        "thrust_n": 1.23,
        "thrust_g": 125.4,
        "torque_nm": 0.04,
        "shaft_power_w": 150.0,
        "rpm": 41000.0,
        "tip_mach": 0.38,
        "tip_radius_mm": 30.089,
        "solver": "rhoSimpleFoam",
        "domain": "open_air",
        "regime": "compressible-MRF",
    }
    fixture = build_prop_cfd_fixture(
        result=result,
        fixture_id="obj_1_ccw_impeller_smoke",
        stl="validation/reference/drone_radial/obj_1_ccw_impeller.stl",
        spin=-1,
        mesh={"base_cell_m": 0.005, "iters": 400, "procs": 8},
        force_tail_drift_pct=2.5,
        date="2026-09-21",
    )
    assert REQUIRED_FIXTURE_KEYS <= set(fixture.keys())
    assert fixture["solver"] == "rhoSimpleFoam"
    assert fixture["domain"] == "open_air"
    assert fixture["regime"] == "compressible-MRF"
    assert fixture["metrics"]["thrust_g"] == pytest.approx(125.4)
    assert fixture["force_tail_drift_pct"] == pytest.approx(2.5)

    out = write_prop_cfd_fixture(fixture, tmp_path / "cfd" / "obj_1.json")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["id"] == "obj_1_ccw_impeller_smoke"
    assert loaded["openfoam_image"] == "opencfd/openfoam-default:2406"


def test_freeze_cli_parser_has_required_flags():
    import importlib.util
    from pathlib import Path

    path = Path("scripts/freeze_prop_cfd_fixture.py")
    spec = importlib.util.spec_from_file_location("freeze_prop_cfd_fixture", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    ap = mod.build_parser()
    names = {a.dest for a in ap._actions}
    for need in ("result", "out", "id", "stl", "require_gate", "allow_no_case"):
        assert need in names


def test_freeze_cli_declares_drift_tol():
    import importlib.util
    from pathlib import Path

    path = Path("scripts/freeze_prop_cfd_fixture.py")
    spec = importlib.util.spec_from_file_location("freeze_prop_cfd_fixture", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    ap = mod.build_parser()
    args = ap.parse_args([
        "--result", "r.json", "--out", "o.json", "--id", "x", "--stl", "s.stl",
        "--drift-tol", "10",
    ])
    assert args.drift_tol == pytest.approx(10.0)


def test_committed_smoke_fixtures_if_present():
    import json
    import math
    from pathlib import Path

    from fansim.propeller.cfd_fixture import REQUIRED_FIXTURE_KEYS

    cfd_dir = Path("validation/reference/drone_radial/cfd")
    paths = sorted(cfd_dir.glob("*_smoke.json")) if cfd_dir.is_dir() else []
    if not paths:
        pytest.skip("no committed smoke fixtures yet")
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert REQUIRED_FIXTURE_KEYS <= set(data.keys())
        assert data["solver"] == "rhoSimpleFoam"
        assert data["domain"] == "open_air"
        assert data["regime"] == "compressible-MRF"
        for k, v in data["metrics"].items():
            assert math.isfinite(float(v)), f"{path.name} metrics.{k}"
