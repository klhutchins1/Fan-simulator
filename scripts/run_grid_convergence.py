# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Grid-convergence study: does the reported CFM stop changing as the mesh is refined?

The review's #2 non-negotiable — screening rankings are only meaningful if they are
resolution-stable. We solve ONE design at free delivery (the stable operating point) on a
sequence of successively finer meshes and report how much cfm_free still moves. If it keeps
drifting, the screening mesh is too coarse to trust even for ranking; if it flattens, we have
a mesh-independent value (and an error bar for the coarse screening mesh).

Usage:
    uv run python scripts/run_grid_convergence.py --base-json runs/opt_run1/pareto.json \
        --base-trial 2 --cells 0.007,0.005,0.0035 --iters 1000 --procs 8
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from fansim.cfd.domain import rig_for_impeller  # noqa: E402
from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.orientation import prepare_axial_cfd  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.geometry import build_impeller, export_stl  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402


def _cell_count(case_dir: Path) -> int:
    """Read the mesh cell count from the checkMesh log (best effort)."""
    log = case_dir / "logs" / "checkMesh.log"
    if not log.exists():
        return 0
    for line in log.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("cells:"):
            try:
                return int(s.split(":")[1])
            except (ValueError, IndexError):
                return 0
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="grid-convergence study (free delivery)")
    ap.add_argument("--base-json", required=True)
    ap.add_argument("--base-trial", type=int, required=True)
    ap.add_argument("--cells", default="0.007,0.005,0.0035",
                    help="base_cell sizes (m), coarse->fine")
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/gridconv")
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    pareto = json.loads(Path(args.base_json).read_text())
    row = next(r for r in pareto if r["trial"] == args.base_trial)
    params = blade_from_flat(row["params"])
    cells = [float(c) for c in args.cells.split(",")]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stl = export_stl(build_impeller(params), out / "impeller.stl")
    rig = rig_for_impeller(params, inlet_diameters=2.0, outlet_diameters=4.0)
    stl, rig = prepare_axial_cfd(stl, rig, out, source="builder")
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
        ncells = _cell_count(wd)
        rows.append({"base_cell": bc, "n_cells": ncells, "cfm_free": m.cfm,
                     "converged": m.converged})
        print(f"  base_cell={bc:.4f}  cells={ncells:>8}  cfm_free={m.cfm:6.1f}  "
              f"converged={m.converged}  ({time.time()-t:.0f}s)", flush=True)

    # Relative change between successive (finer) meshes = the grid-convergence signal.
    print("\n===== GRID CONVERGENCE =====")
    for a, b in zip(rows, rows[1:]):
        dp = abs(b["cfm_free"] - a["cfm_free"]) / (abs(a["cfm_free"]) + 1e-9) * 100
        print(f"  {a['base_cell']:.4f} -> {b['base_cell']:.4f}: "
              f"{a['cfm_free']:.1f} -> {b['cfm_free']:.1f} CFM  ({dp:.1f}% change)")
    if len(rows) >= 3:
        last = abs(rows[-1]["cfm_free"] - rows[-2]["cfm_free"]) / rows[-2]["cfm_free"] * 100
        verdict = ("GRID-INDEPENDENT" if last < 2.0
                   else "NOT grid-independent — finer mesh still changing the answer")
        print(f"  finest step: {last:.1f}% change => {verdict}")

    fig, ax = plt.subplots(figsize=(7, 5))
    xs = [r["n_cells"] or 1 / r["base_cell"] for r in rows]
    ax.plot(xs, [r["cfm_free"] for r in rows], "o-")
    ax.set_xlabel("mesh cells")
    ax.set_ylabel("cfm_free  [CFM]")
    ax.set_title(f"Grid convergence — trial {args.base_trial} (free delivery)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "gridconv.png", dpi=130)
    (out / "gridconv.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"-> {out/'gridconv.png'} , {out/'gridconv.json'}  (total {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
