"""Tests for compact FW-H loading (fansim.acoustics.fwh). Synthetic signals only; no GPU."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from fansim.acoustics.farfield import (
    blade_pass_frequency,
    dba_from_pressure,
    tone_level_db,
)
from fansim.acoustics.fwh import (
    loading_pressure_compact,
    loading_pressure_panels,
    noise_from_compact_force,
)


def _bpf_force(amp: float = 0.01, n_blades: int = 7, rpm: float = 2000.0, t_end: float = 0.4):
    bpf = blade_pass_frequency(n_blades, rpm)
    fs = 20000.0
    t = np.arange(0, t_end, 1.0 / fs)
    Fz = amp * np.sin(2.0 * np.pi * bpf * t)
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])
    return t, F, 1.0 / fs, bpf


def test_compact_one_over_r_drops_six_db():
    _t, F, dt, _bpf = _bpf_force()
    p1 = loading_pressure_compact(F, dt, r_obs=1.0)
    p2 = loading_pressure_compact(F, dt, r_obs=2.0)
    d1 = dba_from_pressure(p1, dt, cutoff_hz=2500.0)
    d2 = dba_from_pressure(p2, dt, cutoff_hz=2500.0)
    assert d1 - d2 == pytest.approx(6.0, abs=0.3)


def test_farassat_1a_unit_force_amplitude():
    """p' = (r̂ · Ḟ) / (4π c r) for a sinusoidal Fz (NASA TM-2007-214853 M=0)."""
    from fansim.acoustics.farfield import C0_AIR

    fs = 20000.0
    f0 = 200.0
    t = np.arange(0, 0.2, 1.0 / fs)
    dt = 1.0 / fs
    amp = 0.02
    Fz = amp * np.sin(2.0 * np.pi * f0 * t)
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])
    r_obs = 1.5
    p = loading_pressure_compact(F, dt, r_hat=(0.0, 0.0, 1.0), r_obs=r_obs, c0=C0_AIR)
    # Ḟ peak ≈ amp * 2π f0; peak |p| ≈ that / (4π c r)
    expect_peak = (amp * 2.0 * math.pi * f0) / (4.0 * math.pi * C0_AIR * r_obs)
    assert float(np.max(np.abs(p))) == pytest.approx(expect_peak, rel=0.05)


def test_origin_panel_matches_compact():
    t, F, dt, _bpf = _bpf_force()
    p_c = loading_pressure_compact(F, dt, r_hat=(0.0, 0.0, 1.0), r_obs=1.0)
    panels = [{"r0": (0.0, 0.0, 0.0), "area": 1.0, "n_hat": (0.0, 0.0, 1.0), "f": F}]
    p_p = loading_pressure_panels(t, panels, x_obs=(0.0, 0.0, 1.0))
    rms = float(np.sqrt(np.mean(p_c * p_c)))
    err = float(np.sqrt(np.mean((p_c - p_p) ** 2)))
    assert rms > 0.0
    assert err / rms < 1e-5


def test_two_offset_panels_on_axis_are_finite():
    t, F, _dt, _bpf = _bpf_force()
    panels = [
        {"r0": (0.0, 0.0, 0.05), "area": 1.0, "n_hat": (0.0, 0.0, 1.0), "f": F},
        {"r0": (0.0, 0.0, -0.05), "area": 1.0, "n_hat": (0.0, 0.0, 1.0), "f": F},
    ]
    p = loading_pressure_panels(t, panels, x_obs=(0.0, 0.0, 1.0))
    assert np.all(np.isfinite(p))
    assert float(np.max(np.abs(p))) > 0.0


def test_noise_from_compact_force_detects_bpf_tone():
    n_blades, rpm = 7, 2000.0
    t, F, dt, bpf = _bpf_force(n_blades=n_blades, rpm=rpm)
    Fz = F[:, 2]
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), -0.05 + Fz])
    m = noise_from_compact_force(t, F, cutoff_hz=2500.0, n_blades=n_blades, rpm=rpm)
    assert m["analogy"] == "fwh_compact"
    assert m["thrust_n"] == pytest.approx(-0.05, abs=2e-3)
    assert math.isfinite(m["noise_dba_band"])
    p = loading_pressure_compact(F - F.mean(axis=0), dt)
    off = tone_level_db(p, dt, bpf * 3.7)
    assert m["bpf_tone_db"] > off


