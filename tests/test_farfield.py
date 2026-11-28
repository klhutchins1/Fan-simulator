"""Tests for the LBM far-field noise reduction (fansim.acoustics.farfield). Synthetic signals only."""

import math

import numpy as np
import pytest

from fansim.acoustics.farfield import (
    a_weighting_db,
    blade_pass_frequency,
    dba_from_pressure,
    dipole_pressure,
    noise_from_cv_force,
    peak_tone_over_harmonics,
    tone_level_db,
)


def test_a_weighting_reference_points():
    # A-weighting is ~0 dB at 1 kHz by construction, negative in the bass, and defined at 20 Hz.
    assert a_weighting_db(1000.0) == pytest.approx(0.0, abs=0.2)
    assert a_weighting_db(100.0) < -15.0     # strong bass attenuation
    assert a_weighting_db(20.0) < a_weighting_db(200.0)


def test_blade_pass_frequency():
    assert blade_pass_frequency(7, 2000.0) == pytest.approx(233.333, abs=1e-2)


def test_dipole_one_over_r_drops_six_db():
    fs = 20000.0
    f0 = 200.0
    t = np.arange(0, 0.4, 1.0 / fs)
    dt = 1.0 / fs
    Fz = 0.01 * np.sin(2.0 * np.pi * f0 * t)
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])
    Fp = F - F.mean(axis=0)
    p1 = dipole_pressure(Fp, dt, r_obs=1.0)
    p2 = dipole_pressure(Fp, dt, r_obs=2.0)
    d1 = dba_from_pressure(p1, dt, cutoff_hz=2500.0)
    d2 = dba_from_pressure(p2, dt, cutoff_hz=2500.0)
    assert d1 - d2 == pytest.approx(6.0, abs=0.3)


def test_noise_from_cv_force_detects_bpf_tone_and_thrust():
    # synthetic force: steady axial thrust + a fluctuation at the blade-pass frequency
    n_blades, rpm = 7, 2000.0
    bpf = blade_pass_frequency(n_blades, rpm)
    fs = 20000.0
    t = np.arange(0, 0.4, 1.0 / fs)
    steady_thrust = 0.05
    Fz = steady_thrust + 0.01 * np.sin(2 * np.pi * bpf * t)
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])
    # feed as (P=0, Fs=+F) so force_from_cv returns F_{fan->fluid} = +(0 + Fs) = F (#124)
    P = np.zeros((len(t), 3))
    m = noise_from_cv_force(t, P, F, cutoff_hz=2500.0, n_blades=n_blades, rpm=rpm)
    assert m["thrust_n"] == pytest.approx(steady_thrust, abs=2e-3)
    assert math.isfinite(m["noise_dba_band"])
    # the BPF tone should sit clearly above a distant off-tone band
    off = tone_level_db(np.gradient(Fz - Fz.mean(), 1.0 / fs), 1.0 / fs, bpf * 3.7)
    on = m["bpf_tone_db"]
    assert on > off


def test_noise_scales_with_fluctuation_amplitude():
    # louder input (bigger force fluctuation) -> higher dB(A), same everything else
    bpf = blade_pass_frequency()
    fs = 20000.0
    t = np.arange(0, 0.3, 1.0 / fs)
    P = np.zeros((len(t), 3))

    def band(amp):
        Fz = amp * np.sin(2 * np.pi * bpf * t)
        F = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])
        return noise_from_cv_force(t, P, F)["noise_dba_band"]

    assert band(0.02) > band(0.005)


def test_noise_from_cv_force_does_not_round_internally():
    # Issue #126: physics helper returns full float precision (rounding belongs in UI/presentation).
    n_blades, rpm = 7, 2000.0
    bpf = blade_pass_frequency(n_blades, rpm)
    fs = 20000.0
    t = np.arange(0, 0.4, 1.0 / fs)
    steady_thrust = 0.051234567
    Fz = steady_thrust + 0.013579 * np.sin(2.0 * np.pi * bpf * t)
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])
    P = np.zeros((len(t), 3))
    m = noise_from_cv_force(t, P, F, cutoff_hz=2500.0, n_blades=n_blades, rpm=rpm)

    Fp = F - F.mean(axis=0)
    dt_cv = float(np.median(np.diff(t)))
    p = dipole_pressure(Fp, dt_cv)
    assert m["noise_dba_band"] == pytest.approx(dba_from_pressure(p, dt_cv, 2500.0), abs=1e-12)
    assert m["noise_dba_band"] != round(m["noise_dba_band"], 2)
    assert m["noise_dba_full"] == pytest.approx(dba_from_pressure(p, dt_cv, None), abs=1e-12)
    assert m["bpf_tone_db"] == pytest.approx(tone_level_db(p, dt_cv, bpf), abs=1e-12)
    assert m["peak_tone_db"] == pytest.approx(
        peak_tone_over_harmonics(p, dt_cv, rpm / 60.0), abs=1e-12
    )
    assert m["thrust_n"] == pytest.approx(float(F[:, 2].mean()), abs=1e-12)
    assert m["thrust_n"] != round(m["thrust_n"], 4)

