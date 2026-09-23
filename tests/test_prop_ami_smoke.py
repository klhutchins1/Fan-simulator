# tests/test_prop_ami_smoke.py
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from fansim.cfd import templates as T
from fansim.propeller.ami_smoke import (
    DELTA_T,
    N_REVS,
    ami_exit_code,
    apply_ami_overlay,
    assess_band,
    band_limits,
    end_time_s,
    rev_period_s,
    result_is_resumable,
    summary_from_rows,
    window_thrust_g,
)
from fansim.propeller.cfd import PropOpenAir, build_prop_case


def test_locked_time_knobs():
    period = rev_period_s(25257.0)
    assert period == 60.0 / 25257.0
    assert end_time_s(25257.0) == N_REVS * period
    assert DELTA_T == 4e-5


def test_window_uses_last_revolution_and_abs_fz():
    end = end_time_s(25257.0)
    period = rev_period_s(25257.0)
    t0 = end - period
    # column 3 is total Fz (N). 9.80665 N → 1000 g.
    rows = [
        [0.0, 0.0, 0.0, 9.80665],
        [t0 - 1e-6, 0.0, 0.0, -9.80665],
        [t0, 0.0, 0.0, 9.80665],
        [end, 0.0, 0.0, -9.80665],
    ]
    mean, count = window_thrust_g(rows, end_time=end, rpm=25257.0)
    assert count == 2
    assert mean == 1000.0


def test_window_zero_samples_is_none():
    end = end_time_s(25257.0)
    mean, count = window_thrust_g([[0.0, 0.0, 0.0, 1.0]], end_time=end, rpm=25257.0)
    assert mean is None
    assert count == 0


def test_band_edges_are_inclusive():
    lo, hi = band_limits()
    assert lo == 703.5
    assert hi == 1172.5
    assert assess_band(lo)["band_pass"] is True
    assert assess_band(hi)["band_pass"] is True
    assert assess_band(938.0)["band_pass"] is True
    assert assess_band(lo - 1e-6)["band_pass"] is False
    assert assess_band(hi + 1e-6)["band_pass"] is False
    assert assess_band(5.0)["band_pass"] is False
    assert assess_band(None)["band_pass"] is False
    assert assess_band(None)["mean_thrust_g"] is None


def test_exit_codes():
    assert ami_exit_code(assess_band(938.0)) == 0
    assert ami_exit_code(assess_band(2000.0)) == 2
    assert ami_exit_code(assess_band(5.0)) == 2
    assert ami_exit_code(assess_band(None)) == 1
    assert ami_exit_code({"mean_thrust_g": float("nan"), "band_pass": False}) == 1


def test_mrf_control_dict_unchanged():
    assert "rhoSimpleFoam" in T.PROP_CONTROL_DICT
    assert "phiMRF" in T.PROP_FV_SCHEMES