def test_noise_from_compact_force_does_not_round_internally():
    """#126: physics helpers return full float precision (rounding belongs in display)."""
    n_blades, rpm = 7, 2000.0
    t, F, _dt, bpf = _bpf_force(n_blades=n_blades, rpm=rpm)
    mean_fz = -1.0 / 30.0  # -0.033333... would lose precision under round(..., 4)
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), mean_fz + F[:, 2]])
    m = noise_from_compact_force(t, F, cutoff_hz=2500.0, n_blades=n_blades, rpm=rpm)
    dt_med = float(np.median(np.diff(t)))
    p = loading_pressure_compact(F - F.mean(axis=0), dt_med)
    assert m["thrust_n"] == pytest.approx(float(F[:, 2].mean()), abs=1e-12)
    assert m["noise_dba_band"] == pytest.approx(dba_from_pressure(p, dt_med, 2500.0), abs=1e-12)
    assert m["noise_dba_full"] == pytest.approx(dba_from_pressure(p, dt_med, None), abs=1e-12)
    assert m["bpf_tone_db"] == pytest.approx(tone_level_db(p, dt_med, bpf), abs=1e-12)



def test_evaluate_noise_declares_fwh_flag():
    text = Path("scripts/evaluate_noise.py").read_text(encoding="utf-8")
    assert "--fwh" in text
    assert "★" not in text


def test_nearfield_loading_matches_exact_stationary_curle():
    """#124: include_nearfield adds (r_hat · F)/(4π r^2), ~+3.7 dB at 233 Hz & r=0.2 m."""
    from fansim.acoustics.farfield import C0_AIR

    fs = 40000.0
    f0 = 233.33333333333334
    w = 2.0 * math.pi * f0
    t = np.arange(0.0, 0.2, 1.0 / fs)
    dt = 1.0 / fs
    amp = 0.05
    F = np.zeros((len(t), 3))
    F[:, 2] = amp * np.cos(w * t)
    r_obs = 0.2
    kr = w * r_obs / C0_AIR

    p_far = loading_pressure_compact(F, dt, r_obs=r_obs, c0=C0_AIR, include_nearfield=False)
    p_full = loading_pressure_compact(F, dt, r_obs=r_obs, c0=C0_AIR, include_nearfield=True)
    p_pan = loading_pressure_panels(
        t,
        [{"r0": (0.0, 0.0, 0.0), "area": 1.0, "n_hat": (0.0, 0.0, 1.0), "f": F}],
        x_obs=(0.0, 0.0, r_obs),
        c0=C0_AIR,
        include_nearfield=True,
    )

    m = t > r_obs / C0_AIR + 2.0 / f0
    tr = t[m] - r_obs / C0_AIR
    exact = (
        -amp * w * np.sin(w * tr) / (4.0 * math.pi * C0_AIR * r_obs)
        + amp * np.cos(w * tr) / (4.0 * math.pi * r_obs * r_obs)
    )
    peak_exact = (amp / (4.0 * math.pi * r_obs * r_obs)) * math.hypot(1.0, kr)
    assert float(np.max(np.abs(p_full[m] - exact))) <= 0.005 * peak_exact
    assert float(np.max(np.abs(p_pan[m] - exact))) <= 0.005 * peak_exact
    # Near-field boost at kr = 0.855 is 10*log10(1 + 1/kr^2) ≈ +3.74 dB
    boost_db = 20.0 * math.log10(
        float(np.sqrt(np.mean(p_full[m] ** 2))) / float(np.sqrt(np.mean(p_far[m] ** 2)))
    )
    assert boost_db == pytest.approx(10.0 * math.log10(1.0 + 1.0 / (kr * kr)), abs=0.05)


