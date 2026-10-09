"""Validate CFD against a REAL impeller STL (e.g. the actual A12x25 geometry).

Meshes an arbitrary watertight impeller STL (axis on Z, centered — see the --prep note),
sizes the duct/MRF rig from the STL's own bounds, runs the free-delivery point (and optional
back-pressures), and compares to the published NF-A12x25 numbers. This is the honest
validation the parametric approximation could not give.

Usage:
    uv run python scripts/validate_stl.py --stl build/a12x25_real_z.stl \
        --rpm 2000 --backs 0 --iters 1200 --base-cell 0.004 --procs 8
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

PUB_FREE_AIR_CFM = 60.1
PUB_SHUTOFF_PA = 22.9


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


def main() -> int:
    ap = argparse.ArgumentParser(description="validate CFD against a real impeller STL")
    ap.add_argument("--stl", required=True, help="watertight impeller STL, axis Z, centered")
    ap.add_argument("--rpm", type=float, default=2000.0)
    ap.add_argument("--backs", default="0", help="back-pressures (Pa) to solve")
    ap.add_argument(
        "--spin", type=int, default=-1,
        help="explicit MRF rotation sign override about +z (default -1, matches "
             "fansim.cfd.orientation.AXIAL_CFD_ORIENTATION); only override this after checking "
             "the orientation/handedness audit, not to chase a sign",
    )
    ap.add_argument("--tip-gap-mm", type=float, default=1.0)
    ap.add_argument("--iters", type=int, default=1200)
    ap.add_argument("--base-cell", type=float, default=0.004)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/validate_real")
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    stl = Path(args.stl)
    backs = [float(b) for b in args.backs.split(",")]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rig = rig_from_stl(stl, args.rpm, args.tip_gap_mm, args.spin, 2.0, 4.0)
    stl, rig = prepare_axial_cfd(stl, rig, out, source="external")
    runner = OpenFOAMRunner(out)
    t0 = time.time()
    print(f"real STL: tip r {rig.duct_radius*1e3-args.tip_gap_mm:.1f} mm, "
          f"axial z[{rig.impeller_z_min*1e3:.1f},{rig.impeller_z_max*1e3:.1f}] mm, "
          f"omega {rig.omega_signed:.0f} rad/s")

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
                     "oscillation_pct": round(m.oscillation_pct, 1),
                     "eff": round(m.efficiency, 1)})
        print(f"  back={b:5.1f} Pa -> {m.cfm:7.1f} CFM  eff {m.efficiency:4.1f}%  "
              f"{'converged' if m.converged else 'UNCONVERGED %.0f%% shift' % m.flow_drift_pct}"
              f" osc={m.oscillation_pct:.0f}%"
              f"  ({time.time()-t:.0f}s)", flush=True)

    free = next((r["cfm"] for r in rows if r["back_pa"] == 0.0), None)
    print("\n===== REAL A12x25 STL vs published =====")
    print(f"  published free-air: {PUB_FREE_AIR_CFM} CFM")
    if free is not None:
        if free < 0:
            print(f"  sim free-air {free:.1f} CFM is NEGATIVE -> flow reversed; this is an "
                  f"orientation/handedness question, not a --spin knob to flip until it looks "
                  f"right -- check fansim/cfd/orientation.py (AXIAL_CFD_ORIENTATION) and the "
                  f"docs/validation/audits/ direction audit before rerunning.")
        else:
            ratio = free / PUB_FREE_AIR_CFM
            print(f"  sim free-air: {free:.1f} CFM => {ratio:.2f}x published ({(ratio-1)*100:+.0f}%)")
    (out / "validate_real.json").write_text(
        json.dumps({"rows": rows, "published_free_cfm": PUB_FREE_AIR_CFM}, indent=2),
        encoding="utf-8")
    print(f"-> {out/'validate_real.json'}  (total {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
