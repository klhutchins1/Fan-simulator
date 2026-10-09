"""Curle compact-dipole aeroacoustics from an LBM fan force history.

Reads build/fan_force_history.csv (t_s, Fx_N, Fy_N, Fz_N) produced by the FluidX3D noise setup
and computes far-field sound at a 1 m observer via the Curle compact-source dipole:

    p'(x,t) = (1 / (4 pi c0)) * (x_i / r^2) * dF'_i/dt      (retarded time -> pure delay, dropped)

where F' is the *fluctuating* force (mean removed; the steady thrust does not radiate). Compact
source is valid here: blade-pass tone ~233 Hz -> wavelength 1.47 m >> the 0.11 m fan.

Outputs: overall dB and dB(A) at 1 m for on-axis / 45deg / in-plane observers, the blade-pass
tone level + harmonics, and a spectrum plot. Absolute level is an ESTIMATE (coarse LBM under-
resolves broadband turbulence; the force time-derivative amplifies the high-frequency numerical
floor) -- the robust, comparable quantities are the BPF tone and *relative* deltas between designs.
"""
import sys
from pathlib import Path
import numpy as np

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/fan_force_history.csv")
from fansim.physics.air import C0_AIR as C0
R_OBS = 1.0         # observer distance, m
PREF = 20e-6        # reference pressure, Pa
N_BLADES = 7
RPM = 2000.0
BPF = N_BLADES * RPM / 60.0   # blade-pass frequency, Hz


def a_weight_db(f):
    """IEC 61672 A-weighting in dB vs frequency (Hz)."""
    f = np.asarray(f, dtype=float)
    f2 = f * f
    ra = (12194.0**2 * f2**2) / (
        (f2 + 20.6**2)
        * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2))
        * (f2 + 12194.0**2)
    )
    with np.errstate(divide="ignore"):
        return 20.0 * np.log10(ra) + 2.00


def observer_pressure(t, F, r_hat):
    """Curle dipole far-field pressure time series at unit-distance observer along r_hat."""
    dt = np.median(np.diff(t))
    dFdt = np.gradient(F, dt, axis=0)                 # (N,3) force time-derivative
    proj = dFdt @ np.asarray(r_hat)                   # x_i/r^2 * dF_i/dt, r=1
    return (1.0 / (4.0 * np.pi * C0 * R_OBS**2)) * proj, dt


def levels(p, dt):
    """Overall dB and dB(A) via Welch PSD; plus (freq, PSD) for plotting/tones."""
    from scipy.signal import welch
    fs = 1.0 / dt
    nper = min(len(p), 4096)
    f, pxx = welch(p, fs=fs, nperseg=nper, window="hann")  # Pa^2/Hz
    df = f[1] - f[0]
    ms = np.sum(pxx * df)                                  # mean-square pressure
    spl = 20.0 * np.log10(np.sqrt(ms) / PREF)
    aw = a_weight_db(np.maximum(f, 1.0))
    ms_a = np.sum(pxx * 10.0 ** (aw / 10.0) * df)
    spl_a = 20.0 * np.log10(np.sqrt(ms_a) / PREF)
    return spl, spl_a, f, pxx


def tone_level(f, pxx, f0, half_bw=8.0):
    """Band SPL (dB) integrated within +/- half_bw Hz of f0."""
    m = np.abs(f - f0) <= half_bw
    if not np.any(m):
        return float("nan")
    df = f[1] - f[0]
    return 20.0 * np.log10(np.sqrt(np.sum(pxx[m] * df)) / PREF)


def main():
    if not CSV.exists():
        sys.exit(f"force history not found: {CSV} (run the FluidX3D noise setup first)")
    d = np.genfromtxt(CSV, delimiter=",", names=True)
    t = d["t_s"]
    F = np.column_stack([d["Fx_N"], d["Fy_N"], d["Fz_N"]])
    Fmean = F.mean(axis=0)
    Fp = F - Fmean                                         # fluctuating force
    dur = t[-1] - t[0]
    print(f"samples={len(t)}  duration={dur*1e3:.1f} ms  ({dur*RPM/60:.1f} revs)")
    print(f"mean force  Fx={Fmean[0]:+.4f}  Fy={Fmean[1]:+.4f}  Fz(thrust)={Fmean[2]:+.4f} N")
    print(f"force fluct RMS  Fx={Fp[:,0].std():.4f}  Fy={Fp[:,1].std():.4f}  Fz={Fp[:,2].std():.4f} N")
    print(f"blade-pass frequency (BPF) = {BPF:.1f} Hz\n")

    observers = {
        "on-axis (front)": (0.0, 0.0, 1.0),
        "45 deg": (0.7071, 0.0, 0.7071),
        "in-plane (side)": (1.0, 0.0, 0.0),
    }
    print(f"{'observer @1m':<20} {'dB':>7} {'dB(A)':>7} {'BPF tone dB':>12}")
    spectra = {}
    for name, rh in observers.items():
        p, dt = observer_pressure(t, Fp, rh)
        spl, spl_a, f, pxx = levels(p, dt)
        tone = tone_level(f, pxx, BPF)
        spectra[name] = (f, pxx)
        print(f"{name:<20} {spl:7.1f} {spl_a:7.1f} {tone:12.1f}")

    # tonal content at on-axis observer (BPF + harmonics)
    f, pxx = spectra["on-axis (front)"]
    print("\nBPF harmonics (on-axis):")
    for k in range(1, 6):
        print(f"  {k}xBPF = {k*BPF:6.0f} Hz : {tone_level(f, pxx, k*BPF):5.1f} dB")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 5))
        for name, (f, pxx) in spectra.items():
            spl_f = 10.0 * np.log10(np.maximum(pxx, 1e-30) * (f[1] - f[0]) / PREF**2)
            ax.semilogx(f[1:], spl_f[1:], label=name, lw=1.1)
        for k in range(1, 6):
            ax.axvline(k * BPF, color="k", ls=":", lw=0.6, alpha=0.5)
        ax.set_xlim(20, f[-1])
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel("SPL per bin (dB re 20 uPa)")
        ax.set_title("A12x25 fan — Curle dipole spectrum @1 m (dotted = BPF harmonics)")
        ax.legend()
        ax.grid(True, which="both", alpha=0.25)
        out = CSV.with_name("fan_noise_spectrum.png")
        fig.tight_layout()
        fig.savefig(out, dpi=130)
        print(f"\nspectrum plot -> {out}")
    except Exception as e:  # noqa: BLE001
        print(f"(plot skipped: {e})")

    print("\nNOTE: published A12x25 = 22.6 dB(A) at 1 m. Absolute dB(A) here is a coarse-LBM")
    print("estimate (broadband under-resolved; dF/dt amplifies the numerical floor); the BPF")
    print("tone and RELATIVE deltas between blade designs are the trustworthy outputs.")


if __name__ == "__main__":
    main()
