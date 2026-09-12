"""GPU LBM shut-off (dead-head) static pressure via FluidX3D.

Runs the sealed-chamber FluidX3D case (``mode=shutoff`` in the job cfg) on an
impeller STL and reduces the logged ΔP history to a *settled* shut-off pressure.
Steady RANS under-reads near stall (~13 Pa); the transient LBM previously settled
near ~21 Pa vs published 22.9 Pa (see ``docs/fluidx3d-setup.md``).

Usage:
  uv run python scripts/evaluate_shutoff.py [impeller.stl]
  uv run python scripts/evaluate_shutoff.py --tip-clear-mm 2.7   # published-Pa match
  uv run python scripts/evaluate_shutoff.py --csv build/shutoff_a12x25.csv
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cfd.lbm_shutoff import PUBLISHED_SHUTOFF_PA, settle_shutoff  # noqa: E402

FLUIDX3D = Path("E:/Projects/programming_2/FluidX3D")
EXE = FLUIDX3D / "bin" / "FluidX3D.exe"
UCRT = r"C:\msys64\ucrt64\bin"
CFG = PROJECT / "build" / "noise_job.cfg"  # shared job cfg; mode=shutoff selects the case
DEFAULT_STL = PROJECT / "build" / "a12x25_real_capped.stl"


def _write_job_cfg(
    stl: Path,
    dia_mm: float,
    out: Path,
    *,
    steps: int = 48000,
    re: float = 8000.0,
    tip_clear_mm: float = 1.0,
) -> None:
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(
        f"stl={stl.as_posix()}\ndia_mm={dia_mm:.3f}\nout={out.as_posix()}\n"
        f"mode=shutoff\nsteps={steps}\nre={re:.1f}\ntip_clear_mm={tip_clear_mm:.3f}\n",
        encoding="utf-8",
    )


def evaluate_shutoff(
    stl: str | Path | None = None,
    *,
    dia_mm: float | None = None,
    label: str | None = None,
    steps: int = 48000,
    re: float = 8000.0,
    tip_clear_mm: float = 1.0,
    keep_csv: bool = True,
    out_dir: Path | None = None,
) -> dict:
    """Run FluidX3D shut-off on an impeller STL and return settled metrics."""
    stl_path = Path(stl).resolve() if stl else DEFAULT_STL.resolve()
    if not stl_path.exists():
        raise FileNotFoundError(stl_path)
    if not EXE.exists():
        raise FileNotFoundError(f"FluidX3D exe missing: {EXE}")
    if dia_mm is None:
        import trimesh

        ext = trimesh.load(str(stl_path)).extents
        dia_mm = float(max(ext[0], ext[1]))
    label = label or stl_path.stem
    out_root = Path(out_dir) if out_dir else (PROJECT / "runs" / "campaign_lbm_shutoff")
    out_root.mkdir(parents=True, exist_ok=True)
    out = (out_root / f"shutoff_{label}.csv").resolve()
    _write_job_cfg(
        stl_path, float(dia_mm), out, steps=steps, re=re, tip_clear_mm=tip_clear_mm
    )

    env = os.environ.copy()
    env["PATH"] = UCRT + os.pathsep + env.get("PATH", "")
    print(
        f"[shutoff] {label}: dia={dia_mm:.1f} mm  Re={re:.0f}  tip_clear={tip_clear_mm:.2f} mm"
        f"  steps={steps}  running LBM ...",
        flush=True,
    )
    # DEVNULL stdout — capturing FluidX3D progress deadlocks the pipe (same as noise).
    r = subprocess.run(
        [str(EXE)],
        cwd=str(FLUIDX3D),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=max(900, steps // 10),
    )
    if not out.exists():
        sys.stderr.write((r.stderr or "")[-2000:] + "\n")
        raise RuntimeError(f"shut-off run produced no CSV for {label}")
    m = settle_shutoff(out)
    m.update(
        label=label,
        dia_mm=round(float(dia_mm), 2),
        stl=str(stl_path),
        steps=steps,
        re=float(re),
        tip_clear_mm=float(tip_clear_mm),
        published_pa=PUBLISHED_SHUTOFF_PA,
    )
    report_path = out_root / f"shutoff_{label}.json"
    report_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
    m["report"] = str(report_path.resolve())
    if not keep_csv:
        out.unlink(missing_ok=True)
    return m


def main() -> None:
    ap = argparse.ArgumentParser(description="FluidX3D LBM shut-off (dead-head) ΔP")
    ap.add_argument("stl", nargs="?", default=None, help="impeller STL (default: A12x25 capped)")
    ap.add_argument("--csv", default=None, help="existing shut-off CSV; skip the LBM run")
    ap.add_argument("--label", default=None)
    ap.add_argument("--dia-mm", type=float, default=None)
    ap.add_argument("--steps", type=int, default=48000)
    ap.add_argument("--re", type=float, default=8000.0, help="LBM Reynolds (default 8000)")
    ap.add_argument(
        "--tip-clear-mm",
        type=float,
        default=1.0,
        help="radial tip clearance in mm/cells (default 1.0)",
    )
    ap.add_argument("--out-dir", default=None, help="CSV/JSON folder (default runs/campaign_lbm_shutoff)")
    a = ap.parse_args()
    if a.csv:
        m = settle_shutoff(a.csv)
        m.setdefault("label", a.label or Path(a.csv).stem)
    else:
        m = evaluate_shutoff(
            a.stl,
            dia_mm=a.dia_mm,
            label=a.label,
            steps=a.steps,
            re=a.re,
            tip_clear_mm=a.tip_clear_mm,
            out_dir=Path(a.out_dir) if a.out_dir else None,
        )
    print(f"\n{'metric':<22}value")
    for k in (
        "label",
        "shut_off_pa",
        "shut_off_pa_std",
        "peak_pa",
        "residual_cfm",
        "re",
        "tip_clear_mm",
        "target_pa",
        "error_pct",
        "n_settle",
        "csv",
        "report",
    ):
        if k in m and m[k] is not None:
            print(f"{k:<22}{m[k]}")
    print(
        f"\nSettled shut-off vs published {PUBLISHED_SHUTOFF_PA} Pa "
        f"(do not use peak_pa — fill transient overshoots)."
    )


if __name__ == "__main__":
    main()
