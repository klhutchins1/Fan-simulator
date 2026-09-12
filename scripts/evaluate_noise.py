# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Finalist NOISE evaluator: any impeller STL -> LBM control-volume Curle dipole -> relative dB(A).

Runs the (generalized) FluidX3D CV-noise setup on a given impeller STL and reduces the logged force
history to a single comparable noise number: the A-weighted, band-limited, on-axis far-field level
at 1 m. The band-limit is applied IDENTICALLY to every design, so the (uncertain) absolute offset
cancels and the metric is a valid RELATIVE ranking of fan designs -- the optimizer's finalist noise
objective. Absolute dB(A) stays coarse-grid-limited; the tone + relative deltas are the robust part.

Usage:  uv run python scripts/evaluate_noise.py <impeller.stl> [--cutoff 2500] [--label name]
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
C0, R_OBS, PREF = 343.0, 1.0, 20e-6
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


def analyze_cv_force(csv, cutoff_hz=2500.0, r_hat=(0.0, 0.0, 1.0)):
    """Reduce a CV-force CSV to noise metrics (delegates to fansim.acoustics.farfield)."""
    sys.path.insert(0, str(PROJECT))
    from fansim.acoustics.farfield import noise_from_cv_force

    d = np.genfromtxt(csv, delimiter=",", names=True)
    P = np.column_stack([d["Px"], d["Py"], d["Pz"]])
    Fs = np.column_stack([d["Fsx"], d["Fsy"], d["Fsz"]])
    return noise_from_cv_force(d["t_s"], P, Fs, cutoff_hz=cutoff_hz,
                               n_blades=N_BLADES, rpm=RPM, r_hat=r_hat)


def evaluate_noise(stl, dia_mm=None, label=None, cutoff_hz=2500.0, keep_csv=True):
    """Run the LBM CV-noise sim on an impeller STL and return noise metrics."""
    stl = Path(stl).resolve()
    if not stl.exists():
        raise FileNotFoundError(stl)
    if dia_mm is None:
        import trimesh
        ext = trimesh.load(str(stl)).extents
        dia_mm = float(max(ext[0], ext[1]))     # assume axis = Z; diameter in the X-Y plane
    label = label or stl.stem
    out = (PROJECT / "build" / f"noise_{label}.csv").resolve()
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(f"stl={stl.as_posix()}\ndia_mm={dia_mm:.3f}\nout={out.as_posix()}\n")

    env = os.environ.copy()
    env["PATH"] = UCRT + os.pathsep + env.get("PATH", "")
    print(f"[noise] {label}: dia={dia_mm:.1f} mm  running LBM CV-noise (~3 min) ...", flush=True)
    # discard FluidX3D's large progress output (capturing it can deadlock the pipe); keep stderr
    r = subprocess.run([str(EXE)], cwd=str(FLUIDX3D), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=900)
    if not out.exists():
        sys.stderr.write((r.stderr or "")[-1500:] + "\n")
        raise RuntimeError(f"noise run produced no output for {label}")
    m = analyze_cv_force(out, cutoff_hz=cutoff_hz)
    m.update(label=label, dia_mm=round(dia_mm, 2), stl=str(stl))
    if not keep_csv:
        out.unlink(missing_ok=True)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stl")
    ap.add_argument("--cutoff", type=float, default=2500.0)
    ap.add_argument("--label", default=None)
    a = ap.parse_args()
    m = evaluate_noise(a.stl, label=a.label, cutoff_hz=a.cutoff)
    print(f"\n{'metric':<18}value")
    for k in ("label", "dia_mm", "thrust_n", "bpf_tone_db", "noise_dba_band", "noise_dba_full"):
        print(f"{k:<18}{m[k]}")
    print(f"\nnoise_dba_band = A-weighted on-axis dB(A)@1m, low-passed at {a.cutoff:.0f} Hz "
          f"(consistent band -> valid RELATIVE metric).")


if __name__ == "__main__":
    main()
