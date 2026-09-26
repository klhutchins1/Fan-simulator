# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Grid convergence on a real impeller STL: does free-air CFM stop moving as the mesh refines?

Confirms whether the validated number (real A12x25 ≈ 57.6 CFM at base_cell 0.004) is
mesh-independent. Solves free delivery (back=0) at a sequence of base cell sizes and reports
the change between successive meshes.

Usage:
    uv run python scripts/grid_convergence_stl.py --stl build/a12x25_real_capped.stl \
        --cells 0.006,0.004,0.003 --iters 1500 --procs 8
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import trimesh  # noqa: E402

from fansim.cfd.domain import MM_TO_M, TestRig  # noqa: E402
from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.orientation import prepare_axial_cfd  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402

PUBLISHED_FREE_CFM = 60.1


def rig_from_stl(stl_path: Path, rpm: float, tip_gap_mm: float, spin: int,
                 inlet_d: float, outlet_d: float) -> TestRig:
    m = trimesh.load(str(stl_path), force="mesh")
    lo, hi = m.bounds
    tip_r_mm = float(np.max(np.linalg.norm(m.vertices[:, :2], axis=1)))
    duct_r = (tip_r_mm + tip_gap_mm) * MM_TO_M
    diameter = 2.0 * duct_r
    return TestRig(
        duct_radius=duct_r, tip_gap=tip_gap_mm * MM_TO_M,
        inlet_length=inlet_d * diameter, outlet_length=outlet_d * diameter,
        impeller_z_min=lo[2] * MM_TO_M, impeller_z_max=hi[2] * MM_TO_M,
        mrf_z_min=(lo[2] - 2.0) * MM_TO_M, mrf_z_max=(hi[2] + 2.0) * MM_TO_M,
        rpm=rpm, inlet_velocity=2.0, spin=spin,
    )


def _cells(case_dir: Path) -> int:
    log = case_dir / "logs" / "checkMesh.log"
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s.startswith("cells:"):
                try:
                    return int(s.split(":")[1])
                except (ValueError, IndexError):
                    return 0
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="grid convergence on an impeller STL")
    ap.add_argument("--stl", required=True)
    ap.add_argument("--rpm", type=float, default=2000.0)
    ap.add_argument("--cells", default="0.006,0.004,0.003")
    ap.add_argument("--iters", type=int, default=1500)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/gridconv_stl")
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    stl = Path(args.stl)
    cells = [float(c) for c in args.cells.split(",")]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rig = rig_from_stl(stl, args.rpm, 1.0, -1, 2.0, 4.0)
    stl, rig = prepare_axial_cfd(stl, rig, out)
    t0 = time.time()

    rows = []
    for bc in cells:
        wd = out / f"cell_{bc:g}"
        build_case(wd, stl, rig, mesh=MeshResolution(base_cell=bc), n_iters=args.iters,
                   n_subdomains=args.procs, back_pressure_pa=0.0)
        r = OpenFOAMRunner(wd)
        t = time.time()
        run_mesh(r)
        run_solve(r, n_procs=args.procs)
        m = parse_fan_metrics(wd, omega_rad_s=rig.omega_rad_s)
        rows.append({"base_cell": bc, "n_cells": _cells(wd), "cfm_free": m.cfm,
                     "converged": m.converged})
        print(f"  base_cell={bc:.4f}  cells={rows[-1]['n_cells']:>8}  "
              f"cfm_free={m.cfm:6.1f}  converged={m.converged}  ({time.time()-t:.0f}s)",
              flush=True)

    print("\n===== GRID CONVERGENCE (free delivery) =====")
    for a, b in zip(rows, rows[1:]):
        dp = abs(b["cfm_free"] - a["cfm_free"]) / (abs(a["cfm_free"]) + 1e-9) * 100
        print(f"  {a['base_cell']:.4f} -> {b['base_cell']:.4f}: "
              f"{a['cfm_free']:.1f} -> {b['cfm_free']:.1f} CFM  ({dp:.1f}% change)")
    if len(rows) >= 2:
        last = abs(rows[-1]["cfm_free"] - rows[-2]["cfm_free"]) / rows[-2]["cfm_free"] * 100
        print(f"  finest step: {last:.1f}% => "
              f"{'GRID-INDEPENDENT' if last < 3 else 'still moving — need finer'}")
        print(f"  finest cfm_free {rows[-1]['cfm_free']:.1f} vs published {PUBLISHED_FREE_CFM} "
              f"({(rows[-1]['cfm_free']/PUBLISHED_FREE_CFM - 1)*100:+.0f}%)")
    (out / "gridconv_stl.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"-> {out/'gridconv_stl.json'}  (total {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
