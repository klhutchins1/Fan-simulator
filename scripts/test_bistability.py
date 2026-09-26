# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Probe whether the steady CFD has multiple solution branches (bistability).

The adversarial review's central suspicion: the bimodal ~49-vs-~60 CFM-load results are a
steady-RANS solution-branch artifact, not aerodynamics. Test it directly: take ONE fixed
design + mesh + operating point, and solve it repeatedly from different initial velocity
fields. If the converged flow depends on the initial guess, the solve is bistable/path-
dependent and every ranking built on it is suspect. Optionally repeat at a finer mesh to see
whether refinement removes the ambiguity.

Usage:
    uv run python scripts/test_bistability.py --base-json runs/opt_run1/pareto.json \
        --base-trial 2 --back-pressure 2 --guesses 0.5,2.5,4.5 --iters 1200 --procs 8
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.domain import rig_for_impeller  # noqa: E402
from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.orientation import prepare_axial_cfd  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.geometry import build_impeller, export_stl  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402


def run_branch_scan(params, out: Path, back_pa: float, guesses, base_cell: float,
                    iters: int, procs: int) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    stl = export_stl(build_impeller(params), out / "impeller.stl")
    rig = rig_for_impeller(params)
    stl, rig = prepare_axial_cfd(stl, rig, out)
    runner = OpenFOAMRunner(out)
    # Mesh once; all solves share this mesh so only the initial field differs.
    build_case(out, stl, rig, mesh=MeshResolution(base_cell=base_cell), n_iters=iters,
               n_subdomains=procs, back_pressure_pa=back_pa, u_guess=guesses[0])
    t = time.time()
    run_mesh(runner)
    print(f"  [mesh @ base_cell={base_cell}] {time.time()-t:.0f}s", flush=True)

    rows = []
    for g in guesses:
        build_case(out, stl, rig, mesh=MeshResolution(base_cell=base_cell), n_iters=iters,
                   n_subdomains=procs, back_pressure_pa=back_pa, u_guess=g)
        t = time.time()
        run_solve(runner, n_procs=procs)
        m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
        rows.append({"u_guess": g, "cfm_load": m.cfm, "static_pa": m.static_pressure_rise_pa,
                     "eff": m.efficiency * 100})
        print(f"  u_guess={g:4.1f} m/s -> cfm_load={m.cfm:6.1f}  static={m.static_pressure_rise_pa:6.1f}Pa"
              f"  eff={m.efficiency*100:5.1f}%  ({time.time()-t:.0f}s)", flush=True)
    return rows


def verdict(rows: list[dict]) -> str:
    loads = [r["cfm_load"] for r in rows]
    spread = max(loads) - min(loads)
    rel = spread / (sum(loads) / len(loads) + 1e-9) * 100
    if rel > 8.0:
        return (f"BISTABLE / path-dependent: cfm_load spans {min(loads):.1f}–{max(loads):.1f} "
                f"({rel:.0f}% spread) from initial condition alone. Rankings are UNRELIABLE.")
    return (f"STABLE: cfm_load {min(loads):.1f}–{max(loads):.1f} ({rel:.1f}% spread) — "
            f"insensitive to initial condition at this mesh.")


def main() -> int:
    ap = argparse.ArgumentParser(description="steady-RANS bistability probe")
    ap.add_argument("--base-json", required=True)
    ap.add_argument("--base-trial", type=int, required=True)
    ap.add_argument("--out", default="runs/bistability")
    ap.add_argument("--back-pressure", type=float, default=2.0)
    ap.add_argument("--guesses", default="0.5,2.5,4.5")
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--refine-cell", type=float, default=None,
                    help="optional finer base_cell to repeat the scan and check convergence")
    ap.add_argument("--iters", type=int, default=1200)
    ap.add_argument("--procs", type=int, default=8)
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    pareto = json.loads(Path(args.base_json).read_text())
    row = next(r for r in pareto if r["trial"] == args.base_trial)
    params = blade_from_flat(row["params"])
    guesses = [float(g) for g in args.guesses.split(",")]
    out = Path(args.out)
    t0 = time.time()

    print(f"Bistability probe: trial {args.base_trial} (nB={params.n_blades}), "
          f"back-pressure {args.back_pressure} Pa, initial guesses {guesses} m/s")
    print(f"[coarse mesh base_cell={args.base_cell}]")
    coarse = run_branch_scan(params, out / "coarse", args.back_pressure, guesses,
                             args.base_cell, args.iters, args.procs)
    results = {"coarse": {"base_cell": args.base_cell, "rows": coarse,
                          "verdict": verdict(coarse)}}
    print("  => " + results["coarse"]["verdict"])

    if args.refine_cell:
        print(f"[refined mesh base_cell={args.refine_cell}]")
        fine = run_branch_scan(params, out / "fine", args.back_pressure, guesses,
                               args.refine_cell, args.iters, args.procs)
        results["fine"] = {"base_cell": args.refine_cell, "rows": fine,
                           "verdict": verdict(fine)}
        print("  => " + results["fine"]["verdict"])

    (out / "bistability.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n-> {out/'bistability.json'}  (total {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
