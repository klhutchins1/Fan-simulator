"""Far-field reduction for the LBM control-volume noise data (Curle compact dipole + A-weighting).

The GPU noise scripts logged a control-volume force history; this module turns it into far-field
levels. It is the single, tested home for the A-weighting curve, the Curle dipole propagation, and
the band-limited dB(A) reduction that were previously duplicated across scripts/fan_noise_*.py.

Curle compact dipole (docs/bibliography.md sec.1):  p'(x,t) = (r_hat . dF/dt) / (4 pi c0 r),
with the fan force on the fluid F(t) = +(dP/dt + Fs) from Reynolds Transport Theorem (#124),
P = control-volume momentum, Fs = outward surface momentum-flux + pressure. Absolute dB(A) is
coarse-grid-limited; the BPF tone and RELATIVE deltas (a consistent band-limit) are the
trustworthy outputs.
"""

from __future__ import annotations

import math

import numpy as np

from fansim.physics.air import C0_AIR

PREF = 20e-6
N_BLADES_DEFAULT, RPM_DEFAULT = 7, 2000.0


def a_weighting_db(f):
    """IEC 61672 A-weighting in dB vs frequency [Hz] (array-safe)."""
    f = np.asarray(f, float)
    if np.any(f < 0.0):
        raise ValueError("frequency f must be >= 0")
    f2 = f * f
    ra = (12194.0**2 * f2**2) / (
        (f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194.0**2)
    )
    with np.errstate(divide="ignore"):
        return 20.0 * np.log10(ra) + 2.00


def blade_pass_frequency(n_blades: int = N_BLADES_DEFAULT, rpm: float = RPM_DEFAULT) -> float:
    """BPF [Hz] = n_blades * rev/s."""
    nb = int(n_blades)
    rpm_f = float(rpm)
    if nb < 0:
        raise ValueError(f"n_blades must be >= 0, got {n_blades!r}")
    if not (math.isfinite(rpm_f) and rpm_f >= 0.0):
        raise ValueError(f"rpm must be finite and >= 0, got {rpm!r}")
    return float(nb * rpm_f / 60.0)


def _welch(sig, dt):
    from scipy.signal import welch

    sig = np.asarray(sig, float)
    dt_f = float(dt)
    if not (math.isfinite(dt_f) and dt_f > 0.0):
        raise ValueError(f"dt must be finite and > 0, got {dt!r}")
    if sig.ndim != 1 or len(sig) < 2:
        raise ValueError("pressure signal must be a 1-D array with at least 2 samples")
    return welch(sig, fs=1.0 / dt_f, nperseg=min(len(sig), 4096), window="hann")


def dba_from_pressure(p, dt, cutoff_hz: float | None = None) -> float:
    """A-weighted overall level [dB(A)] of a pressure time series, optional low-pass at cutoff_hz."""
    p = np.asarray(p, float)
    dt_f = float(dt)
    if not (math.isfinite(dt_f) and dt_f > 0.0):
        raise ValueError(f"dt must be finite and > 0, got {dt!r}")
    if p.ndim != 1 or len(p) < 2:
        raise ValueError("pressure signal must be a 1-D array with at least 2 samples")
    if cutoff_hz is not None:
        from scipy.signal import butter, filtfilt

        cut = float(cutoff_hz)
        if not (math.isfinite(cut) and cut > 0.0):
            raise ValueError(f"cutoff_hz must be finite and > 0, got {cutoff_hz!r}")
        b, a = butter(4, cut / (0.5 / dt_f), "low")
        p = filtfilt(b, a, p)
    f, pxx = _welch(p, dt_f)
    aw = a_weighting_db(np.maximum(f, 1.0))
    ms = float(np.sum(pxx * 10.0 ** (aw / 10.0) * (f[1] - f[0])))
    if not math.isfinite(ms):
        return float("nan")
    return float(20.0 * math.log10(math.sqrt(ms) / PREF)) if ms > 0.0 else float("-inf")


def tone_level_db(p, dt, f0, half_bw: float = 8.0) -> float:
    """Band SPL [dB] within +/- half_bw of f0 (e.g. the blade-pass tone).

    On short windows where the Welch bin spacing exceeds ``2 * half_bw`` and ``f0`` still lies
    inside the resolved spectrum (``f0 <= f[-1] + half_bw``), falls back to the single nearest
    frequency bin instead of returning NaN (#124). Frequencies past Nyquist return NaN.
    """
    f0_f = float(f0)
    bw = float(half_bw)
    if not (math.isfinite(f0_f) and f0_f >= 0.0):
        raise ValueError(f"f0 must be finite and >= 0, got {f0!r}")
    if not (math.isfinite(bw) and bw > 0.0):
        raise ValueError(f"half_bw must be finite and > 0, got {half_bw!r}")
    f, pxx = _welch(p, dt)
    if f0_f > float(f[-1]) + bw:
        return float("nan")
    df = float(f[1] - f[0])
    m = np.abs(f - f0_f) <= bw
    if np.any(m):
        ms = float(np.sum(pxx[m] * df))
    else:
        idx = int(np.argmin(np.abs(f - f0_f)))
        ms = float(pxx[idx] * df)
    if not math.isfinite(ms):
        return float("nan")
    return float(20.0 * math.log10(math.sqrt(ms) / PREF)) if ms > 0.0 else float("-inf")


