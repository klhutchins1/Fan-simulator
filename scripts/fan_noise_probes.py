# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Fan noise from LBM fixed pressure probes (numerical microphones).

Reads build/fan_probe_history.csv (written by the FluidX3D probe noise setup): a few '#' metadata
lines giving each probe's distance from the fan, then columns t_s, <probe>_Pa ... of the acoustic
pressure fluctuation p' at each fixed fluid point.

For each probe we report the blade-pass tone (BPF=233 Hz) + harmonics, the near-field overall SPL
and dB(A), and a far-field @1 m estimate via 1/r spherical spreading (compact source: wavelength
1.47 m >> 0.11 m fan). Near-field probes over-read the true far field (hydrodynamic pseudo-sound
does not spread as 1/r), so the farthest probe is the most trustworthy and the BPF tone + RELATIVE
deltas between designs are the robust outputs, not the absolute broadband dB(A).
"""
import re
import sys
from pathlib import Path
import numpy as np

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/fan_probe_history.csv")
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
    if not np.any(m):
        return float("nan")
    return 20.0 * np.log10(np.sqrt(np.sum(pxx[m] * (f[1] - f[0]))) / PREF)


def main():
    if not CSV.exists():
        sys.exit(f"probe history not found: {CSV} (run the FluidX3D probe setup first)")
    lines = CSV.read_text().splitlines()
    dists, names_meta = {}, []
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("#"):
            m = re.match(r"#\s*([^,]+),\s*\d+,\s*\d+,\s*\d+,\s*([\d.]+)", ln)
            if m:
                names_meta.append(m.group(1).strip())
                dists[m.group(1).strip()] = float(m.group(2))
        elif ln.startswith("t_s"):
            header_idx = i
            cols = ln.split(",")
            break
    data = np.loadtxt(lines[header_idx + 1:], delimiter=",")
    t = data[:, 0]
    dt = np.median(np.diff(t))
    dur = t[-1] - t[0]
    probe_cols = [c[:-3] for c in cols[1:]]  # strip "_Pa"
    print(f"samples={len(t)}  dt={dt*1e6:.1f} us  duration={dur*1e3:.1f} ms  ({dur*RPM/60:.1f} revs)")
    print(f"BPF={BPF:.1f} Hz,  Nyquist={0.5/dt:.0f} Hz\n")

    print(f"{'probe':<16}{'dist_m':>7}{'p_rms_Pa':>10}{'nearSPL':>8}{'near dBA':>9}"
          f"{'BPF dB':>8}{'far@1m dBA*':>12}")
    spectra = {}
    for j, name in enumerate(probe_cols):
        p = data[:, j + 1]
        p = p - np.mean(p)
        d = dists.get(name, np.nan)
        spl, spl_a, f, pxx = levels(p, dt)
        spectra[name] = (f, pxx, d)
        prms = np.sqrt(np.mean(p**2))
        t_bpf = tone(f, pxx, BPF)
        far_a = spl_a + 20.0 * np.log10(d / 1.0) if d == d else float("nan")  # 1/r to 1 m
        print(f"{name:<16}{d:7.3f}{prms:10.4f}{spl:8.1f}{spl_a:9.1f}{t_bpf:8.1f}{far_a:12.1f}")

    # tonal content at the farthest axial probe
    far_name = max(spectra, key=lambda k: spectra[k][2])
    f, pxx, d = spectra[far_name]
    print(f"\nBPF harmonics @ {far_name} (dist {d:.3f} m):")
    for k in range(1, 6):
        print(f"  {k}xBPF = {k*BPF:6.0f} Hz : {tone(f, pxx, k*BPF):5.1f} dB (near-field)")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 5))
        for name, (f, pxx, d) in spectra.items():
            spl_f = 10.0 * np.log10(np.maximum(pxx, 1e-30) * (f[1] - f[0]) / PREF**2)
            ax.semilogx(f[1:], spl_f[1:], lw=1.0, label=f"{name} ({d*1000:.0f} mm)")
        for k in range(1, 6):
            ax.axvline(k * BPF, color="k", ls=":", lw=0.6, alpha=0.5)
        ax.set_xlim(20, 0.5 / dt)
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel("SPL per bin (dB re 20 uPa, near-field)")
        ax.set_title("A12x25 fan — probe pressure spectra (dotted = BPF harmonics)")
        ax.legend(fontsize=8)
        ax.grid(True, which="both", alpha=0.25)
        out = CSV.with_name("fan_noise_probe_spectrum.png")
        fig.tight_layout()
        fig.savefig(out, dpi=130)
        print(f"\nspectrum plot -> {out}")
    except Exception as e:  # noqa: BLE001
        print(f"(plot skipped: {e})")

    print("\n* far@1m dBA = near dB(A) scaled by 1/r from the probe distance — an UPPER estimate")
    print("  (near-field pseudo-sound doesn't fully obey 1/r). Published A12x25 = 22.6 dB(A)@1 m.")
    print("  Trust the BPF tone and RELATIVE deltas between designs, not the absolute broadband.")


if __name__ == "__main__":
    main()
