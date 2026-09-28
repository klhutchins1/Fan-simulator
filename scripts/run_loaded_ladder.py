"""Loaded-branch diagnostic ladder runner (roadmap 19.6, Task 3).

Tests one lever at a time to find where the A12x25 CFD collapses under
back-pressure: a plenum-only case, a plenum+frame case, and a frozen-rotor
URANS overlay on top of that. Each rung meshes once and solves the requested
back-pressure points, writing ``docs/validation/loaded_ladder/<rung>.json``
after EVERY point so a killed run still leaves a usable partial result.

Do NOT run this against real CFD from an automated agent without explicit
sign-off -- it launches Docker/OpenFOAM. Use ``--help`` to inspect wiring only.

Usage:
    uv run python scripts/run_loaded_ladder.py --rung plenum --points 0,5,10,15 \\
        --procs 16 --iters 1000 --base-cell 0.005
    uv run python scripts/run_loaded_ladder.py --rung urans --points 0,10,20 \\
        --revs 10 --procs 16
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import trimesh  # noqa: E402

from fansim.cfd.casing import export_casing_stl  # noqa: E402
from fansim.cfd.domain import MM_TO_M  # noqa: E402
from fansim.cfd.frame import export_frame_stl  # noqa: E402
from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import (  # noqa: E402
    apply_urans_transient,
    build_case,
    run_mesh,
    run_solve,
    run_solve_urans,
)
from fansim.cfd.orientation import prepare_axial_cfd  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.cfd.sanity import overall as sanity_overall, run_sanity  # noqa: E402
from fansim.cfd.timing import (  # noqa: E402
    estimate_urans_wall_s,
    mesh_cells,
    pilot_iters,
    write_pilot_json,
)
from fansim.geometry.blade import min_blade_wall_mm  # noqa: E402
from fansim.geometry.config import load_blade_params  # noqa: E402
from fansim.validation.loaded_ladder import (  # noqa: E402
    PUB_FREE_AIR_CFM,
    PUB_SHUTOFF_PA,
    ladder_verdict,
)

# Re-use the shared helpers from the A12x25 validation script rather than
# duplicating mesh-resolution / STL-resolution / rig-construction logic.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_a12x25_validation import (  # noqa: E402
    DEFAULT_PARAMS,
    _mesh,
    _resolve_impeller_stl,
    _rig_for_case,
)

RUNGS = ("plenum", "frame", "urans")
DEFAULT_POINTS = "0,5,10,15"

CFD_VERSION = "loaded_ladder_v1"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Loaded-branch diagnostic ladder: plenum / frame / urans rungs, "
                    "one lever at a time, against published NF-A12x25 P-Q.")
    ap.add_argument("--rung", choices=RUNGS, required=True,
                    help="which ladder rung to run")
    ap.add_argument("--params", default=DEFAULT_PARAMS,
                    help="blade recipe YAML (default: cockpit reference stock)")
    ap.add_argument("--points", default=DEFAULT_POINTS,
                    help="back-pressure sweep [Pa], comma-separated")
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--iters", type=int, default=1000,
                    help="steady iterations (plenum/frame rungs)")
    ap.add_argument("--revs", type=float, default=10,
                    help="rotor revolutions for the URANS end time (urans rung)")
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--tip-gap-mm", type=float, default=0.5)
    ap.add_argument("--box-scale", type=float, default=3.0)
    ap.add_argument("--delta-t", type=float, default=1e-5,
                    help="URANS initial/base time step (urans rung)")
    ap.add_argument("--max-co", type=float, default=1.5,
                    help="URANS adjustable-timestep max Courant number (urans rung)")
    ap.add_argument("--out", default="runs/loaded_ladder")
    ap.add_argument("--pilot", action="store_true",
                    help="mesh once, solve ONE point at max(50, iters//10) iterations "
                         "(or a short URANS sample), print/write <out>/<rung>/pilot.json "
                         "with the estimated full-run time, then exit")
    return ap


def _plenum_z_mm(rig: Any) -> float:
    """Downstream plenum cut plane: half a duct diameter past the impeller."""
    duct_radius_mm = rig.duct_radius / MM_TO_M
    return rig.impeller_z_max / MM_TO_M + 0.5 * (2 * duct_radius_mm)


def _fill_radius_mm(rig: Any, box_scale: float) -> float:
    duct_radius_mm = rig.duct_radius / MM_TO_M
    return box_scale * duct_radius_mm * math.sqrt(2) + 5.0


def _stl_z_max_mm(path: Path) -> float:
    mesh = trimesh.load(str(path), force="mesh")
    return float(mesh.bounds[1, 2])


def _results_path(rung: str) -> Path:
    return Path("docs/validation/loaded_ladder") / f"{rung}.json"


def _write_results(
    *,
    rung: str,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    verdict = ladder_verdict(rows)
    payload = {
        "rung": rung,
        "config": config,
        "rows": rows,
        "verdict": verdict,
    }
    out_path = _results_path(rung)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return verdict


def run_pilot(
    *, rung: str, out: Path, rig: Any, args: argparse.Namespace, build, runner, points: list[float],
) -> int:
    """Mesh once, solve ONE point at a fraction of --iters (or a short URANS sample).

    Writes ``<out>/pilot.json`` with the estimated full-run time for ``len(points)`` back-
    pressure points, then returns without running the requested sweep.
    """
    n_points = max(1, len(points))

    if rung == "urans":
        # Sample a short URANS burst (10% of the requested revolutions) to measure the
        # simulated-time rate, then scale to the full revs * 60 / rpm simulated time.
        pilot_revs = max(0.1, float(args.revs) * 0.1)
        pilot_end_time = pilot_revs * 60.0 / rig.rpm
        build(points[0])
        t_mesh = time.time()
        run_mesh(runner)
        mesh_s = time.time() - t_mesh
        apply_urans_transient(
            out, end_time=pilot_end_time, delta_t=args.delta_t, max_co=args.max_co)
        t_solve = time.time()
        run_solve_urans(runner, n_procs=int(args.procs))
        wall_s = time.time() - t_solve
        sim_s_per_wall_s = pilot_end_time / wall_s if wall_s > 0 else 0.0
        full_wall_s_per_point = estimate_urans_wall_s(
            sim_s_per_wall_s=sim_s_per_wall_s, revs=args.revs, rpm=rig.rpm)
        cells = mesh_cells(out)
        payload = write_pilot_json(
            out / "pilot.json",
            cells=cells, mesh_s=mesh_s, sec_per_iter=full_wall_s_per_point,
            iters=1, points=n_points,
            extra={"pilot_revs": pilot_revs, "sim_s_per_wall_s": sim_s_per_wall_s,
                  "note": "urans: sec_per_iter is wall-s per point, iters=1"},
        )
    else:
        pilot_n = pilot_iters(int(args.iters))
        build(points[0], n_iters=pilot_n)
        t_mesh = time.time()
        run_mesh(runner)
        mesh_s = time.time() - t_mesh
        t_solve = time.time()
        run_solve(runner, n_procs=int(args.procs))
        wall_s = time.time() - t_solve
        sec_per_iter = wall_s / pilot_n if pilot_n else 0.0
        cells = mesh_cells(out)
        payload = write_pilot_json(
            out / "pilot.json",
            cells=cells, mesh_s=mesh_s, sec_per_iter=sec_per_iter,
            iters=int(args.iters), points=n_points,
            extra={"pilot_iters": pilot_n},
        )

    print(
        f"[pilot {rung}] cells={cells} mesh={mesh_s:.0f}s -> full run ({n_points} points) "
        f"~{payload['estimated_full_run_eta']} ({payload['estimated_full_run_s']:.0f}s)",
        flush=True,
    )
    print(f"-> {out / 'pilot.json'}")
    return 0


def run_ladder(args: argparse.Namespace) -> int:
    rung = args.rung
    points = [float(p) for p in args.points.split(",")]
    out = Path(args.out) / rung
    out.mkdir(parents=True, exist_ok=True)
    procs = int(args.procs)
    base_cell = float(args.base_cell)
    box_scale = float(args.box_scale)
    tip_gap_mm = float(args.tip_gap_mm)

    params = load_blade_params(args.params)
    min_wall = min_blade_wall_mm(params)
    stl_shared = _resolve_impeller_stl(out, params, None)
    rig = _rig_for_case(params, tip_gap_mm, None)

    # Always orient and fit via prepare_axial_cfd (Audit #1 direction fix).
    stl, rig = prepare_axial_cfd(stl_shared, rig, out)

    plenum_z_mm = _plenum_z_mm(rig)
    fill_radius_mm = _fill_radius_mm(rig, box_scale)

    casing_path = out / "casing.stl"
    export_casing_stl(
        rig, casing_path,
        plenum_z_mm=plenum_z_mm, fill_radius_mm=fill_radius_mm,
    )

    frame_path: Path | None = None
    if rung in ("frame", "urans"):
        frame_path = out / "frame.stl"
        export_frame_stl(params, rig, frame_path)
        frame_z_max = _stl_z_max_mm(frame_path)
        if not frame_z_max < plenum_z_mm:
            raise ValueError(
                f"frame z_max={frame_z_max:.2f} mm is not upstream of the plenum "
                f"plane plenum_z_mm={plenum_z_mm:.2f} mm -- the frame would sit "
                "inside (or past) the outlet chamber")

    mesh_res = _mesh(base_cell, min_wall_mm=min_wall)

    config: dict[str, Any] = {
        "rung": rung,
        "params": args.params,
        "points": points,
        "procs": procs,
        "base_cell": base_cell,
        "box_scale": box_scale,
        "tip_gap_mm": tip_gap_mm,
        "plenum_z_mm": plenum_z_mm,
        "cfd_version": CFD_VERSION,
    }
    if rung == "urans":
        config.update({
            "revs": args.revs,
            "delta_t": args.delta_t,
            "max_co": args.max_co,
        })
    else:
        config["iters"] = args.iters

    runner = OpenFOAMRunner(out)

    def _build(back_pa: float, n_iters: int | None = None) -> None:
        build_case(
            out, stl, rig,
            mesh=mesh_res,
            n_iters=int(n_iters if n_iters is not None else args.iters),
            n_subdomains=procs,
            back_pressure_pa=back_pa,
            frame_stl_mm=frame_path,
            casing_stl_mm=casing_path,
            box_scale=box_scale,
        )

    if args.pilot:
        return run_pilot(rung=rung, out=out, rig=rig, args=args, build=_build, runner=runner,
                         points=points)

    # Mesh once at the first point, then solve each point.
    _build(points[0])
    run_mesh(runner)

    rows: list[dict[str, Any]] = []

    def _solve_point(back_pa: float) -> dict[str, Any]:
        _build(back_pa)
        t0 = time.time()
        if rung == "urans":
            end_time = args.revs * 60.0 / rig.rpm
            apply_urans_transient(
                out, end_time=end_time, delta_t=args.delta_t, max_co=args.max_co)
            run_solve_urans(runner, n_procs=procs)
        else:
            run_solve(runner, n_procs=procs)
        wall_s = time.time() - t0
        m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
        sanity_checks = run_sanity(out, metrics=m, omega_signed=rig.omega_signed)
        return {
            "back_pa": back_pa,
            "cfm": m.cfm,
            "converged": m.converged,
            "drift_pct": round(m.flow_drift_pct, 1),
            "oscillation_pct": round(m.oscillation_pct, 1),
            "sanity": [asdict(c) for c in sanity_checks],
            "sanity_status": sanity_overall(sanity_checks),
            "cells": mesh_cells(out),
            "wall_s": wall_s,
            "sec_per_iter": (wall_s / args.iters) if rung != "urans" and args.iters else None,
        }

    for b in points:
        t0 = time.time()
        row = _solve_point(b)
        rows.append(row)
        verdict = _write_results(rung=rung, rows=rows, config=config)
        print(
            f"[{rung}] back={b:5.1f} Pa -> {row['cfm']:6.1f} CFM  "
            f"{'converged' if row['converged'] else 'UNCONVERGED'}  "
            f"shift={row['drift_pct']:.1f}%  osc={row['oscillation_pct']:.1f}%  "
            f"({time.time() - t0:.0f}s)",
            flush=True,
        )

    if verdict["verdict"] == "PASS" and 20.0 not in points:
        b = 20.0
        t0 = time.time()
        row = _solve_point(b)
        rows.append(row)
        verdict = _write_results(rung=rung, rows=rows, config=config)
        print(
            f"[{rung}] back={b:5.1f} Pa -> {row['cfm']:6.1f} CFM  "
            f"{'converged' if row['converged'] else 'UNCONVERGED'}  "
            f"shift={row['drift_pct']:.1f}%  osc={row['oscillation_pct']:.1f}%  "
            f"({time.time() - t0:.0f}s)  [added for PASS confirmation]",
            flush=True,
        )

    print(f"\n===== LOADED LADDER: {rung} =====")
    print(f"  published free-air: {PUB_FREE_AIR_CFM} CFM ; shut-off: {PUB_SHUTOFF_PA} Pa")
    print(f"  verdict: {verdict['verdict']}")
    if verdict["shutoff_pa"] is not None:
        print(f"  shut-off: {verdict['shutoff_pa']:.1f} Pa")
    if verdict["free_air_cfm"] is not None:
        print(f"  free air: {verdict['free_air_cfm']:.1f} CFM")
    for r in verdict["reasons"]:
        print(f"  - {r}")
    print(f"-> {_results_path(rung)}")

    return 0 if verdict["verdict"] != "FAIL" else 1


def main() -> int:
    args = build_parser().parse_args()
    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2
    return run_ladder(args)


if __name__ == "__main__":
    sys.exit(main())
