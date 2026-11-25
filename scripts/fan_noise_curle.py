#!/usr/bin/env python3
"""CLI: Curle compact-dipole levels from an LBM force history (FluidX3D).

Maths live in ``fansim.acoustics.farfield`` (RV-4 promote #75). This script only
loads CSV, calls the library, and optionally plots.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from fansim.acoustics.farfield import (
    PREF,
    a_weighting_db,
    blade_pass_frequency,
    dipole_pressure,
    tone_level_db,
)
from fansim.physics.air import C0_AIR as C0  # noqa: F401  — audit/scripts expect C0

R_OBS = 1.0
N_BLADES = 7
RPM = 2000.0


def observer_pressure(t, F, r_hat, r_obs: float = R_OBS):
    """Far-field pressure via ``dipole_pressure`` (1/r Curle; fixes the old r² bug)."""
    dt = float(np.median(np.diff(t)))
    return dipole_pressure(F, dt, r_hat=r_hat, r_obs=r_obs), dt


def levels(p, dt):
    """Overall dB and dB(A) via Welch PSD; plus (freq, PSD) for plotting/tones."""
    from scipy.signal import welch

    fs = 1.0 / dt
    nper = min(len(p), 4096)
    f, pxx = welch(p, fs=fs, nperseg=nper, window="hann")
    df = f[1] - f[0]
    ms = np.sum(pxx * df)
    spl = 20.0 * np.log10(np.sqrt(ms) / PREF)
    aw = a_weighting_db(np.maximum(f, 1.0))
    ms_a = np.sum(pxx * 10.0 ** (aw / 10.0) * df)
    spl_a = 20.0 * np.log10(np.sqrt(ms_a) / PREF)
    return spl, spl_a, f, pxx


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "csv",
        nargs="?",
        default="build/fan_force_history.csv",
        type=Path,
        help="force history CSV (t_s, Fx_N, Fy_N, Fz_N)",
    )
    args = ap.parse_args(argv)
    csv = args.csv
    if not csv.exists():
        print(f"force history not found: {csv} (run the FluidX3D noise setup first)", file=sys.stderr)
        return 1

    d = np.genfromtxt(csv, delimiter=",", names=True)
    t = d["t_s"]
    F = np.column_stack([d["Fx_N"], d["Fy_N"], d["Fz_N"]])
    Fmean = F.mean(axis=0)
    Fp = F - Fmean
    bpf = blade_pass_frequency(N_BLADES, RPM)
    dur = float(t[-1] - t[0])
    print(f"samples={len(t)}  duration={dur * 1e3:.1f} ms  ({dur * RPM / 60:.1f} revs)")
    print(f"mean force  Fx={Fmean[0]:+.4f}  Fy={Fmean[1]:+.4f}  Fz(thrust)={Fmean[2]:+.4f} N")
    print(f"force fluct RMS  Fx={Fp[:, 0].std():.4f}  Fy={Fp[:, 1].std():.4f}  Fz={Fp[:, 2].std():.4f} N")
    print(f"blade-pass frequency (BPF) = {bpf:.1f} Hz\n")

    observers = {
        "on-axis (front)": (0.0, 0.0, 1.0),
        "45 deg": (0.7071, 0.0, 0.7071),
        "in-plane (side)": (1.0, 0.0, 0.0),
    }
    print(f"{'observer @1m':<20} {'dB':>7} {'dB(A)':>7} {'BPF tone dB':>12}")
    spectra = {}
    for name, rh in observers.items():
        p, dt = observer_pressure(t, Fp, rh, r_obs=R_OBS)
        spl, spl_a, f, pxx = levels(p, dt)
        tone = tone_level_db(p, dt, bpf)
        spectra[name] = (f, pxx, p, dt)
        print(f"{name:<20} {spl:7.1f} {spl_a:7.1f} {tone:12.1f}")

    f, pxx, p_axis, dt = spectra["on-axis (front)"]
    print("\nBPF harmonics (on-axis):")
    for k in range(1, 6):
        print(f"  {k}xBPF = {k * bpf:6.0f} Hz : {tone_level_db(p_axis, dt, k * bpf):5.1f} dB")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 5))
        for name, (f, pxx, _, _) in spectra.items():
            spl_f = 10.0 * np.log10(np.maximum(pxx, 1e-30) * (f[1] - f[0]) / PREF**2)
            ax.semilogx(f[1:], spl_f[1:], label=name, lw=1.1)
        for k in range(1, 6):
            ax.axvline(k * bpf, color="k", ls=":", lw=0.6, alpha=0.5)
        ax.set_xlim(20, f[-1])
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel("SPL per bin (dB re 20 uPa)")
        ax.set_title("A12x25 fan — Curle dipole spectrum @1 m (dotted = BPF harmonics)")
        ax.legend()
        ax.grid(True, which="both", alpha=0.25)
        out = csv.with_name("fan_noise_spectrum.png")
        fig.tight_layout()
        fig.savefig(out, dpi=130)
        print(f"\nspectrum plot -> {out}")
    except Exception as exc:  # noqa: BLE001
        print(f"(plot skipped: {exc})")

    print("\nNOTE: published A12x25 = 22.6 dB(A) at 1 m. Absolute dB(A) here is a coarse-LBM")
    print("estimate (broadband under-resolved; dF/dt amplifies the numerical floor); the BPF")
    print("tone and RELATIVE deltas between blade designs are the trustworthy outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
