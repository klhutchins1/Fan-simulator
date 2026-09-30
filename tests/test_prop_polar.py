"""Prop forward-flight polar (BEMT + CFD helpers) — unit tests, no Docker."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from fansim.prop_spec import get_prop_spec
from fansim.propeller.geometry import prop_blade_params
from fansim.propeller.polar import (
    advance_ratio,
    cfd_bc_u,
    nondim,
    parse_float_list,
    resolve_sweep,
    run_bemt_polar,
    v_inf_from_j,
    write_polar_artifacts,
)


def test_advance_ratio_and_inverse():
    rpm, d = 21000.0, 0.127
    j = advance_ratio(15.0, rpm, d)
    assert j == pytest.approx(15.0 / ((rpm / 60.0) * d))
    assert v_inf_from_j(j, rpm, d) == pytest.approx(15.0)


def test_nondim_hover_eta_null():
    nd = nondim(2.0, 100.0, rpm=21000.0, diameter_m=0.127, v_inf=0.0)
    assert nd["J"] == pytest.approx(0.0)
    assert nd["eta"] is None
    assert nd["CT"] > 0.0
    assert nd["CP"] > 0.0


def test_nondim_forward_eta_positive():
    rpm, d, v = 21000.0, 0.127, 15.0
    nd = nondim(1.5, 80.0, rpm=rpm, diameter_m=d, v_inf=v)
    j = advance_ratio(v, rpm, d)
    assert nd["eta"] == pytest.approx(j * nd["CT"] / (2.0 * math.pi * nd["CP"]))


def test_resolve_sweep_merges_v_and_j():
    rpm, d = 21000.0, 0.127
    vs = resolve_sweep(v_inf=[10.0], j=[0.2], rpm=rpm, diameter_m=d, include_hover=True)
    assert vs[0] == pytest.approx(0.0)
    assert 10.0 in vs
    assert any(abs(v - v_inf_from_j(0.2, rpm, d)) < 1e-9 for v in vs)


def test_resolve_sweep_default_grid():
    vs = resolve_sweep(rpm=21000.0, diameter_m=0.127)
    assert vs == [0.0, 5.0, 10.0, 15.0, 20.0]


def test_parse_float_list():
    assert parse_float_list("0, 5;10") == [0.0, 5.0, 10.0]
    assert parse_float_list(None) is None


def test_cfd_bc_u_hover_eps():
    assert cfd_bc_u(0.0) == pytest.approx(1.0)
    assert cfd_bc_u(10.0) == pytest.approx(10.0)


def test_bemt_polar_runs_and_writes(tmp_path):
    spec = get_prop_spec("fpv_5inch")
    rpm = 0.7 * spec.rpm_max
    d = spec.diameter_mm / 1000.0
    blade = prop_blade_params(spec)
    points = run_bemt_polar(blade, rpm, [0.0, 15.0], diameter_m=d)
    assert len(points) == 2
    assert points[0].source == "bemt"
    assert points[0].J == pytest.approx(0.0)
    assert points[1].eta is not None
    csv_path, json_path = write_polar_artifacts(tmp_path, points, meta={"spec": "fpv_5inch"})
    assert csv_path.is_file() and json_path.is_file()
    text = csv_path.read_text(encoding="utf-8")
    assert "v_inf" in text and "CT" in text


def test_set_prop_freestream_rewrites_u(tmp_path):
    from fansim.cfd.openfoam_case import MeshResolution
    from fansim.geometry import watertight_report
    from fansim.propeller.cfd import build_prop_case, prop_open_air, set_prop_freestream
    from fansim.propeller.geometry import build_prop

    spec = get_prop_spec("fpv_5inch")
    stl = tmp_path / "prop.stl"
    build_prop(spec, stl)
    rep = watertight_report(stl)
    (_, _, z0), (_, _, z1) = rep.bounds_mm
    R = spec.diameter_mm / 2000.0
    dom = prop_open_air(R, z0 / 1000.0, z1 / 1000.0, rpm=15000.0, u_eps=1.0)
    case = tmp_path / "case"
    build_prop_case(case, stl, dom, mesh=MeshResolution(base_cell=0.02), n_iters=5, n_subdomains=1)
    set_prop_freestream(case, 12.5, tip_radius_m=R)
    u_text = (case / "0/U").read_text(encoding="utf-8")
    assert "12.5" in u_text


def test_purge_prop_time_dirs(tmp_path):
    from fansim.propeller.cfd import purge_prop_time_dirs

    (tmp_path / "0").mkdir()
    (tmp_path / "100").mkdir()
    (tmp_path / "constant").mkdir()
    (tmp_path / "postProcessing").mkdir()
    purge_prop_time_dirs(tmp_path)
    assert (tmp_path / "0").is_dir()
    assert (tmp_path / "constant").is_dir()
    assert not (tmp_path / "100").exists()
    assert not (tmp_path / "postProcessing").exists()


def test_run_cfd_polar_applies_direction_suspect_backstop():
    """§19.11: polar results get the same INCONCLUSIVE+wrong-sign flag as evaluate_prop_cfd."""
    from fansim.propeller.polar import finalize_cfd_polar_result

    out = finalize_cfd_polar_result({
        "direction_crosscheck": {"verdict": "INCONCLUSIVE"},
        "points": [
            {"thrust_sign_ok": True, "v_inf": 0.0},
            {"thrust_sign_ok": False, "v_inf": 10.0},
        ],
    })
    assert out["thrust_sign_ok"] is False
    assert out["direction_suspect"] is True
    assert "direction_warning" in out

    ok = finalize_cfd_polar_result({
        "direction_crosscheck": {"verdict": "INCONCLUSIVE"},
        "points": [{"thrust_sign_ok": True}],
    })
    assert ok["thrust_sign_ok"] is True
    assert "direction_suspect" not in ok


def test_run_cfd_polar_invalid_direction_raises(tmp_path):
    from fansim.propeller.polar import run_cfd_polar

    spec = get_prop_spec("fpv_5inch")
    with pytest.raises(ValueError, match="direction"):
        run_cfd_polar(spec, tmp_path, [0.0], direction="nope")


def test_polar_point_carries_thrust_sign_fields():
    from fansim.propeller.polar import _point_from_forces

    p_ok = _point_from_forces(
        v_inf=0.0, rpm=20000.0, diameter_m=0.127, thrust_n=5.0, torque_nm=0.1, power_w=200.0,
        source="cfd", thrust_sign_ok=True, thrust_sign_error=None,
    )
    assert p_ok.thrust_sign_ok is True and p_ok.thrust_sign_error is None

    p_bad = _point_from_forces(
        v_inf=0.0, rpm=20000.0, diameter_m=0.127, thrust_n=-5.0, torque_nm=0.1, power_w=200.0,
        source="cfd", thrust_sign_ok=False, thrust_sign_error="Fz=+5 N pushes the wrong way",
    )
    assert p_bad.thrust_sign_ok is False
    assert "wrong way" in p_bad.thrust_sign_error

    # BEMT points never claim a sign verdict -- there's no raw solver Fz behind them.
    p_bemt = _point_from_forces(
        v_inf=0.0, rpm=20000.0, diameter_m=0.127, thrust_n=5.0, torque_nm=0.1, power_w=200.0,
        source="bemt",
    )
    assert p_bemt.thrust_sign_ok is None and p_bemt.thrust_sign_error is None


def test_write_polar_artifacts_includes_thrust_sign_columns(tmp_path):
    from fansim.propeller.polar import _point_from_forces, write_polar_artifacts

    p = _point_from_forces(
        v_inf=0.0, rpm=20000.0, diameter_m=0.127, thrust_n=5.0, torque_nm=0.1, power_w=200.0,
        source="cfd", thrust_sign_ok=False, thrust_sign_error="wrong direction",
    )
    csv_path, json_path = write_polar_artifacts(tmp_path, [p])
    text = csv_path.read_text(encoding="utf-8")
    assert "thrust_sign_ok" in text and "thrust_sign_error" in text
    assert "wrong direction" in text


def test_cli_scripts_declare_flags():
    bemt = Path("scripts/evaluate_prop_polar.py").read_text(encoding="utf-8")
    cfd = Path("scripts/evaluate_prop_cfd_polar.py").read_text(encoding="utf-8")
    for text in (bemt, cfd):
        assert "--v-inf" in text
        assert "--j" in text
        assert "--spec" in text
    assert "--dry-run" in cfd
    assert "--bemt-floor" in cfd