def test_apply_ami_overlay_writes_sliding_case(tmp_path: Path):
    stl = Path("validation/reference/drone_radial/obj_2_ccw.stl")
    dom = PropOpenAir(
        tip_radius=0.045,
        domain_radius=0.225,
        z_min=-0.1,
        z_max=0.2,
        mrf_z_min=-0.02,
        mrf_z_max=0.02,
        rpm=25257.0,
        omega_signed=-2644.0,
        u_freestream=1.0,
    )
    build_prop_case(tmp_path, stl, dom, n_iters=10, n_subdomains=8)
    assert (tmp_path / "constant/MRFProperties").is_file()
    assert "rhoSimpleFoam" in (tmp_path / "system/controlDict").read_text(encoding="utf-8")

    apply_ami_overlay(
        tmp_path,
        omega_signed=dom.omega_signed,
        ami_radius=1.05 * dom.tip_radius,
        ami_z_min=dom.mrf_z_min,
        ami_z_max=dom.mrf_z_max,
        end_time=end_time_s(25257.0),
        delta_t=DELTA_T,
        u_freestream=1.0,
        k=1.0e-4,
        omega_turb=10.0,
    )
    control = (tmp_path / "system/controlDict").read_text(encoding="utf-8")
    schemes = (tmp_path / "system/fvSchemes").read_text(encoding="utf-8")
    solution = (tmp_path / "system/fvSolution").read_text(encoding="utf-8")
    motion = (tmp_path / "system/dynamicMeshDict").read_text(encoding="utf-8")
    baffles = (tmp_path / "system/createBafflesDict").read_text(encoding="utf-8")
    velocity = (tmp_path / "0/U").read_text(encoding="utf-8")
    assert "rhoPimpleFoam" in control
    assert "rhoSimpleFoam" not in control
    assert "writeInterval   1" in control
    assert "backward" in schemes
    assert "steadyState" not in schemes
    assert "phiMRF" not in schemes
    assert "nOuterCorrectors 1" in solution
    assert "nCorrectors     2" in solution
    assert "nNonOrthogonalCorrectors 1" in solution
    assert "SIMPLE" not in solution
    assert "rotatingMotion" in motion
    assert "cellZone        rotor" in motion
    assert "cyclicAMI" in baffles
    assert "transform       rotational" in baffles
    assert "searchableCylinder" in baffles
    assert "movingWallVelocity" in velocity
    assert "AMI1" in velocity and "AMI2" in velocity
    assert not (tmp_path / "constant/MRFProperties").exists()
    for name in ("T", "p", "k", "omega", "nut", "alphat", "pointDisplacement"):
        text = (tmp_path / "0" / name).read_text(encoding="utf-8")
        assert "AMI1" in text and "AMI2" in text
    assert "limitTemperature" in (tmp_path / "system/fvOptions").read_text(encoding="utf-8")
    assert "hePsiThermo" in (tmp_path / "constant/thermophysicalProperties").read_text(encoding="utf-8")


def test_summary_from_rows_band_pass():
    end = end_time_s(25257.0)
    period = rev_period_s(25257.0)
    fz = 938.0 / (1000.0 / 9.80665)  # newtons for 938 g
    rows = [[end - period, 0.0, 0.0, fz], [end, 0.0, 0.0, fz]]
    summary = summary_from_rows(
        rows, stl="obj_2_ccw.stl", rpm=25257.0, base_cell=0.005,
    )
    assert summary["regime"] == "compressible-AMI"
    assert summary["solver"] == "rhoPimpleFoam"
    assert summary["thrust_g_samples"] == 2
    assert summary["mean_thrust_g"] == pytest.approx(938.0, rel=1e-6)
    assert summary["band_pass"] is True
    assert summary["delta_t"] == 4e-5
    assert "reason" not in summary
    assert ami_exit_code(summary) == 0


def test_summary_from_rows_empty_window():
    summary = summary_from_rows(
        [[0.0, 0.0, 0.0, 1.0]],
        stl="obj_2_ccw.stl",
        rpm=25257.0,
        base_cell=0.005,
        reason="mean window has zero samples",
    )
    assert summary["mean_thrust_g"] is None
    assert summary["band_pass"] is False
    assert summary["thrust_g_samples"] == 0
    assert summary["reason"] == "mean window has zero samples"
    assert ami_exit_code(summary) == 1


def test_result_is_resumable(tmp_path: Path):
    path = tmp_path / "result.json"
    assert result_is_resumable(path) is False
    path.write_text(json.dumps({"mean_thrust_g": None}), encoding="utf-8")
    assert result_is_resumable(path) is False
    path.write_text(json.dumps({"mean_thrust_g": 900.0}), encoding="utf-8")
    assert result_is_resumable(path) is True


