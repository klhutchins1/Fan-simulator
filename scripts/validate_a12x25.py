# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Validate the CFD against the published NF-A12x25 curve (review §6.1).

Runs the A12x25 approximation across a back-pressure sweep (which IS the fan's static
pressure), builds the P-Q curve on the stable branch, and compares to the manufacturer
points: free-air 60.1 CFM @ 0 Pa and shut-off 0 CFM @ 22.9 Pa. The gap between our idealized
sim and the published numbers is the idealization+geometry error budget we must close before
any absolute claim. Points near shut-off (deep stall) will flag unconverged — expected.

Usage:
    Prefer Phase 3 entry: ``scripts/run_a12x25_validation.py`` (defaults to reference stock).

    uv run python scripts/validate_a12x25.py --params config/problems/a12x25.yaml \
        --backs 0,5,10,15,20 --iters 1000 --base-cell 0.005 --procs 8
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
from fansim.geometry.config import load_blade_params  # noqa: E402

# Published NF-A12x25 PWM (docs/a12x25-reference.md).
PUB_FREE_AIR_CFM = 60.1
PUB_SHUTOFF_PA = 22.9


def main() -> int:
    ap = argparse.ArgumentParser(description="A12x25 CFD validation")
    ap.add_argument("--params", default="config/problems/a12x25.yaml")
    ap.add_argument("--backs", default="0,5,10,15,20")
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/validate_a12x25")
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    params = load_blade_params(args.params)
    backs = [float(b) for b in args.backs.split(",")]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stl = export_stl(build_impeller(params), out / "impeller.stl")
    rig = rig_for_impeller(params, inlet_diameters=2.0, outlet_diameters=4.0)
    stl, rig = prepare_axial_cfd(stl, rig, out, source="builder")
    runner = OpenFOAMRunner(out)
    t0 = time.time()

    build_case(out, stl, rig, mesh=MeshResolution(base_cell=args.base_cell),
               n_iters=args.iters, n_subdomains=args.procs, back_pressure_pa=backs[0])
    run_mesh(runner)
    print(f"[mesh] {time.time()-t0:.0f}s", flush=True)

    rows = []
    for b in backs:
        build_case(out, stl, rig, mesh=MeshResolution(base_cell=args.base_cell),
                   n_iters=args.iters, n_subdomains=args.procs, back_pressure_pa=b)
        t = time.time()
        run_solve(runner, n_procs=args.procs)
        m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
        rows.append({"back_pa": b, "cfm": m.cfm, "converged": m.converged,
                     "drift_pct": round(m.flow_drift_pct, 1),
                     "oscillation_pct": round(m.oscillation_pct, 1)})
        print(f"  back={b:5.1f} Pa -> {m.cfm:6.1f} CFM  "
              f"{'converged' if m.converged else 'UNCONVERGED %.0f%% shift' % m.flow_drift_pct}"
              f" osc={m.oscillation_pct:.0f}%"
              f"  ({time.time()-t:.0f}s)", flush=True)

    free_air = next((r["cfm"] for r in rows if r["back_pa"] == 0.0), None)

    print("\n===== VALIDATION vs published NF-A12x25 =====")
    print(f"  published free-air: {PUB_FREE_AIR_CFM} CFM ; shut-off: {PUB_SHUTOFF_PA} Pa")
    if free_air is not None:
        ratio = free_air / PUB_FREE_AIR_CFM
        print(f"  sim free-air (0 Pa): {free_air:.1f} CFM  "
              f"=> {ratio:.2f}x published ({(ratio-1)*100:+.0f}%)")
        print("  (>1 = over-prediction, expected from slip walls / no frame struts / "
              "unresolved tip gap; the validation task is to shrink this toward 1.0.)")

    fig, ax = plt.subplots(figsize=(7.5, 5))
    conv = [r for r in rows if r["converged"]]
    unconv = [r for r in rows if not r["converged"]]
    if conv:
        ax.plot([r["cfm"] for r in conv], [r["back_pa"] for r in conv], "o-",
                color="tab:blue", label="sim (converged)")
    if unconv:
        ax.scatter([r["cfm"] for r in unconv], [r["back_pa"] for r in unconv],
                   facecolors="none", edgecolors="gray", label="sim (unconverged, near stall)")
    ax.scatter([PUB_FREE_AIR_CFM, 0.0], [0.0, PUB_SHUTOFF_PA], color="crimson", s=80,
               marker="*", zorder=5, label="published A12x25")
    ax.set_xlabel("Flow  [CFM]")
    ax.set_ylabel("Static pressure / back-pressure  [Pa]")
    ax.set_title("A12x25 validation: sim vs published")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "validation.png", dpi=130)
    (out / "validation.json").write_text(
        json.dumps({"rows": rows, "published": {"free_air_cfm": PUB_FREE_AIR_CFM,
                    "shutoff_pa": PUB_SHUTOFF_PA}}, indent=2), encoding="utf-8")
    print(f"-> {out/'validation.png'} , {out/'validation.json'}  (total {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
