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
