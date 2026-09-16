"""Far-field reduction for the LBM control-volume noise data (Curle compact dipole + A-weighting).

The GPU noise scripts logged a control-volume force history; this module turns it into far-field
levels. It is the single, tested home for the A-weighting curve, the Curle dipole propagation, and
the band-limited dB(A) reduction that were previously duplicated across scripts/fan_noise_*.py.

Curle compact dipole (docs/bibliography.md sec.1):  p'(x,t) = (r_hat . dF/dt) / (4 pi c0 r),
with the fan force on the fluid F(t) = -(dP/dt + Fs), P = control-volume momentum, Fs = surface
momentum-flux + pressure. Absolute dB(A) is coarse-grid-limited; the BPF tone and RELATIVE deltas
(a consistent band-limit) are the trustworthy outputs.
"""

from __future__ import annotations

import numpy as np

C0_AIR = 343.0
PREF = 20e-6
N_BLADES_DEFAULT, RPM_DEFAULT = 7, 2000.0


def a_weighting_db(f):
    """IEC 61672 A-weighting in dB vs frequency [Hz] (array-safe)."""
    f = np.asarray(f, float)
    f2 = f * f
    ra = (12194.0**2 * f2**2) / (
        (f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194.0**2)
    )
    with np.errstate(divide="ignore"):
        return 20.0 * np.log10(ra) + 2.00


def blade_pass_frequency(n_blades: int = N_BLADES_DEFAULT, rpm: float = RPM_DEFAULT) -> float:
    """BPF [Hz] = n_blades * rev/s."""
    return n_blades * rpm / 60.0


def _welch(sig, dt):
    from scipy.signal import welch
    return welch(sig, fs=1.0 / dt, nperseg=min(len(sig), 4096), window="hann")


def dba_from_pressure(p, dt, cutoff_hz: float | None = None) -> float:
    """A-weighted overall level [dB(A)] of a pressure time series, optional low-pass at cutoff_hz."""
    if cutoff_hz is not None:
        from scipy.signal import butter, filtfilt
        b, a = butter(4, cutoff_hz / (0.5 / dt), "low")
        p = filtfilt(b, a, p)
    f, pxx = _welch(p, dt)
    aw = a_weighting_db(np.maximum(f, 1.0))
    ms = np.sum(pxx * 10.0 ** (aw / 10.0) * (f[1] - f[0]))
    return 20.0 * np.log10(np.sqrt(ms) / PREF)


def tone_level_db(p, dt, f0, half_bw: float = 8.0) -> float:
    """Band SPL [dB] within +/- half_bw of f0 (e.g. the blade-pass tone)."""
    f, pxx = _welch(p, dt)
    m = np.abs(f - f0) <= half_bw
    return 20.0 * np.log10(np.sqrt(np.sum(pxx[m] * (f[1] - f[0]))) / PREF) if np.any(m) else float("nan")


def peak_tone_over_harmonics(p, dt, f_rev, n_harm: int = 24, half_bw: float = 8.0) -> float:
    """Loudest single tone across shaft-order harmonics k*f_rev (k=1..n_harm), in dB.

    Even blade spacing puts all tonal energy at the blade-pass frequency, so `tone_level_db` at the
    BPF captures it. UNEVEN (but balanced) spacing deliberately SPREADS that energy across k*f_rev
    harmonics — the BPF-only measure then misses where the energy went. This returns the loudest tone
    anywhere in the harmonic series, the honest 'how tonal is it' number to compare even vs uneven."""
    levels = [tone_level_db(p, dt, k * f_rev, half_bw) for k in range(1, n_harm + 1)]
    levels = [x for x in levels if x == x]  # drop NaN (frequencies past the spectrum)
    return max(levels) if levels else float("nan")


def dipole_pressure(F_fluct, dt, r_hat=(0.0, 0.0, 1.0), c0: float = C0_AIR, r_obs: float = 1.0):
    """Curle compact-dipole far-field pressure time series at observer direction r_hat, distance r_obs."""
    dFdt = np.gradient(np.asarray(F_fluct, float), dt, axis=0)
    return (np.asarray(r_hat, float) @ dFdt.T) / (4.0 * np.pi * c0 * r_obs)


def force_from_cv(t, P, Fs):
    """Fan force on the fluid F(t) = -(dP/dt + Fs) from CV momentum P and surface-flux Fs (both (N,3))."""
    dt = float(np.median(np.diff(t)))
    return -(np.gradient(np.asarray(P, float), dt, axis=0) + np.asarray(Fs, float)), dt


def noise_from_cv_force(t, P, Fs, *, cutoff_hz: float = 2500.0, n_blades: int = N_BLADES_DEFAULT,
                        rpm: float = RPM_DEFAULT, r_hat=(0.0, 0.0, 1.0)) -> dict:
    """Reduce a control-volume force history to noise metrics (the tested core of evaluate_noise).

    Returns band-limited & full A-weighted on-axis dB(A) @1 m, the blade-pass tone level, and the
    mean thrust. See module docstring for the physics.
    """
    F, dt = force_from_cv(t, P, Fs)
    thrust = float(F[:, 2].mean())
    Fp = F - F.mean(axis=0)
    p = dipole_pressure(Fp, dt, r_hat=r_hat)
    bpf = blade_pass_frequency(n_blades, rpm)
    return {
        "noise_dba_band": round(dba_from_pressure(p, dt, cutoff_hz), 2),
        "noise_dba_full": round(dba_from_pressure(p, dt, None), 2),
        "bpf_tone_db": round(tone_level_db(p, dt, bpf), 2),
        # loudest tone across ALL shaft-order harmonics — the honest tonality when a design (e.g. uneven
        # spacing) spreads its blade-pass energy off the single BPF. Use THIS to compare tonal designs.
        "peak_tone_db": round(peak_tone_over_harmonics(p, dt, rpm / 60.0), 2),
        "thrust_n": round(thrust, 4),
        "cutoff_hz": cutoff_hz,
        "samples": int(len(t)),
    }