def test_permeable_monopole_mass_flux_matches_analytic():
    """#124: stationary permeable FW-H monopole term Q_dot_n(t_ret) / (4π r)."""
    from fansim.acoustics.farfield import C0_AIR

    fs = 40000.0
    f0 = 250.0
    w = 2.0 * math.pi * f0
    t = np.arange(0.0, 0.15, 1.0 / fs)
    q0 = 1e-3  # kg/s
    q_n = q0 * np.cos(w * t)
    r0 = (0.05, -0.03, 0.02)
    x_obs = (0.0, 0.0, 0.8)
    r = float(np.linalg.norm(np.asarray(x_obs) - np.asarray(r0)))
    panel = {
        "r0": r0,
        "area": 0.01,
        "n_hat": (0.0, 0.0, 1.0),
        "f": np.zeros((len(t), 3)),
        "q_n": q_n,
    }
    p = loading_pressure_panels(t, [panel], x_obs=x_obs, c0=C0_AIR)
    m = t > r / C0_AIR + 2.0 / f0
    tr = t[m] - r / C0_AIR
    exact = -q0 * w * np.sin(w * tr) / (4.0 * math.pi * r)
    peak = q0 * w / (4.0 * math.pi * r)
    assert float(np.max(np.abs(p[m] - exact))) <= 0.005 * peak
    with pytest.raises(ValueError, match="q_n"):
        loading_pressure_panels(t, [{**panel, "q_n": q_n[:-3]}], x_obs=x_obs, c0=C0_AIR)


def test_retarded_delay_exceeding_window_raises_instead_of_silent_zero():
    """#124: window duration <= r/c0 must raise ValueError instead of returning silent zeros."""
    dt = 1.0 / 50000.0
    n = 50  # 0.98 ms < 1.0 m / 343 m/s (~2.92 ms)
    t = np.arange(n, dtype=float) * dt
    F = np.zeros((n, 3))
    F[:, 2] = 0.01 * np.sin(2.0 * math.pi * 500.0 * t)
    with pytest.raises(ValueError, match="window duration"):
        loading_pressure_compact(F, dt, r_obs=1.0)
    with pytest.raises(ValueError, match="window duration"):
        loading_pressure_panels(
            t,
            [{"r0": (0.0, 0.0, 0.0), "area": 1.0, "n_hat": (0.0, 0.0, 1.0), "f": F}],
            x_obs=(0.0, 0.0, 1.0),
        )


def test_trim_retarded_removes_step_transient():
    """#124: trim_retarded=True slices to valid t >= t0 + max_delay with no leading zero step."""
    from fansim.acoustics.farfield import C0_AIR

    t, F, dt, _bpf = _bpf_force(t_end=0.1)
    r_obs = 1.0
    p_full = loading_pressure_compact(F, dt, r_obs=r_obs, c0=C0_AIR, trim_retarded=False)
    p_trim = loading_pressure_compact(F, dt, r_obs=r_obs, c0=C0_AIR, trim_retarded=True)
    delay_samples = math.ceil((r_obs / C0_AIR) / dt)
    assert len(p_trim) == len(p_full) - delay_samples
    assert np.allclose(p_trim, p_full[delay_samples:], atol=1e-15)
    # First sample of trimmed signal is already non-zero (sin'(0) != 0)
    assert abs(p_trim[0]) > 0.0
    panels = [
        {"r0": (0.0, 0.0, 0.05), "area": 0.01, "n_hat": (0.0, 0.0, 1.0), "f": F},
        {"r0": (0.0, 0.0, -0.05), "area": 0.01, "n_hat": (0.0, 0.0, -1.0), "f": F},
    ]
    p_pan_full = loading_pressure_panels(t, panels, x_obs=(0.0, 0.0, 1.0), trim_retarded=False)
    p_pan_trim = loading_pressure_panels(t, panels, x_obs=(0.0, 0.0, 1.0), trim_retarded=True)
    max_delay = 1.05 / C0_AIR
    valid = t >= t[0] + max_delay
    assert np.allclose(p_pan_trim, p_pan_full[valid], atol=1e-15)
    m = noise_from_compact_force(t, F, r_obs=1.0, include_nearfield=True, trim_retarded=True)
    assert m["samples"] == len(p_trim)
    assert math.isfinite(m["noise_dba_band"])
