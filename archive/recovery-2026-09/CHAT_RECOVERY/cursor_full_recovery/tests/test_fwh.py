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


def test_evaluate_noise_declares_fwh_flag():
    text = Path("scripts/evaluate_noise.py").read_text(encoding="utf-8")
    assert "--fwh" in text
    assert "★" not in text