def _load_cli():
    path = Path("scripts/run_prop_ami_smoke.py")
    spec = importlib.util.spec_from_file_location("run_prop_ami_smoke", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_cli_parser_defaults():
    mod = _load_cli()
    args = mod.build_parser().parse_args([])
    assert args.stl.name == "obj_2_ccw.stl"
    assert args.rpm == pytest.approx(25257.0)
    assert args.procs == 8
    assert args.base_cell == pytest.approx(0.005)
    assert args.force is False
    assert args.out.as_posix().endswith("runs/drone_radial_cfd/ami/obj_2")


def test_cli_missing_stl(tmp_path: Path, capsys):
    mod = _load_cli()
    code = mod.main([
        "--stl", str(tmp_path / "missing.stl"),
        "--out", str(tmp_path / "out"),
    ])
    assert code == 1
    assert "ERROR" in capsys.readouterr().err


def test_cli_runtime_error_writes_failed_result(tmp_path: Path, monkeypatch):
    mod = _load_cli()
    stl = Path("validation/reference/drone_radial/obj_2_ccw.stl")
    out = tmp_path / "out"

    def _fail(*_args, **_kwargs):
        raise RuntimeError("solver failed")

    monkeypatch.setattr(mod, "run_case", _fail)
    code = mod.main(["--stl", str(stl), "--out", str(out)])
    assert code == 1
    payload = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert payload["mean_thrust_g"] is None


def test_cli_non_runtime_error_propagates(tmp_path: Path, monkeypatch):
    mod = _load_cli()
    stl = Path("validation/reference/drone_radial/obj_2_ccw.stl")
    out = tmp_path / "out"

    def _bug(*_args, **_kwargs):
        raise ValueError("bug")

    monkeypatch.setattr(mod, "run_case", _bug)
    with pytest.raises(ValueError, match="bug"):
        mod.main(["--stl", str(stl), "--out", str(out)])


def test_cli_stamp_not_written_for_null_mean(tmp_path: Path, monkeypatch):
    mod = _load_cli()
    stamp = tmp_path / "stamp.json"
    monkeypatch.setattr(mod, "STAMP", stamp)
    mod._maybe_stamp(
        Path("validation/reference/drone_radial/obj_2_ccw.stl"),
        25257.0,
        {"mean_thrust_g": None},
    )
    assert not stamp.exists()


def test_cli_stamp_written_for_obj2_at_target_rpm(tmp_path: Path, monkeypatch):
    mod = _load_cli()
    stamp = tmp_path / "stamp.json"
    monkeypatch.setattr(mod, "STAMP", stamp)
    mod._maybe_stamp(
        Path("validation/reference/drone_radial/obj_2_ccw.stl"),
        25257.0,
        {"mean_thrust_g": 938.0, "band_pass": True},
    )
    assert stamp.is_file()
    payload = json.loads(stamp.read_text(encoding="utf-8"))
    assert payload["mean_thrust_g"] == pytest.approx(938.0)


def test_cli_stamp_not_written_for_non_target_identity(tmp_path: Path, monkeypatch):
    mod = _load_cli()
    stamp = tmp_path / "stamp.json"
    monkeypatch.setattr(mod, "STAMP", stamp)
    mod._maybe_stamp(
        Path("validation/reference/drone_radial/other.stl"),
        25257.0,
        {"mean_thrust_g": 938.0},
    )
    assert not stamp.exists()
    mod._maybe_stamp(
        Path("validation/reference/drone_radial/obj_2_ccw.stl"),
        25000.0,
        {"mean_thrust_g": 938.0},
    )
    assert not stamp.exists()


def test_cli_main_resume_skips_run_case(tmp_path: Path, monkeypatch):
    mod = _load_cli()
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps({"mean_thrust_g": 938.0, "band_pass": True}),
        encoding="utf-8",
    )

    def _must_not_run(*_args, **_kwargs):
        raise AssertionError("run_case should not be called on resumable result")

    monkeypatch.setattr(mod, "run_case", _must_not_run)
    code = mod.main(["--out", str(out)])
    assert code == 0
