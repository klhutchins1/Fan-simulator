"""Audit #6: acoustics models vs analytic results (verification only; validation is INCONCLUSIVE).

Tolerances were pre-registered in docs/validation/audits/2026-09-29-audit-06-acoustics.md before any
comparison:
  compact dipole amplitude vs F0 w cos(th)/(4 pi c0 r)      rel err <= 0.5% (finite-difference limited)
  1/r decay (r=1 vs 2 vs 4 m), retarded-time shift           amplitude ratio within 0.5%; waveform 0.5%
  cos(theta) directivity, null at 90 deg                     rel err <= 0.5%; null <= 1e-9 of peak
  radiated power  W = <Fdot^2>/(12 pi rho c0^3)              rel err <= 0.5% vs numeric sphere integral
  BPF = B rpm/60, harmonics k*BPF                            exact (1e-12)
  tonal array factor: equal spacing A(m)=N at m=kN, 0 else   1e-9; FFT synthesis vs A(m) 1e-9
  Proudman  alpha rho eps Mt^5  (alpha 0.1 as cited)         1e-12 vs hand value; Mt^5 scaling 1e-12
  dB references (pref 20 uPa, W_ref 1 pW)                    0.05 dB; sine dB(A) 0.15 dB
  A-weighting vs IEC 61672-1 table                           0.1 dB (table is rounded to 0.1)
  panel FW-H loading vs analytic offset dipole               rel err <= 1%
  single-sourced c0 / rho                                    identity
"""

from __future__ import annotations

import importlib.util
import inspect
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from fansim.acoustics import farfield as ff
from fansim.acoustics import fwh, tonal
from fansim.acoustics import proxies as px
from fansim.physics import air

C0 = air.C0_AIR
RHO = air.RHO_AMCA
ROOT = Path(__file__).resolve().parents[2]

F0, FREQ = 2.0, 233.333333          # N, Hz (fan BPF-like)
W = 2 * math.pi * FREQ


def _t(dur=0.5, n_per=400):
    dt = 1.0 / (FREQ * n_per)
    return np.arange(0, dur, dt), dt


