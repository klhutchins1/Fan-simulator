"""Rule A: converged iff the tail mean is stable; the swing is reported, not judged."""

from __future__ import annotations

import math

import pytest

from fansim.cfd.metrics import CFD_VERSION, convergence, oscillation_pct


def _write_flow(case, values):
    d = case / "postProcessing" / "outletFlow" / "0"
    d.mkdir(parents=True, exist_ok=True)
    (d / "surfaceFieldValue.dat").write_text(
        "".join(f"{i + 1} {v}\n" for i, v in enumerate(values)), encoding="utf-8")


def test_limit_cycle_with_stable_mean_is_converged(tmp_path):
    # 8% peak-to-peak oscillation around 0.03, many periods in the tail.
    vals = [0.03 * (1 + 0.04 * math.sin(2 * math.pi * i / 10)) for i in range(400)]
    _write_flow(tmp_path, vals)
    ok, shift = convergence(tmp_path)
    assert ok and shift < 2.0
    assert oscillation_pct(tmp_path) == pytest.approx(8.0, abs=0.5)  # samples miss the exact peaks


def test_drifting_mean_is_not_converged(tmp_path):
    vals = [0.02 + 0.00004 * i for i in range(400)]  # still climbing through the tail
    _write_flow(tmp_path, vals)
    ok, shift = convergence(tmp_path)
    assert not ok and shift > 2.0


def test_too_short_history(tmp_path):
    _write_flow(tmp_path, [0.03, 0.03, 0.03])
    assert convergence(tmp_path) == (False, 999.0)


def test_cfd_version_bumped():
    assert CFD_VERSION == 7


def test_flow_trajectory_ignores_truncated_single_column_row(tmp_path):
    """A 1-column flushed line ('15') must not be read as flow=15.0 m^3/s."""
    d = tmp_path / "postProcessing" / "outletFlow" / "0"
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"{i + 1} 0.03" for i in range(20)]
    lines.insert(17, "18")  # truncated row inside the last-25% tail
    (d / "surfaceFieldValue.dat").write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, shift = convergence(tmp_path)
    assert ok and shift == pytest.approx(0.0, abs=1e-12)
    assert oscillation_pct(tmp_path) == pytest.approx(0.0, abs=1e-12)


def test_parse_fan_metrics_rejects_negative_omega_and_nonpositive_rho(tmp_path):
    """Unsigned omega_rad_s < 0 (e.g. signed MRF omega) or rho <= 0 must raise, not return P_shaft < 0."""
    from fansim.cfd.metrics import parse_fan_metrics

    def put(fo, fname, row):
        d = tmp_path / "postProcessing" / fo / "0"
        d.mkdir(parents=True, exist_ok=True)
        (d / fname).write_text(f"# header\n{row}\n", encoding="utf-8")

    put("forces", "moment.dat", "600  0 0 -0.010  0 0 -0.010  0 0 0")
    put("forces", "force.dat", "600  0 0 -0.20  0 0 -0.20  0 0 0")
    put("outletFlow", "surfaceFieldValue.dat", "600  0.025")
    put("inletP", "surfaceFieldValue.dat", "600  -2.0")
    put("outletP", "surfaceFieldValue.dat", "600  6.667")

    with pytest.raises(ValueError, match="omega_rad_s"):
        parse_fan_metrics(tmp_path, omega_rad_s=-209.44)
    with pytest.raises(ValueError, match="omega_rad_s"):
        parse_fan_metrics(tmp_path, omega_rad_s=float("nan"))
    with pytest.raises(ValueError, match="rho"):
        parse_fan_metrics(tmp_path, omega_rad_s=209.44, rho=0.0)
    with pytest.raises(ValueError, match="rho"):
        parse_fan_metrics(tmp_path, omega_rad_s=209.44, rho=-1.2)
    # Stationary rotor (omega == 0) is valid: zero shaft power, zero efficiency.
    m0 = parse_fan_metrics(tmp_path, omega_rad_s=0.0)
    assert m0.shaft_power_w == 0.0 and m0.efficiency == 0.0


# --- #88: multi-metric convergence & shut-off reference scaling ----------------------------------

def _write_full_trajectories(
    case,
    flows,
    p_in=None,
    p_out=None,
    mz=None,
    mz_rear=None,
):
    _write_flow(case, flows)

    def _put_scalar(fo, vals):
        d = case / "postProcessing" / fo / "0"
        d.mkdir(parents=True, exist_ok=True)
        (d / "surfaceFieldValue.dat").write_text(
            "".join(f"{i + 1} {v}\n" for i, v in enumerate(vals)), encoding="utf-8"
        )

    def _put_moment(fo, vals):
        d = case / "postProcessing" / fo / "0"
        d.mkdir(parents=True, exist_ok=True)
        (d / "moment.dat").write_text(
            "".join(f"{i + 1} 0 0 {v} 0 0 {v} 0 0 0\n" for i, v in enumerate(vals)),
            encoding="utf-8",
        )

    if p_in is not None:
        _put_scalar("inletP", p_in)
    if p_out is not None:
        _put_scalar("outletP", p_out)
    if mz is not None:
        _put_moment("forces", mz)
    if mz_rear is not None:
        _put_moment("forcesRear", mz_rear)


