#!/usr/bin/env python3
"""CLI: Curle far-field levels from a control-volume force history (FluidX3D).

Maths live in ``fansim.acoustics.farfield`` (RV-4 promote #76). This script only
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
    force_from_cv,
    tone_level_db,
)
from fansim.physics.air import C0_AIR as C0  # noqa: F401  — audit/scripts expect C0

R_OBS = 1.0
N_BLADES, RPM = 7, 2000.0


def levels(p, dt):
    from scipy.signal import welch

    f, pxx = welch(p, fs=1.0 / dt, nperseg=min(len(p), 4096), window="hann")
    df = f[1] - f[0]
    spl = 20.0 * np.log10(np.sqrt(np.sum(pxx * df)) / PREF)
    aw = a_weighting_db(np.maximum(f, 1.0))
    spl_a = 20.0 * np.log10(np.sqrt(np.sum(pxx * 10.0 ** (aw / 10.0) * df)) / PREF)
    return spl, spl_a, f, pxx


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "csv",
        nargs="?",
        default="build/fan_cv_force.csv",
        type=Path,
        help="CV force CSV (t_s, Px..Pz, Fsx..Fsz)",
    )
    args = ap.parse_args(argv)
    csv = args.csv
    if not csv.exists():
        print(f"CV force history not found: {csv} (run the FluidX3D CV setup first)", file=sys.stderr)
        return 1

    d = np.genfromtxt(csv, delimiter=",", names=True)
    t = d["t_s"]
    P = np.column_stack([d["Px"], d["Py"], d["Pz"]])
    Fs = np.column_stack([d["Fsx"], d["Fsy"], d["Fsz"]])
    F, dt = force_from_cv(t, P, Fs)
    Fmean = F.mean(axis=0)
    Fp = F - Fmean
    bpf = blade_pass_frequency(N_BLADES, RPM)
    dur = float(t[-1] - t[0])
    print(f"samples={len(t)}  dt={dt * 1e6:.1f} us  duration={dur * 1e3:.1f} ms  ({dur * RPM / 60:.1f} revs)")
    print(f"mean fan force  Fx={Fmean[0]:+.4f}  Fy={Fmean[1]:+.4f}  Fz(thrust)={Fmean[2]:+.4f} N")
    print(f"force fluct RMS Fx={Fp[:, 0].std():.4f}  Fy={Fp[:, 1].std():.4f}  Fz={Fp[:, 2].std():.4f} N")
    print(f"BPF={bpf:.1f} Hz,  Nyquist={0.5 / dt:.0f} Hz\n")

    observers = {
        "on-axis (front)": (0.0, 0.0, 1.0),
        "45 deg": (0.7071, 0.0, 0.7071),
        "in-plane (side)": (1.0, 0.0, 0.0),
    }
    print(f"{'observer @1 m':<20}{'dB':>8}{'dB(A)':>8}{'BPF dB':>9}")
    spectra = {}
    for name, rh in observers.items():
        p = dipole_pressure(Fp, dt, r_hat=rh, r_obs=R_OBS)
        spl, spl_a, f, pxx = levels(p, dt)
        spectra[name] = (f, pxx, p)
        tb = tone_level_db(p, dt, bpf)
        print(f"{name:<20}{spl:8.1f}{spl_a:8.1f}{tb:9.1f}")

    thetas = np.linspace(0, np.pi, 13)
    ms_a = []
    from scipy.signal import welch

    for th in thetas:
        rh = np.array([np.sin(th), 0.0, np.cos(th)])
        p = dipole_pressure(Fp, dt, r_hat=rh, r_obs=R_OBS)
        f, pxx = welch(p, fs=1.0 / dt, nperseg=min(len(p), 4096), window="hann")
        aw = a_weighting_db(np.maximum(f, 1.0))
        ms_a.append(np.sum(pxx * 10.0 ** (aw / 10.0) * (f[1] - f[0])) * np.sin(th))
    spl_hemi = 20.0 * np.log10(np.sqrt(np.sum(ms_a) / np.sum(np.sin(thetas))) / PREF)
    print(f"\nhemispherical-avg dB(A) @1 m = {spl_hemi:.1f}   (published A12x25 = 22.6 dB(A))")

    f, pxx, p_axis = spectra["on-axis (front)"]
    print("\nBPF harmonics (on-axis):")
    for k in range(1, 6):
        print(f"  {k}xBPF = {k * bpf:6.0f} Hz : {tone_level_db(p_axis, dt, k * bpf):5.1f} dB")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 5))
        for name, (f, pxx, _) in spectra.items():
            spl_f = 10.0 * np.log10(np.maximum(pxx, 1e-30) * (f[1] - f[0]) / PREF**2)
            ax.semilogx(f[1:], spl_f[1:], lw=1.1, label=name)
        for k in range(1, 6):
            ax.axvline(k * bpf, color="k", ls=":", lw=0.6, alpha=0.5)
        ax.set_xlim(20, 0.5 / dt)
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel("SPL per bin (dB re 20 uPa) @1 m")
        ax.set_title("A12x25 fan — control-volume Curle dipole, far-field @1 m")
        ax.legend()
        ax.grid(True, which="both", alpha=0.25)
        out = csv.with_name("fan_noise_cv_spectrum.png")
        fig.tight_layout()
        fig.savefig(out, dpi=130)
        print(f"\nspectrum plot -> {out}")
    except Exception as exc:  # noqa: BLE001
        print(f"(plot skipped: {exc})")

    print("\nThis is a TRUE far-field estimate (compact dipole propagated to 1 m). Absolute dB(A)")
    print("still carries coarse-LBM uncertainty (broadband under-resolved; the fan is only ~2 cells")
    print("thick at 1 mm); the BPF tone and RELATIVE deltas between designs remain the most robust.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
