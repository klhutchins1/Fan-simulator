"""Absolute far-field fan noise from the control-volume force (Curle compact dipole).

Reads build/fan_cv_force.csv (from the FluidX3D CV-force setup): columns t_s, Px,Py,Pz (SI volume
momentum, kg*m/s), Fsx,Fsy,Fsz (SI surface momentum-flux + pressure force, N). The net force the
fan exerts on the fluid is

    F_i(t) = -( dP_i/dt + Fs_i )

and by Curle's compact-dipole analogy the far-field acoustic pressure at observer direction r_hat,
distance r, is

    p'(x,t) = (r_hat_i / (4 pi c0 r^2)) * dF_i/dt      (retarded time -> pure delay, dropped)

Because the source is acoustically compact (BPF wavelength 1.47 m >> the 0.11 m fan), this
propagates to ANY distance -- so we get an honest 1 m far-field dB(A), unlike near-field probes.
"""
import sys
from pathlib import Path
import numpy as np

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/fan_cv_force.csv")
from fansim.physics.air import C0_AIR as C0
R_OBS = 1.0
PREF = 20e-6
N_BLADES, RPM = 7, 2000.0
BPF = N_BLADES * RPM / 60.0


def a_weight_db(f):
    f = np.asarray(f, dtype=float)
    f2 = f * f
    ra = (12194.0**2 * f2**2) / (
        (f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194.0**2)
    )
    with np.errstate(divide="ignore"):
        return 20.0 * np.log10(ra) + 2.00


def levels(p, dt):
    from scipy.signal import welch
    f, pxx = welch(p, fs=1.0 / dt, nperseg=min(len(p), 4096), window="hann")
    df = f[1] - f[0]
    spl = 20.0 * np.log10(np.sqrt(np.sum(pxx * df)) / PREF)
    aw = a_weight_db(np.maximum(f, 1.0))
    spl_a = 20.0 * np.log10(np.sqrt(np.sum(pxx * 10.0 ** (aw / 10.0) * df)) / PREF)
    return spl, spl_a, f, pxx


def tone(f, pxx, f0, half_bw=8.0):
    m = np.abs(f - f0) <= half_bw
    return 20.0 * np.log10(np.sqrt(np.sum(pxx[m] * (f[1] - f[0]))) / PREF) if np.any(m) else np.nan


def main():
    if not CSV.exists():
        sys.exit(f"CV force history not found: {CSV} (run the FluidX3D CV setup first)")
    d = np.genfromtxt(CSV, delimiter=",", names=True)
    t = d["t_s"]
    dt = float(np.median(np.diff(t)))
    P = np.column_stack([d["Px"], d["Py"], d["Pz"]])
    Fs = np.column_stack([d["Fsx"], d["Fsy"], d["Fsz"]])
    # force on the fluid: F = -(dP/dt + Fs)
    dPdt = np.gradient(P, dt, axis=0)
    F = -(dPdt + Fs)
    Fmean = F.mean(axis=0)
    Fp = F - Fmean
    dur = t[-1] - t[0]
    print(f"samples={len(t)}  dt={dt*1e6:.1f} us  duration={dur*1e3:.1f} ms  ({dur*RPM/60:.1f} revs)")
    print(f"mean fan force  Fx={Fmean[0]:+.4f}  Fy={Fmean[1]:+.4f}  Fz(thrust)={Fmean[2]:+.4f} N")
    print(f"force fluct RMS Fx={Fp[:,0].std():.4f}  Fy={Fp[:,1].std():.4f}  Fz={Fp[:,2].std():.4f} N")
    print(f"BPF={BPF:.1f} Hz,  Nyquist={0.5/dt:.0f} Hz\n")

    dFdt = np.gradient(Fp, dt, axis=0)   # dipole time-derivative
    observers = {
        "on-axis (front)": (0.0, 0.0, 1.0),
        "45 deg": (0.7071, 0.0, 0.7071),
        "in-plane (side)": (1.0, 0.0, 0.0),
    }
    print(f"{'observer @1 m':<20}{'dB':>8}{'dB(A)':>8}{'BPF dB':>9}")
    spectra = {}
    best = None
    for name, rh in observers.items():
        p = (np.asarray(rh) @ dFdt.T) / (4.0 * np.pi * C0 * R_OBS**2)
        spl, spl_a, f, pxx = levels(p, dt)
        spectra[name] = (f, pxx)
        tb = tone(f, pxx, BPF)
        print(f"{name:<20}{spl:8.1f}{spl_a:8.1f}{tb:9.1f}")
        if best is None or spl_a > best[1]:
            best = (name, spl_a)

    # hemispherical-average dB(A) over a set of directions (simple solid-angle mean)
    thetas = np.linspace(0, np.pi, 13)
    ms_a = []
    from scipy.signal import welch
    for th in thetas:
        rh = np.array([np.sin(th), 0.0, np.cos(th)])
        p = (rh @ dFdt.T) / (4.0 * np.pi * C0 * R_OBS**2)
        f, pxx = welch(p, fs=1.0 / dt, nperseg=min(len(p), 4096), window="hann")
        aw = a_weight_db(np.maximum(f, 1.0))
        ms_a.append(np.sum(pxx * 10.0 ** (aw / 10.0) * (f[1] - f[0])) * np.sin(th))
    spl_hemi = 20.0 * np.log10(np.sqrt(np.sum(ms_a) / np.sum(np.sin(thetas))) / PREF)
    print(f"\nhemispherical-avg dB(A) @1 m = {spl_hemi:.1f}   (published A12x25 = 22.6 dB(A))")

    f, pxx = spectra["on-axis (front)"]
    print("\nBPF harmonics (on-axis):")
    for k in range(1, 6):
        print(f"  {k}xBPF = {k*BPF:6.0f} Hz : {tone(f, pxx, k*BPF):5.1f} dB")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 5))
        for name, (f, pxx) in spectra.items():
            spl_f = 10.0 * np.log10(np.maximum(pxx, 1e-30) * (f[1] - f[0]) / PREF**2)
            ax.semilogx(f[1:], spl_f[1:], lw=1.1, label=name)
        for k in range(1, 6):
            ax.axvline(k * BPF, color="k", ls=":", lw=0.6, alpha=0.5)
        ax.set_xlim(20, 0.5 / dt)
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel("SPL per bin (dB re 20 uPa) @1 m")
        ax.set_title("A12x25 fan — control-volume Curle dipole, far-field @1 m")
        ax.legend()
        ax.grid(True, which="both", alpha=0.25)
        out = CSV.with_name("fan_noise_cv_spectrum.png")
        fig.tight_layout()
        fig.savefig(out, dpi=130)
        print(f"\nspectrum plot -> {out}")
    except Exception as e:  # noqa: BLE001
        print(f"(plot skipped: {e})")

    print("\nThis is a TRUE far-field estimate (compact dipole propagated to 1 m). Absolute dB(A)")
    print("still carries coarse-LBM uncertainty (broadband under-resolved; the fan is only ~2 cells")
    print("thick at 1 mm); the BPF tone and RELATIVE deltas between designs remain the most robust.")


if __name__ == "__main__":
    main()
