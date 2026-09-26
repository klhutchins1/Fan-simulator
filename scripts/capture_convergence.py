# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Capture and plot the flow-convergence trajectory of one design at several back-pressures.

Shows whether the steady solve settles (free delivery, stable branch) or wanders/oscillates
(near-stall load point) — the smoking gun for why the load objective is non-reproducible.

Usage:
    uv run python scripts/capture_convergence.py --base-json runs/opt_run1/pareto.json \
        --base-trial 2 --backs 0,1,2 --iters 2000 --base-cell 0.005
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
from fansim.cfd.metrics import (  # noqa: E402
    CFM_PER_M3S,
    _flow_trajectory,
    convergence,
    oscillation_pct,
)
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.orientation import prepare_axial_cfd  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.geometry import build_impeller, export_stl  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="convergence-trajectory capture")
    ap.add_argument("--base-json", required=True)
    ap.add_argument("--base-trial", type=int, required=True)
    ap.add_argument("--backs", default="0,1,2", help="back-pressures (Pa) to test")
    ap.add_argument("--iters", type=int, default=2000)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/convergence")
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    pareto = json.loads(Path(args.base_json).read_text())
    row = next(r for r in pareto if r["trial"] == args.base_trial)
    params = blade_from_flat(row["params"])
    backs = [float(b) for b in args.backs.split(",")]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stl = export_stl(build_impeller(params), out / "impeller.stl")
    rig = rig_for_impeller(params)
    stl, rig = prepare_axial_cfd(stl, rig, out)
    runner = OpenFOAMRunner(out)
    t0 = time.time()

    build_case(out, stl, rig, mesh=MeshResolution(base_cell=args.base_cell),
               n_iters=args.iters, n_subdomains=args.procs, back_pressure_pa=backs[0])
    run_mesh(runner)
    print(f"[mesh] {time.time()-t0:.0f}s", flush=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    summary = []
    for b in backs:
        build_case(out, stl, rig, mesh=MeshResolution(base_cell=args.base_cell),
                   n_iters=args.iters, n_subdomains=args.procs, back_pressure_pa=b)
        t = time.time()
        run_solve(runner, n_procs=args.procs)
        traj = _flow_trajectory(out)
        conv, drift = convergence(out)
        osc = oscillation_pct(out)
        its = [p[0] for p in traj]
        cfm = [p[1] * CFM_PER_M3S for p in traj]
        ax.plot(its, cfm, marker="o", ms=3, label=f"{b:g} Pa  (final {cfm[-1]:.0f} CFM, "
                f"{'converged' if conv else 'SHIFT %.0f%%' % drift}, osc {osc:.0f}%)")
        summary.append({"back_pa": b, "final_cfm": cfm[-1], "converged": conv,
                        "drift_pct": drift, "oscillation_pct": osc})
        print(f"[back={b:g}Pa] final {cfm[-1]:.1f} CFM  "
              f"{'converged' if conv else 'SHIFT %.1f%%' % drift}  osc={osc:.1f}%"
              f"  ({time.time()-t:.0f}s)",
              flush=True)

    ax.set_xlabel("SIMPLE iteration")
    ax.set_ylabel("Outlet flow  [CFM]")
    ax.set_title(f"Convergence trajectory — trial {args.base_trial} (nB={params.n_blades})")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "convergence.png", dpi=130)
    (out / "convergence.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"-> {out/'convergence.png'} , {out/'convergence.json'}  (total {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
