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
    assert CFD_VERSION == 6


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