def test_velocity_driven_drifting_pressure_is_not_converged(tmp_path):
    """P1 (#88): pinned outletFlow (FIELD_U) must NOT mask drifting inletP / pressure rise."""
    n = 400
    flows = [0.025] * n
    p_in = [-10.0 - 0.05 * i for i in range(n)]  # climbing inlet suction throughout tail
    p_out = [0.0] * n
    mz = [-0.010] * n
    _write_full_trajectories(tmp_path, flows, p_in=p_in, p_out=p_out, mz=mz)
    ok, shift = convergence(tmp_path)
    assert not ok and shift > 2.0


def test_drifting_torque_is_not_converged(tmp_path):
    """P2 (#88): settled flow and pressure must NOT mask drifting rotor torque Mz."""
    n = 400
    flows = [0.025] * n
    p_in = [-4.0] * n
    p_out = [8.0] * n
    mz = [-0.008 - 0.00003 * i for i in range(n)]  # still drifting in tail
    _write_full_trajectories(tmp_path, flows, p_in=p_in, p_out=p_out, mz=mz)
    ok, shift = convergence(tmp_path)
    assert not ok and shift > 2.0


def test_cror_drifting_rear_torque_is_not_converged(tmp_path):
    """P2 (#88): CROR forcesRear/moment.dat drift is caught independently of front rotor."""
    n = 400
    _write_full_trajectories(
        tmp_path,
        flows=[0.025] * n,
        p_in=[-4.0] * n,
        p_out=[8.0] * n,
        mz=[-0.010] * n,
        mz_rear=[0.005 + 0.00003 * i for i in range(n)],
    )
    ok, shift = convergence(tmp_path)
    assert not ok and shift > 2.0


def test_multimetric_settled_limit_cycle_is_converged(tmp_path):
    """P3 (#88): settled flow, pressure rise, and torque all pass together."""
    n = 400
    flows = [0.03 * (1.0 + 0.03 * math.sin(2 * math.pi * i / 10)) for i in range(n)]
    p_in = [-4.0 * (1.0 + 0.02 * math.sin(2 * math.pi * i / 10)) for i in range(n)]
    p_out = [8.0] * n
    mz = [-0.012 * (1.0 + 0.02 * math.sin(2 * math.pi * i / 10)) for i in range(n)]
    _write_full_trajectories(tmp_path, flows, p_in=p_in, p_out=p_out, mz=mz)
    ok, shift = convergence(tmp_path)
    assert ok and shift < 2.0


def test_shutoff_near_zero_flow_does_not_blow_up(tmp_path):
    """P4 (#88): settled shut-off (Q ~ 0) must not explode shift or oscillation_pct."""
    n = 400
    # Tiny numerical jitter around Q = 0 (~0.002 CFM), settled pressure and torque
    flows = [1e-6 * math.sin(2 * math.pi * i / 8) for i in range(n)]
    p_in = [-20.0] * n
    p_out = [0.0] * n
    mz = [-0.015] * n
    _write_full_trajectories(tmp_path, flows, p_in=p_in, p_out=p_out, mz=mz)
    ok, shift = convergence(tmp_path)
    osc = oscillation_pct(tmp_path)
    assert ok and shift < 2.0
    assert math.isfinite(osc) and osc <= 2.5


def test_shutoff_real_drift_near_zero_still_fails(tmp_path):
    """P4 (#88): genuine flow drift near zero (0 -> 5e-5 m^3/s) is still flagged unconverged."""
    n = 400
    flows = [5e-5 * (i / n) for i in range(n)]
    _write_full_trajectories(tmp_path, flows, p_in=[-20.0] * n, p_out=[0.0] * n, mz=[-0.015] * n)
    ok, shift = convergence(tmp_path)
    assert not ok and shift > 2.0


def test_truncated_secondary_history_fails_convergence(tmp_path):
    """P5 (#88): a present secondary QoI with < 4 tail samples is treated as unconverged."""
    n = 400
    _write_full_trajectories(
        tmp_path,
        flows=[0.025] * n,
        p_in=[-4.0] * 3,  # truncated
        p_out=[8.0] * n,
        mz=[-0.010] * n,
    )
    assert convergence(tmp_path) == (False, 999.0)


@pytest.mark.parametrize("kwargs", [{"tail_frac": 0.0}, {"tail_frac": 1.5}, {"tol_pct": 0.0}, {"tol_pct": -1.0}])
def test_convergence_rejects_invalid_params(tmp_path, kwargs):
    _write_flow(tmp_path, [0.03] * 40)
    with pytest.raises(ValueError):
        convergence(tmp_path, **kwargs)


