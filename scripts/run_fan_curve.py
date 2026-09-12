# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Trace a fan's P-Q characteristic by sweeping the operating point.

Meshes the impeller once, then solves at a range of inlet velocities (each a point on the
pressure-flow curve). Writes fan_curve.csv + fan_curve.png and estimates the free-delivery
flow (static-pressure = 0 crossing) and shut-off pressure.

Usage:
    uv run python scripts/run_fan_curve.py [--params config/design_space.yaml]
        [--out runs/fan_curve] [--velocities 0.25,0.5,1,1.5,2,3] [--iters 500] [--procs 8]
"""

from __future__ import annotations

import argparse
import csv
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
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.geometry import build_impeller, export_stl  # noqa: E402
from fansim.geometry.config import load_blade_params  # noqa: E402


def free_delivery_cfm(points: list[dict]) -> float | None:
    """Interpolate the CFM where static pressure crosses zero (free delivery)."""
    pts = sorted(points, key=lambda p: p["cfm"])
    for a, b in zip(pts, pts[1:]):
        pa, pb = a["static_pa"], b["static_pa"]
        if pa == 0:
            return a["cfm"]
        if (pa > 0) != (pb > 0):  # sign change brackets the crossing
            f = pa / (pa - pb)
            return a["cfm"] + f * (b["cfm"] - a["cfm"])
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="fansim P-Q fan-curve sweep")
    ap.add_argument("--params", default="config/design_space.yaml")
    ap.add_argument("--out", default="runs/fan_curve")
    ap.add_argument("--velocities", default="0.25,0.5,1.0,1.5,2.0,3.0")
    ap.add_argument("--iters", type=int, default=500)
    ap.add_argument("--base-cell", type=float, default=0.004)
    ap.add_argument("--procs", type=int, default=8)
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    velocities = [float(v) for v in args.velocities.split(",")]

    params = load_blade_params(args.params)
    stl = export_stl(build_impeller(params), out / "impeller.stl")
    runner = OpenFOAMRunner(out)

    # Mesh once at the first operating point's geometry.
    rig0 = rig_for_impeller(params, inlet_diameters=1.0, outlet_diameters=1.5,
                            inlet_velocity=velocities[0])
    build_case(out, stl, rig0, mesh=MeshResolution(base_cell=args.base_cell),
               n_iters=args.iters, n_subdomains=args.procs)
    t = time.time()
    run_mesh(runner)
    print(f"[mesh] once, {time.time()-t:.0f}s")

    points: list[dict] = []
    for v in velocities:
        rig = rig_for_impeller(params, inlet_diameters=1.0, outlet_diameters=1.5,
                               inlet_velocity=v)
        # Rewrite 0/ + dicts for this operating point (keeps constant/polyMesh).
        build_case(out, stl, rig, mesh=MeshResolution(base_cell=args.base_cell),
                   n_iters=args.iters, n_subdomains=args.procs)
        t = time.time()
        run_solve(runner, n_procs=args.procs)
        m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
        row = {"inlet_v": v, "cfm": m.cfm, "static_pa": m.static_pressure_rise_pa,
               "power_w": m.shaft_power_w, "torque_mnm": m.torque_nm * 1e3,
               "efficiency_pct": m.efficiency * 100.0}
        points.append(row)
        print(f"[point] v={v:4.2f}  Q={m.cfm:6.1f} CFM  dP={m.static_pressure_rise_pa:7.2f} Pa"
              f"  P={m.shaft_power_w:5.2f} W  ({time.time()-t:.0f}s)")

    # CSV
    with open(out / "fan_curve.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(points[0].keys()))
        w.writeheader()
        w.writerows(points)

    # Plot
    pts = sorted(points, key=lambda p: p["cfm"])
    q = [p["cfm"] for p in pts]
    dp = [p["static_pa"] for p in pts]
    pw = [p["power_w"] for p in pts]
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(q, dp, "o-", color="tab:blue", label="static pressure")
    ax1.axhline(0, color="gray", lw=0.8, ls="--")
    ax1.set_xlabel("Flow  Q  [CFM]")
    ax1.set_ylabel("Static pressure rise  [Pa]", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax2 = ax1.twinx()
    ax2.plot(q, pw, "s--", color="tab:red", label="shaft power")
    ax2.set_ylabel("Shaft power  [W]", color="tab:red")
    ax2.tick_params(axis="y", labelcolor="tab:red")
    fd = free_delivery_cfm(points)
    title = "Fan P-Q curve"
    if fd is not None:
        title += f"  (free delivery ~ {fd:.0f} CFM)"
        ax1.axvline(fd, color="green", lw=0.8, ls=":")
    ax1.set_title(title)
    fig.tight_layout()
    fig.savefig(out / "fan_curve.png", dpi=130)

    print("\n===== FAN CURVE =====")
    for p in pts:
        print(f"  {p['cfm']:6.1f} CFM   {p['static_pa']:7.2f} Pa   {p['power_w']:5.2f} W")
    if fd is not None:
        print(f"  free delivery ~ {fd:.1f} CFM;  shut-off dP ~ {max(dp):.1f} Pa")
    print(f"  -> {out/'fan_curve.csv'} , {out/'fan_curve.png'}")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