def peak_tone_over_harmonics(p, dt, f_rev, n_harm: int = 24, half_bw: float = 8.0) -> float:
    """Loudest single tone across shaft-order harmonics k*f_rev (k=1..n_harm), in dB.

    Even blade spacing puts all tonal energy at the blade-pass frequency, so `tone_level_db` at the
    BPF captures it. UNEVEN (but balanced) spacing deliberately SPREADS that energy across k*f_rev
    harmonics — the BPF-only measure then misses where the energy went. This returns the loudest tone
    anywhere in the harmonic series, the honest 'how tonal is it' number to compare even vs uneven."""
    f_rev_f = float(f_rev)
    if not (math.isfinite(f_rev_f) and f_rev_f > 0.0):
        raise ValueError(f"f_rev must be finite and > 0, got {f_rev!r}")
    if int(n_harm) < 1:
        raise ValueError(f"n_harm must be >= 1, got {n_harm!r}")
    levels = [tone_level_db(p, dt, k * f_rev_f, half_bw) for k in range(1, int(n_harm) + 1)]
    levels = [x for x in levels if not math.isnan(x)]  # drop NaN (frequencies past the spectrum)
    return float(max(levels)) if levels else float("nan")


def dipole_pressure(F_fluct, dt, r_hat=(0.0, 0.0, 1.0), c0: float = C0_AIR, r_obs: float = 1.0):
    """Curle compact-dipole far-field pressure time series at observer direction r_hat, distance r_obs."""
    F = np.asarray(F_fluct, float)
    dt_f = float(dt)
    c0_f = float(c0)
    r_f = float(r_obs)
    if F.ndim != 2 or F.shape[0] < 2 or F.shape[1] != 3:
        raise ValueError(f"F_fluct must have shape (N >= 2, 3), got {F.shape}")
    if not (math.isfinite(dt_f) and dt_f > 0.0):
        raise ValueError(f"dt must be finite and > 0, got {dt!r}")
    if not (math.isfinite(c0_f) and c0_f > 0.0):
        raise ValueError(f"c0 must be finite and > 0, got {c0!r}")
    if not (math.isfinite(r_f) and r_f > 0.0):
        raise ValueError(f"r_obs must be finite and > 0, got {r_obs!r}")
    rh = np.asarray(r_hat, float)
    if rh.shape != (3,) or not np.all(np.isfinite(rh)):
        raise ValueError(f"r_hat must be a finite 3-vector, got {r_hat!r}")
    rh_norm = float(np.linalg.norm(rh))
    if rh_norm <= 0.0:
        raise ValueError("r_hat must be non-zero")
    rh = rh / rh_norm
    dFdt = np.gradient(F, dt_f, axis=0)
    return (rh @ dFdt.T) / (4.0 * np.pi * c0_f * r_f)


def force_from_cv(t, P, Fs):
    """Fan force on the fluid F(t) = +(dP/dt + Fs) from CV momentum P and outward flux Fs (both (N,3))."""
    t_arr = np.asarray(t, float)
    P_arr = np.asarray(P, float)
    Fs_arr = np.asarray(Fs, float)
    if t_arr.ndim != 1 or len(t_arr) < 2:
        raise ValueError("t must be a 1-D array with at least 2 samples")
    if P_arr.shape[0] != len(t_arr) or Fs_arr.shape[0] != len(t_arr):
        raise ValueError(
            f"P and Fs must match len(t)={len(t_arr)}, got {P_arr.shape} and {Fs_arr.shape}"
        )
    dt = float(np.median(np.diff(t_arr)))
    if not (math.isfinite(dt) and dt > 0.0):
        raise ValueError(f"time step dt must be finite and > 0, got {dt!r}")
    return (np.gradient(P_arr, dt, axis=0) + Fs_arr), dt


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
        "noise_dba_band": float(dba_from_pressure(p, dt, cutoff_hz)),
        "noise_dba_full": float(dba_from_pressure(p, dt, None)),
        "bpf_tone_db": float(tone_level_db(p, dt, bpf)),
        # loudest tone across ALL shaft-order harmonics — the honest tonality when a design (e.g. uneven
        # spacing) spreads its blade-pass energy off the single BPF. Use THIS to compare tonal designs.
        "peak_tone_db": float(peak_tone_over_harmonics(p, dt, rpm / 60.0)),
        "thrust_n": float(thrust),
        "cutoff_hz": float(cutoff_hz),
        "samples": len(t),
    }
