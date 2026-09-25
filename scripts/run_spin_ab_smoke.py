"""Free-air spin A/B smoke: which omega sign pumps positive outletFlow?

Reuses the Stock a12x25 recipe + ducted MRF case. Meshes once, then solves
free-air (0 Pa back) at spin=-1 and spin=+1 with the same mesh.

Usage:
    uv run python scripts/run_spin_ab_smoke.py
    uv run python scripts/run_spin_ab_smoke.py --base-cell 0.006 --iters 800 --procs 8
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.domain import rig_for_impeller  # noqa: E402
from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.geometry import build_impeller, export_stl  # noqa: E402
from fansim.geometry.blade import min_blade_wall_mm  # noqa: E402
from fansim.geometry.config import load_blade_params  # noqa: E402

DEFAULT_PARAMS = "config/problems/a12x25_reference.yaml"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Free-air spin A/B smoke (Stock a12x25)")
    ap.add_argument("--params", default=DEFAULT_PARAMS)
    ap.add_argument("--tip-gap-mm", type=float, default=0.5)
    ap.add_argument("--base-cell", type=float, default=0.006)
    ap.add_argument("--iters", type=int, default=800)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/spin_ab_smoke")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    params = load_blade_params(args.params)
    stl = out / "impeller.stl"
    if not stl.is_file():
        print(f"[geom] building {stl}", flush=True)
        export_stl(build_impeller(params), stl)

    base_rig = rig_for_impeller(params, tip_gap_mm=float(args.tip_gap_mm))
    min_wall = min_blade_wall_mm(params)
    mesh = MeshResolution.for_blade(float(args.base_cell), min_wall)
    print(
        f"[mesh] base_cell={args.base_cell} for_blade surf={mesh.surf_min}/{mesh.surf_max} "
        f"min_wall={min_wall:g} mm tip_gap={args.tip_gap_mm:g} mm",
        flush=True,
    )

    # Mesh once with default spin (MRF omega is rewritten per solve).
    runner = OpenFOAMRunner(out)
    build_case(
        out, stl, base_rig,
        mesh=mesh,
        n_iters=int(args.iters),
        n_subdomains=int(args.procs),
        back_pressure_pa=0.0,
    )
    t_mesh = time.time()
    run_mesh(runner)
    print(f"[mesh] done in {time.time() - t_mesh:.0f}s", flush=True)

    rows: list[dict] = []
    for spin in (-1, 1):
        rig = replace(base_rig, spin=int(spin))
        build_case(
            out, stl, rig,
            mesh=mesh,
            n_iters=int(args.iters),
            n_subdomains=int(args.procs),
            back_pressure_pa=0.0,
        )
        print(
            f"[solve] spin={spin:+d} omega_signed={rig.omega_signed:.4f} "
            f"u_axial={rig.u_axial:+.2f}",
            flush=True,
        )
        t0 = time.time()
        run_solve(runner, n_procs=int(args.procs))
        m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
        row = {
            "spin": int(spin),
            "omega_signed": rig.omega_signed,
            "u_axial": rig.u_axial,
            "cfm": m.cfm,
            "flow_m3s": m.flow_m3s,
            "static_pressure_rise_pa": m.static_pressure_rise_pa,
            "converged": m.converged,
            "drift_pct": round(m.flow_drift_pct, 2),
            "thrust_n": m.thrust_n,
            "torque_nm": m.torque_nm,
            "wall_s": round(time.time() - t0, 1),
        }
        rows.append(row)
        flag = "converged" if m.converged else f"UNCONVERGED {m.flow_drift_pct:.0f}%"
        print(
            f"  -> CFM={m.cfm:+.1f}  thrust_z={m.thrust_n:+.3f} N  "
            f"{flag}  ({row['wall_s']:.0f}s)",
            flush=True,
        )

    # Prefer the spin that delivers positive CFM; if both positive, prefer higher CFM.
    pos = [r for r in rows if r["cfm"] > 0]
    if pos:
        winner = max(pos, key=lambda r: r["cfm"])
        verdict = (
            f"spin={winner['spin']:+d} pumps +Z duct "
            f"({winner['cfm']:.1f} CFM); lock glyphs/domain to this sense"
        )
    else:
        winner = None
        verdict = "neither spin produced positive CFM — mesh/BC problem, not just sign"

    payload = {
        "params": args.params,
        "tip_gap_mm": float(args.tip_gap_mm),
        "base_cell": float(args.base_cell),
        "iters": int(args.iters),
        "mesh": asdict(mesh),
        "rows": rows,
        "preferred_spin": None if winner is None else winner["spin"],
        "verdict": verdict,
    }
    summary = out / "spin_ab_summary.json"
    summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n===== SPIN A/B =====\n  {verdict}\n-> {summary}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