def _amp(p):
    """Steady-state amplitude of a sinusoid (ignore the first/last 10%)."""
    n = len(p)
    return np.max(np.abs(p[n // 10: -n // 10]))


# ---------------------------------------------------------------- acoustics.curle_dipole
@pytest.mark.parametrize("theta_deg", [0.0, 30.0, 60.0, 90.0, 120.0, 180.0])
def test_dipole_amplitude_and_directivity(theta_deg):
    t, dt = _t()
    th = math.radians(theta_deg)
    F = np.zeros((len(t), 3))
    F[:, 2] = F0 * np.cos(W * t)
    r_hat = (math.sin(th), 0.0, math.cos(th))
    p = ff.dipole_pressure(F, dt, r_hat=r_hat, r_obs=1.0)
    peak = F0 * W / (4 * math.pi * C0)          # hand: amplitude at theta=0, r=1
    expected = peak * abs(math.cos(th))
    if abs(math.cos(th)) < 1e-6:
        assert _amp(p) <= 1e-9 * peak
    else:
        assert _amp(p) == pytest.approx(expected, rel=0.005)


def test_dipole_absolute_hand_number():
    # F0=2 N, 233.33 Hz, r=1 m: p = 2*1466.07/(4 pi 343) = 0.6803 Pa
    t, dt = _t()
    F = np.zeros((len(t), 3))
    F[:, 2] = F0 * np.cos(W * t)
    assert _amp(ff.dipole_pressure(F, dt)) == pytest.approx(0.6803, rel=0.005)


def test_dipole_one_over_r_and_retarded_time():
    t, dt = _t(dur=0.5)
    F = np.zeros((len(t), 3))
    F[:, 2] = F0 * np.cos(W * t)
    amps = {}
    for r in (1.0, 2.0, 4.0):
        p = fwh.loading_pressure_compact(F, dt, r_obs=r)
        # analytic retarded solution p = -F0 W sin(W (t - r/c)) /(4 pi c r), valid for t > r/c
        ana = -F0 * W * np.sin(W * (t - r / C0)) / (4 * math.pi * C0 * r)
        m = t > r / C0 + 2.0 / FREQ
        assert np.max(np.abs(p[m] - ana[m])) <= 0.005 * F0 * W / (4 * math.pi * C0 * r)
        amps[r] = _amp(p)
    assert amps[1.0] / amps[2.0] == pytest.approx(2.0, rel=0.005)
    assert amps[2.0] / amps[4.0] == pytest.approx(2.0, rel=0.005)


def test_dipole_power_matches_curle_closed_form():
    """Integrate intensity over a sphere numerically; compare with <Fdot^2>/(12 pi rho c0^3)."""
    t, dt = _t()
    F = np.zeros((len(t), 3))
    F[:, 2] = F0 * np.cos(W * t)
    r = 3.0
    th = np.linspace(0, math.pi, 361)
    ms = []
    for a in th:
        p = ff.dipole_pressure(F, dt, r_hat=(math.sin(a), 0, math.cos(a)), r_obs=r)
        n = len(p)
        ms.append(np.mean(p[n // 10: -n // 10] ** 2))
    ms = np.array(ms)
    integrand = ms / (RHO * C0) * 2 * math.pi * r * r * np.sin(th)
    w_num = float(np.sum(0.5 * (integrand[1:] + integrand[:-1]) * np.diff(th)))
    w_closed = 0.5 * (F0 * W) ** 2 / (12 * math.pi * RHO * C0**3)
    assert w_num == pytest.approx(w_closed, rel=0.005)


def test_cv_force_pipeline_tone_level():
    """P=0, Fs=+F(t) => fan-on-fluid force F(t) (#124); BPF tone level equals analytic rms SPL."""
    n_b, rpm = 7, 2000.0
    bpf = ff.blade_pass_frequency(n_b, rpm)
    dt = 1.0 / 8192.0
    t = np.arange(0, 2.0, dt)
    Fz = 0.05 * np.sin(2 * math.pi * bpf * t)
    Fs = np.zeros((len(t), 3))
    Fs[:, 2] = Fz
    out = ff.noise_from_cv_force(t, np.zeros((len(t), 3)), Fs, n_blades=n_b, rpm=rpm)
    p_rms = 0.05 * 2 * math.pi * bpf / (4 * math.pi * C0) / math.sqrt(2)
    assert out["bpf_tone_db"] == pytest.approx(20 * math.log10(p_rms / 20e-6), abs=0.3)
    assert out["thrust_n"] == pytest.approx(0.0, abs=1e-3)


def test_force_from_cv_sign_convention():
    """F_{fan->fluid} = +(dP/dt + Fs) per RTT (#124): P=a t => F = +a + Fs."""
    t = np.linspace(0, 1, 101)
    P = np.zeros((101, 3))
    P[:, 2] = 3.0 * t
    Fs = np.zeros((101, 3))
    Fs[:, 2] = 1.0
    F, _ = ff.force_from_cv(t, P, Fs)
    assert np.allclose(F[:, 2], 4.0)


def test_near_field_term_error_is_quantified():
    """The kernel is the FAR-field term only. Exact compact-dipole field has an extra F/r^2 term in
    quadrature; its amplitude error is sqrt(1+1/(k r)^2) - 1. Quantify at the observers in use."""
    k = W / C0

    def err_db(r):
        return 20 * math.log10(math.sqrt(1 + 1 / (k * r) ** 2))

    assert err_db(1.0) < 0.35          # 1 m (scripts, LBM): far-field kernel adequate for the tone
    assert err_db(0.2) > 3.0           # 0.2 m (DES default): kernel UNDER-predicts the tone by ~3.8 dB
    assert math.isclose(err_db(0.2), 3.8, abs_tol=0.3)


# ---------------------------------------------------------------- acoustics.tonal_bpf
def test_bpf_and_harmonics():
    assert ff.blade_pass_frequency(7, 2000.0) == pytest.approx(7 * 2000 / 60, rel=1e-12)
    assert ff.blade_pass_frequency(9, 1500.0) == pytest.approx(225.0, rel=1e-12)
    assert ff.blade_pass_frequency() == pytest.approx(7 * 2000 / 60)
    for k in (1, 2, 3):
        assert k * ff.blade_pass_frequency(5, 3000.0) == pytest.approx(k * 250.0)


@pytest.mark.parametrize("n", [3, 5, 7, 9])
def test_equal_spacing_array_factor(n):
    ang = 2 * np.pi * np.arange(n) / n
    m, a = tonal.blade_passing_modes(ang, m_max=4 * n)
    for mi, ai in zip(m, a):
        assert ai == pytest.approx(n if mi % n == 0 else 0.0, abs=1e-9)
    assert tonal.tonal_peak_ratio(ang) == pytest.approx(1.0, abs=1e-12)
    assert tonal.peak_tone_reduction_db(ang) == pytest.approx(0.0, abs=1e-9)


def test_uneven_spacing_lowers_peak_and_db_formula():
    n = 7
    ang = 2 * np.pi * np.arange(n) / n + 0.15 * np.sin(3 * np.arange(n))
    r = tonal.tonal_peak_ratio(ang)
    assert 0.0 < r < 1.0
    assert tonal.peak_tone_reduction_db(ang) == pytest.approx(20 * math.log10(r), abs=1e-12)
    _, a = tonal.blade_passing_modes(ang)
    assert a.max() <= n + 1e-9          # triangle inequality bound


def test_array_factor_matches_fft_synthesis():
    """Sum of N identical Gaussian pulses at angles th_k: harmonic m of the sum = A(m) x pulse."""
    ang = np.array([0.0, 1.1, 2.0, 3.3, 4.0, 5.2])
    ntime = 4096
    phi = 2 * np.pi * np.arange(ntime) / ntime
    width = 0.05

    def pulse(c):
        d = (phi - c + np.pi) % (2 * np.pi) - np.pi
        return np.exp(-0.5 * (d / width) ** 2)

    single = pulse(0.0)
    sig = sum(pulse(a) for a in ang)
    S, S1 = np.fft.rfft(sig), np.fft.rfft(single)
    m = np.arange(1, 25)
    _, amp = tonal.blade_passing_modes(ang, m_max=24)
    assert np.allclose(np.abs(S[m]) / np.abs(S1[m]), amp, atol=1e-9)


# ---------------------------------------------------------------- acoustics.proudman
def test_proudman_hand_value_and_scaling():
    k, eps = 1.5, 10.0
    mt = math.sqrt(2 * k) / C0
    hand = 0.1 * RHO * eps * mt**5
    assert float(px.proudman_power_density(k, eps)) == pytest.approx(hand, rel=1e-12)
    assert px.ALPHA_PROUDMAN == 0.1
    base = float(px.proudman_power_density(1.0, 1.0))
    assert float(px.proudman_power_density(4.0, 1.0)) / base == pytest.approx(32.0, rel=1e-12)
    assert float(px.proudman_power_density(1.0, 3.0)) / base == pytest.approx(3.0, rel=1e-12)
    assert float(px.proudman_power_density(1.0, 1.0, rho=2 * RHO)) / base == pytest.approx(2.0, rel=1e-12)
    assert float(px.proudman_power_density(1.0, 1.0, c0=2 * C0)) / base == pytest.approx(2.0**-5, rel=1e-12)


def test_proudman_units_and_swl():
    # dimensions: rho[kg/m3] * eps[m2/s3] = kg/(m s3) = W/m3 (Mt dimensionless)
    v = np.array([0.5, 2.0])
    k = np.array([1.0, 2.0])
    eps = np.array([5.0, 7.0])
    total = float(np.sum(px.proudman_power_density(k, eps) * v))
    assert px.proudman_swl(k, eps, v) == pytest.approx(10 * math.log10(total / 1e-12), abs=1e-9)
    assert px.sound_power_level(1e-12) == pytest.approx(0.0, abs=1e-12)
    assert px.sound_power_level(1e-3) == pytest.approx(90.0, abs=1e-9)
    assert px.sound_power_level(0.0) == float("-inf")
    assert px.epsilon_from_komega(2.0, 50.0) == pytest.approx(0.09 * 2.0 * 50.0, rel=1e-12)
    assert float(px.turbulent_mach(1.5)) == pytest.approx(math.sqrt(3.0) / C0, rel=1e-12)


def test_curle_surface_proxy_is_per_correlation_area():
    """FINDING: curle_surface_swl integrates <pdot^2> dS but omits the correlation area, so its value
    is W/m^2 (dimensionally), not W. For a fully coherent uniform patch of area A the true Curle power
    is <Fdot^2>/(12 pi rho c^3) = A^2 <pdot^2>/(12 pi rho c^3) = (proxy linear value) * A.
    Ranking use is unaffected; the docstring 'radiated power ... dB re 1 pW' is not literal."""
    A, dpdt2 = 0.01, 4.0e4
    w_proxy = 10 ** (px.curle_surface_swl(np.array([dpdt2]), np.array([A])) / 10) * 1e-12
    w_true = (A * A * dpdt2) / (12 * math.pi * RHO * C0**3)
    assert w_true / w_proxy == pytest.approx(A, rel=1e-9)
    assert w_proxy == pytest.approx(A * dpdt2 / (12 * math.pi * RHO * C0**3), rel=1e-9)


# ---------------------------------------------------------------- levels / weighting
IEC_A = {10: -70.4, 63: -26.2, 100: -19.1, 125: -16.1, 250: -8.6, 500: -3.2, 1000: 0.0,
         2000: 1.2, 4000: 1.0, 8000: -1.1, 10000: -2.5}


@pytest.mark.parametrize("f,expected", sorted(IEC_A.items()))
def test_a_weighting_iec61672(f, expected):
    assert float(ff.a_weighting_db(f)) == pytest.approx(expected, abs=0.1)


def test_a_weighting_1khz_is_zero():
    assert abs(float(ff.a_weighting_db(1000.0))) < 0.01


def test_db_reference_and_sine_level():
    assert ff.PREF == 20e-6
    fs = 8192.0
    dt = 1.0 / fs
    t = np.arange(0, 4.0, dt)
    p = 1.0 * np.sin(2 * math.pi * 1024.0 * t)            # 1 Pa amplitude, on a Welch bin
    exp_db = 20 * math.log10((1 / math.sqrt(2)) / 20e-6)   # 90.97 dB
    assert ff.tone_level_db(p, dt, 1024.0) == pytest.approx(exp_db, abs=0.15)
    aw = float(ff.a_weighting_db(1024.0))
    assert ff.dba_from_pressure(p, dt) == pytest.approx(exp_db + aw, abs=0.15)
    assert 20 * math.log10(1.0 / 20e-6) == pytest.approx(93.98, abs=0.01)


# ---------------------------------------------------------------- acoustics.fwh
def test_panel_kernel_offset_dipole_matches_analytic():
    """One panel at r0 (observer at x_obs): p = r_hat.Fdot(t-r/c)/(4 pi c r), r = |x - r0|."""
    t, _dt = _t(dur=0.4)
    F = np.zeros((len(t), 3))
    F[:, 0] = F0 * np.cos(W * t)
    F[:, 2] = 0.5 * F0 * np.sin(W * t)
    r0 = np.array([0.03, -0.02, 0.05])
    x_obs = np.array([1.2, 0.7, 1.9])
    p = fwh.loading_pressure_panels(t, [{"r0": r0, "area": 1.0, "n_hat": (0, 0, 1), "f": F}], x_obs=x_obs)
    d = x_obs - r0
    r = np.linalg.norm(d)
    rh = d / r
    tr = t - r / C0
    fdot_x = -F0 * W * np.sin(W * tr)
    fdot_z = 0.5 * F0 * W * np.cos(W * tr)
    pdot = (rh[0] * fdot_x + rh[2] * fdot_z) / (4 * math.pi * C0 * r)
    m = t > r / C0 + 2 / FREQ
    scale = F0 * W / (4 * math.pi * C0 * r)
    assert np.max(np.abs(p[m] - pdot[m])) <= 0.01 * scale


def test_panel_superposition_and_compact_consistency():
    t, dt = _t(dur=0.3)
    F = np.zeros((len(t), 3))
    F[:, 2] = F0 * np.cos(W * t)
    x = (0.0, 0.0, 1.0)
    one = fwh.loading_pressure_panels(t, [{"r0": (0, 0, 0), "f": F}], x_obs=x)
    two = fwh.loading_pressure_panels(t, [{"r0": (0, 0, 0), "f": F}, {"r0": (0, 0, 0), "f": F}], x_obs=x)
    assert np.allclose(two, 2 * one, atol=1e-12)
    comp = fwh.loading_pressure_compact(F, dt, r_hat=x, r_obs=1.0)
    assert np.max(np.abs(comp - one)) <= 0.01 * np.max(np.abs(comp))


def test_fwh_has_no_source_motion_or_thickness_terms():
    """Documented absence: 'FW-H' here is the stationary loading-noise kernel. No Mach / velocity /
    Doppler argument exists, so the moving-source (Farassat 1A) factor 1/(1 - M_r)^2 is not computed."""
    for fn in (fwh.loading_pressure_compact, fwh.loading_pressure_panels, fwh.noise_from_permeable_panels):
        names = set(inspect.signature(fn).parameters)
        assert not (names & {"mach", "v_src", "velocity", "M", "omega"}), fn.__name__
    assert not [n for n in dir(fwh) if "doppler" in n.lower() or "mach" in n.lower()]


def test_des_face_force_uses_single_sourced_rho():
    from fansim.cfd import des_fwh
    assert des_fwh.RHO_AIR is air.RHO_AMCA


# ---------------------------------------------------------------- single-sourcing
def test_c0_rho_single_sourced():
    from fansim.propeller import noise as pn
    assert ff.C0_AIR is air.C0_AIR and fwh.C0_AIR is air.C0_AIR and px.C0_AIR is air.C0_AIR
    assert px.RHO_AIR is air.RHO_AMCA and pn.C_SOUND is air.C0_AIR
    assert inspect.signature(ff.dipole_pressure).parameters["c0"].default == air.C0_AIR


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem + "_audit", path)
    old = sys.argv
    sys.argv = [str(path)]
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.argv = old
    return mod


def test_script_a_weighting_uses_farfield_module():
    """#75/#76: curle/cv CLIs import farfield; evaluate_noise may still keep a local alias."""
    f = np.array([50.0, 100.0, 1000.0, 4000.0, 9000.0])
    for name in ("fan_noise_curle.py", "fan_noise_cv.py"):
        mod = _load(ROOT / "scripts" / name)
        assert mod.a_weighting_db is ff.a_weighting_db, name
        assert np.allclose(mod.a_weighting_db(f), ff.a_weighting_db(f), atol=1e-12), name
        assert mod.C0 == air.C0_AIR
    mod = _load(ROOT / "scripts" / "evaluate_noise.py")
    assert np.allclose(mod._a_weight_db(f), ff.a_weighting_db(f), atol=1e-12)
    # evaluate_noise delegates all acoustic math to fansim.acoustics.farfield / fwh (no local C0 alias)
    assert not hasattr(mod, "C0")


def test_curle_script_uses_one_over_r_dipole():
    """#75: observer_pressure delegates to dipole_pressure (1/r), including r_obs ≠ 1 m."""
    mod = _load(ROOT / "scripts" / "fan_noise_curle.py")
    t, dt = _t(dur=0.05)
    F = np.zeros((len(t), 3))
    F[:, 2] = F0 * np.cos(W * t)
    p1, _ = mod.observer_pressure(t, F, (0, 0, 1), r_obs=1.0)
    p2, _ = mod.observer_pressure(t, F, (0, 0, 1), r_obs=2.0)
    assert np.max(np.abs(p1 - ff.dipole_pressure(F, dt, r_obs=1.0))) <= 1e-9 * np.max(np.abs(p1))
    assert np.max(np.abs(p2 - ff.dipole_pressure(F, dt, r_obs=2.0))) <= 1e-9 * np.max(np.abs(p2))
    assert np.max(np.abs(p1)) / np.max(np.abs(p2)) == pytest.approx(2.0, rel=1e-6)


# ---------------------------------------------------------------- claims (propeller proxies)
def test_prop_fwh_synthetic_is_not_a_fwh_calculation():
    from fansim.propeller.noise import prop_fwh_from_mean_thrust
    a = prop_fwh_from_mean_thrust(1.0, 3000.0, 3)
    b = prop_fwh_from_mean_thrust(1.0, 9000.0, 3)
    assert a["bpf_hz"] == pytest.approx(3 * 3000 / 60)
    # level ignores rpm entirely: 20 log10(T) + 40 -> no tip-speed / Mach dependence
    assert a["noise_dba_band"] == b["noise_dba_band"] == pytest.approx(40.0)
    assert prop_fwh_from_mean_thrust(10.0, 3000.0, 3)["noise_dba_band"] == pytest.approx(60.0)


def test_prop_rel_dba_monotone_in_tip_speed():
    from types import SimpleNamespace

    from fansim.propeller.noise import estimate_prop_noise
    prm = SimpleNamespace(tip_radius=60.0, n_blades=3)
    perf = SimpleNamespace(thrust_n=2.0)
    lo = estimate_prop_noise(prm, 4000.0, perf)
    hi = estimate_prop_noise(prm, 8000.0, perf)
    assert hi["rel_dba"] > lo["rel_dba"]
    assert lo["bpf_hz"] == pytest.approx(3 * 4000 / 60, abs=0.5)
    assert lo["tip_mach"] == pytest.approx(4000 * 2 * math.pi / 60 * 0.06 / C0, abs=1e-3)
