"""Finalist NOISE evaluator: any impeller STL -> LBM control-volume Curle dipole -> relative dB(A).

Runs the (generalized) FluidX3D CV-noise setup on a given impeller STL and reduces the logged force
history to a single comparable noise number: the A-weighted, band-limited, on-axis far-field level
at 1 m. The band-limit is applied IDENTICALLY to every design, so the (uncertain) absolute offset
cancels and the metric is a valid RELATIVE ranking of fan designs -- the optimizer's finalist noise
objective. Absolute dB(A) stays coarse-grid-limited; the tone + relative deltas are the robust part.

Usage:  uv run python scripts/evaluate_noise.py <impeller.stl> [--cutoff 2500] [--label name]
        uv run python scripts/evaluate_noise.py <impeller.stl> --fwh | --permeable | --patches
        uv run python scripts/evaluate_noise.py --csv build/noise_foo.csv [--fwh|--permeable|--patches]
Import: from evaluate_noise import evaluate_noise -> dict(noise_dba_band, bpf_tone_db, thrust_n, ...)
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parent.parent
FLUIDX3D = Path("E:/Projects/programming_2/FluidX3D")
EXE = FLUIDX3D / "bin" / "FluidX3D.exe"
UCRT = r"C:\msys64\ucrt64\bin"
CFG = PROJECT / "build" / "noise_job.cfg"
from fansim.physics.air import C0_AIR as C0
R_OBS, PREF = 1.0, 20e-6
N_BLADES, RPM = 7, 2000.0
BPF = N_BLADES * RPM / 60.0


def _a_weight_db(f):
    f = np.asarray(f, float)
    f2 = f * f
    ra = (12194.0**2 * f2**2) / (
        (f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194.0**2)
    )
    with np.errstate(divide="ignore"):
        return 20.0 * np.log10(ra) + 2.00


def _tone(f, pxx, f0, half_bw=8.0):
    m = np.abs(f - f0) <= half_bw
    return 20.0 * np.log10(np.sqrt(np.sum(pxx[m] * (f[1] - f[0]))) / PREF) if np.any(m) else np.nan


def analyze_cv_force(csv, cutoff_hz=2500.0, r_hat=(0.0, 0.0, 1.0), fwh=False):
    """Reduce a CV-force CSV to noise metrics (Curle 1/r² default; FW-H 1/r if fwh)."""
    sys.path.insert(0, str(PROJECT))
    from fansim.acoustics.farfield import force_from_cv, noise_from_cv_force

    d = np.genfromtxt(csv, delimiter=",", names=True)
    t = d["t_s"]
    P = np.column_stack([d["Px"], d["Py"], d["Pz"]])
    Fs = np.column_stack([d["Fsx"], d["Fsy"], d["Fsz"]])
    if fwh:
        from fansim.acoustics.fwh import noise_from_compact_force
        F, _dt = force_from_cv(t, P, Fs)
        return noise_from_compact_force(t, F, cutoff_hz=cutoff_hz, r_hat=r_hat)
    m = noise_from_cv_force(t, P, Fs, cutoff_hz=cutoff_hz,
                           n_blades=N_BLADES, rpm=RPM, r_hat=r_hat)
    m["analogy"] = "curle"
    return m


def analyze_permeable(csv, dia_mm=110.5, cutoff_hz=2500.0):
    """Reduce a six-face permeable CSV with the panel FW-H loading kernel."""
    sys.path.insert(0, str(PROJECT))
    from fansim.acoustics.fwh import analyze_permeable_csv
    return analyze_permeable_csv(csv, dia_mm=dia_mm, cutoff_hz=cutoff_hz)


def analyze_patches(csv, dia_mm=110.5, cutoff_hz=2500.0):
    """Reduce a 24-patch permeable CSV with the panel FW-H loading kernel."""
    sys.path.insert(0, str(PROJECT))
    from fansim.acoustics.fwh import analyze_patches_csv
    return analyze_patches_csv(csv, dia_mm=dia_mm, cutoff_hz=cutoff_hz)


def _write_job_cfg(stl, dia_mm, out, mode="cv"):
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(
        f"stl={Path(stl).as_posix()}\ndia_mm={dia_mm:.3f}\nout={Path(out).as_posix()}\n"
        f"mode={mode}\n"
    )


def _analogy_flags(fwh, permeable, patches):
    n = int(bool(fwh)) + int(bool(permeable)) + int(bool(patches))
    if n > 1:
        raise ValueError("cannot combine --fwh, --permeable, and --patches")


def evaluate_noise(stl, dia_mm=None, label=None, cutoff_hz=2500.0, keep_csv=True,
                   fwh=False, permeable=False, patches=False):
    """Run the LBM CV-noise sim on an impeller STL and return noise metrics."""
    _analogy_flags(fwh, permeable, patches)
    stl = Path(stl).resolve()
    if not stl.exists():
        raise FileNotFoundError(stl)
    if dia_mm is None:
        import trimesh
        ext = trimesh.load(str(stl)).extents
        dia_mm = float(max(ext[0], ext[1]))     # assume axis = Z; diameter in the X-Y plane
    label = label or stl.stem
    if patches:
        suffix, mode = "_patches", "patches"
    elif permeable:
        suffix, mode = "_perm", "permeable"
    else:
        suffix, mode = "", "cv"
    out = (PROJECT / "build" / f"noise_{label}{suffix}.csv").resolve()
    _write_job_cfg(stl, dia_mm, out, mode=mode)

    env = os.environ.copy()
    env["PATH"] = UCRT + os.pathsep + env.get("PATH", "")
    print(f"[noise] {label}: dia={dia_mm:.1f} mm  mode={mode}  running LBM (~3 min) ...", flush=True)
    r = subprocess.run([str(EXE)], cwd=str(FLUIDX3D), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=900)
    if not out.exists():
        sys.stderr.write((r.stderr or "")[-1500:] + "\n")
        raise RuntimeError(f"noise run produced no output for {label}")
    if patches:
        m = analyze_patches(out, dia_mm=dia_mm, cutoff_hz=cutoff_hz)
    elif permeable:
        m = analyze_permeable(out, dia_mm=dia_mm, cutoff_hz=cutoff_hz)
    else:
        m = analyze_cv_force(out, cutoff_hz=cutoff_hz, fwh=fwh)
    m.update(label=label, dia_mm=round(dia_mm, 2), stl=str(stl))
    if not keep_csv:
        out.unlink(missing_ok=True)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stl", nargs="?", default=None,
                    help="impeller STL (omit when --csv is set)")
    ap.add_argument("--csv", default=None,
                    help="existing force CSV; skip the LBM run")
    ap.add_argument("--cutoff", type=float, default=2500.0)
    ap.add_argument("--label", default=None)
    ap.add_argument("--dia-mm", type=float, default=None,
                    help="tip diameter for permeable/patch box geometry (default 110.5 or from STL)")
    ap.add_argument("--fwh", action="store_true",
                    help="far-field FW-H loading (1/r) from integrated CV. Default is Curle 1/r2.")
    ap.add_argument("--permeable", action="store_true",
                    help="six-face permeable FW-H (writes mode=permeable; multi-face CSV).")
    ap.add_argument("--patches", action="store_true",
                    help="2x2-per-face permeable FW-H (24 panels; writes mode=patches).")
    a = ap.parse_args()
    n_flags = int(a.fwh) + int(a.permeable) + int(a.patches)
    if n_flags > 1:
        ap.error("cannot combine --fwh, --permeable, and --patches")
    if a.csv:
        dia = a.dia_mm if a.dia_mm is not None else 110.5
        if a.patches:
            m = analyze_patches(a.csv, dia_mm=dia, cutoff_hz=a.cutoff)
        elif a.permeable:
            m = analyze_permeable(a.csv, dia_mm=dia, cutoff_hz=a.cutoff)
        else:
            m = analyze_cv_force(a.csv, cutoff_hz=a.cutoff, fwh=a.fwh)
        m.setdefault("label", a.label or Path(a.csv).stem)
        m.setdefault("dia_mm", a.dia_mm)
        m.setdefault("stl", None)
    elif a.stl:
        m = evaluate_noise(a.stl, label=a.label, cutoff_hz=a.cutoff, fwh=a.fwh,
                           permeable=a.permeable, patches=a.patches, dia_mm=a.dia_mm)
    else:
        ap.error("need an STL or --csv")
    print(f"\n{'metric':<18}value")
    keys = ("label", "dia_mm", "thrust_n", "bpf_tone_db", "noise_dba_band", "noise_dba_full",
            "analogy", "n_panels")
    for k in keys:
        if k in m and m[k] is not None:
            print(f"{k:<18}{m[k]}")
    analogy = m.get("analogy", "curle")
    print(f"\nnoise_dba_band = A-weighted on-axis dB(A)@1m, low-passed at {a.cutoff:.0f} Hz "
          f"(analogy={analogy}; consistent band -> valid RELATIVE metric inside one analogy).")


if __name__ == "__main__":
    main()
