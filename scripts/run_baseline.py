"""Walking-skeleton entry point: one command, full pipeline.

    geometry (design vector) -> watertight STL -> OpenFOAM MRF case -> mesh -> solve
    -> CFM / static-pressure / torque / power -> metrics.json

Usage:
    uv run python scripts/run_baseline.py [--params config/design_space.yaml] [--random]
        [--out runs/baseline] [--iters 600] [--base-cell 0.004] [--skip-solve]
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
from fansim.cfd.openfoam_case import (  # noqa: E402
    MeshResolution, build_case, run_mesh, run_solve,
)
from fansim.cfd.orientation import prepare_axial_cfd  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.geometry import BladeParams, build_impeller, export_stl, watertight_report  # noqa: E402
from fansim.geometry.config import load_blade_params  # noqa: E402


def sample_random(base: BladeParams, seed: int | None) -> BladeParams:
    """Perturb the design vector for a random entry point (demo of --random mode)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    base.n_blades = int(rng.integers(5, 12))
    for st in base.stations:
        st.chord = float(np.clip(st.chord * rng.uniform(0.8, 1.2), 8.0, 30.0))
        st.stagger_deg = float(np.clip(st.stagger_deg + rng.uniform(-10, 10), 15.0, 70.0))
        st.sweep = float(st.sweep + rng.uniform(-3, 5))
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description="fansim walking-skeleton baseline run")
    ap.add_argument("--params", default="config/design_space.yaml")
    ap.add_argument("--random", action="store_true", help="perturb the design vector")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default="runs/baseline")
    ap.add_argument("--iters", type=int, default=600)
    ap.add_argument("--base-cell", type=float, default=0.004)
    ap.add_argument("--procs", type=int, default=8, help="MPI ranks for the solve")
    ap.add_argument("--inlet-velocity", type=float, default=2.0)
    ap.add_argument("--back-pressure", type=float, default=None,
                    help="Pa; if set, use pressure-driven BCs (CFM emerges from design)")
    ap.add_argument("--inlet-diameters", type=float, default=1.0)
    ap.add_argument("--outlet-diameters", type=float, default=1.5)
    ap.add_argument("--skip-solve", action="store_true", help="mesh only, no simpleFoam")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    if not image_available():
        print("ERROR: OpenFOAM Docker image not found (opencfd/openfoam-default:2406).")
        return 2

    # 1. Geometry -------------------------------------------------------------
    params = load_blade_params(args.params)
    if args.random:
        params = sample_random(params, args.seed)
    print(f"[geometry] {params.n_blades} blades, "
          f"staggers {[round(s.stagger_deg, 1) for s in params.stations]}")
    impeller = build_impeller(params)
    stl = export_stl(impeller, out / "impeller.stl")
    rep = watertight_report(stl)
    if not rep.ok:
        print(f"ERROR: impeller not mesh-ready: {rep}")
        return 3
    print(f"[geometry] watertight OK, {rep.n_faces} faces, "
          f"vol {rep.volume_mm3:.0f} mm^3 -> {stl}")

    # 2. CFD case + mesh ------------------------------------------------------
    rig = rig_for_impeller(
        params,
        inlet_diameters=args.inlet_diameters,
        outlet_diameters=args.outlet_diameters,
        inlet_velocity=args.inlet_velocity,
    )
    stl, rig = prepare_axial_cfd(stl, rig, out, source="builder")
    build_case(out, stl, rig, mesh=MeshResolution(base_cell=args.base_cell),
               n_iters=args.iters, n_subdomains=args.procs,
               back_pressure_pa=args.back_pressure)
    runner = OpenFOAMRunner(out)
    print(f"[cfd] omega={rig.omega_rad_s:.1f} rad/s, "
          f"tip speed {rig.tip_speed:.1f} m/s, duct r {rig.duct_radius*1e3:.1f} mm")

    t = time.time()
    run_mesh(runner)
    print(f"[mesh] pipeline {time.time()-t:.0f}s")

    if args.skip_solve:
        print(f"[done] mesh only in {time.time()-t_start:.0f}s")
        return 0

    # 3. Solve ----------------------------------------------------------------
    t = time.time()
    run_solve(runner, n_procs=args.procs)
    print(f"[solve] simpleFoam ({args.procs} procs) {time.time()-t:.0f}s")

    # 4. Metrics --------------------------------------------------------------
    metrics = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
    payload = {
        "design": {"n_blades": params.n_blades,
                   "stations": [vars(s) for s in params.stations]},
        "operating_point": {"inlet_velocity_ms": rig.inlet_velocity,
                            "rpm": rig.rpm, "omega_rad_s": rig.omega_rad_s},
        "metrics": metrics.to_dict(),
        "runtime_s": round(time.time() - t_start, 1),
    }
    (out / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    m = metrics
    print("\n===== FAN METRICS =====")
    print(f"  CFM (outlet)          : {m.cfm:8.1f} ft^3/min")
    print(f"  static pressure rise  : {m.static_pressure_rise_pa:8.2f} Pa")
    print(f"  torque                : {m.torque_nm*1e3:8.2f} mN.m")
    print(f"  shaft power           : {m.shaft_power_w:8.2f} W")
    print(f"  axial thrust          : {m.thrust_n:8.3f} N")
    print(f"  aero efficiency       : {m.efficiency*100:8.1f} %")
    print(f"  -> {out/'metrics.json'}  (total {payload['runtime_s']:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)  # skip OCP/VTK atexit teardown (harmless shutdown segfault)
