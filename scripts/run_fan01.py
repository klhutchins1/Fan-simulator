"""FAN-01 external CFD-method benchmark runner (.superpowers/sdd/fan01-runner-brief.md).

FAN-01 (Kroemer et al., Zenodo 10787093, CC-BY-4.0) is a low-pressure axial fan with a
published watertight rotor STL and a measured 20-point back-pressure/flow characteristic,
used here as an external-method validation: geometry and measurement are independent of
anything in this repo, unlike the NF-A12x25 recipe-fit validation.

Direction is derived from the rotor mesh alone (no hand-set spin) via
``fansim.cfd.orientation.prepare_axial_cfd(source="external")`` (proof -> ``orientation_from_proof``).

Usage:
    uv run python scripts/run_fan01.py --pilot
    uv run python scripts/run_fan01.py --points 7,64,126,135,205,253 \\
        --iters 1000 --procs 16 --base-cell 0.02 --out runs/fan01
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.metrics import parse_fan_metrics
from fansim.cfd.openfoam_case import (
    MeshResolution,
    apply_urans_transient,
    build_case,
    run_mesh,
    run_solve,
    run_solve_urans,
)
from fansim.cfd.orientation import prepare_axial_cfd
from fansim.cfd.runner import OpenFOAMRunner, image_available
from fansim.cfd.sanity import overall as sanity_overall
from fansim.cfd.sanity import run_sanity
from fansim.cfd.timing import (
    mean_time_step,
    mesh_cells,
    pilot_iters,
    read_fo_time_column,
    urans_pilot_estimate,
    write_pilot_json,
)
from fansim.validation.fan01 import (
    DEFAULT_OUT_STL,
    FAN01_MRF_MARGIN_MM,
    fan01_rig,
    load_characteristic,
    measured_q_report,
    scale_rotor_to_published_tip,
    tip_gap_report,
)

DEFAULT_POINTS = "7,64,126,135,205,253"
DEFAULT_MIN_WALL_MM = 4.0  # measured 2026-09-28: chord-binned section thickness via cylinder cuts
# (median 7.1 mm at r=140, 5.4 at r=185, 4.7 at r=230; thinner toward LE/TE) -> 4.0 mm for mesh sizing.
RING_LENGTH_MM = 201.0  # rig casing sleeve: 96.5mm upstream + 104.5mm downstream of rotor mid
RING_CENTER_OFFSET_MM = (104.5 - 96.5) / 2.0  # +4mm downstream of the rotor mid-plane
OUT_JSON = Path("docs/validation/fan01/fan01_cfd_rv2.json")
URANS_OUT_JSON = Path("docs/validation/fan01/fan01_urans.json")
URANS_PILOT_REV_FRAC = 0.25  # pilot end_time = this fraction of one revolution


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="FAN-01 external CFD-method benchmark (measured characteristic)")
    ap.add_argument("--stl", default=str(DEFAULT_OUT_STL),
                    help="rotor STL (default: extracted validation/reference/fan01/fan01_rotor.stl)")
    ap.add_argument("--points", default=DEFAULT_POINTS,
                    help="back-pressures [Pa], comma-separated (default matches the measured "
                         "chamber pressures at Q ~= 2.08, 1.80, 1.40, 0.99, 0.61, 0.20 m3/s)")
    ap.add_argument("--rpm", type=float, default=1486.0)
    ap.add_argument("--min-wall-mm", type=float, default=DEFAULT_MIN_WALL_MM,
                    help="thinnest blade wall [mm] for the adaptive mesh (MeshResolution.for_blade)")
    ap.add_argument("--layers", action="store_true", default=False,
                    help="grow prism layers on the impeller (snappy addLayers; off by default)")
    ap.add_argument(
        "--align-tip", action="store_true", default=False,
        help="§19.13: uniform-scale rotor so tip radius matches published 247.5 mm "
             "(restores 2.5 mm geometric tip clearance vs duct)",
    )
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--base-cell", type=float, default=0.02)
    ap.add_argument("--out", default="runs/fan01")
    ap.add_argument(
        "--out-json", type=Path, default=None,
        help=f"result rows JSON path (default: {OUT_JSON} steady, {URANS_OUT_JSON} --urans)",
    )
    ap.add_argument("--pilot", action="store_true",
                    help="mesh once, solve ONE point briefly, print the estimate for all "
                         "points, then exit without running the full sweep")
    ap.add_argument("--urans", action="store_true",
                    help="frozen-rotor URANS (pimpleFoam) instead of steady MRF simpleFoam")
    ap.add_argument("--revs", type=float, default=4.0,
                    help="[urans] rotor revolutions to simulate per point (default 4)")
    ap.add_argument("--max-co", type=float, default=5.0,
                    help="[urans] max Courant number for the adjustable time step")
    ap.add_argument("--n-outer", type=int, default=3,
                    help="[urans] PIMPLE nOuterCorrectors (>1 adds outer-loop residual "
                         "control + relaxation so a larger --max-co still converges)")
    ap.add_argument("--delta-t", type=float, default=1e-5,
                    help="[urans] initial time step [s] (adjustTimeStep then targets --max-co)")
    ap.add_argument("--pilot-seconds", type=float, default=600.0,
                    help="[urans --pilot] wall-clock budget for the short transient solve")
    return ap


def resolve_out_json(args: argparse.Namespace) -> Path:
    """Result JSON path: --out-json override, else URANS_OUT_JSON (--urans) or OUT_JSON (steady)."""
    if args.out_json is not None:
        return Path(args.out_json)
    return URANS_OUT_JSON if args.urans else OUT_JSON


def _mesh(base_cell: float, min_wall_mm: float, add_layers: bool) -> MeshResolution:
    return MeshResolution.for_blade(base_cell, min_wall_mm, add_layers=add_layers)


def prepare_rig_and_stl(stl_src: Path, out: Path, rpm: float,
                        *, align_tip: bool = False) -> tuple[Path, Any, str]:
    """fan01_rig -> prepare_axial_cfd(source="external") -> oriented rig+STL (roadmap 19.2)."""
    out.mkdir(parents=True, exist_ok=True)
    gap = tip_gap_report(stl_src)
    print(
        f"[fan01] tip_gap measured={gap['tip_gap_mm_measured']:.2f} mm "
        f"(STL tip {gap['tip_radius_mm_measured']:.2f}) vs published "
        f"{gap['tip_gap_mm_published']:.2f} mm",
        flush=True,
    )
    src = stl_src
    if align_tip:
        aligned = out / "fan01_rotor_tip_aligned.stl"
        info = scale_rotor_to_published_tip(stl_src, aligned)
        print(
            f"[fan01] --align-tip scale={info['scale']:.6f} "
            f"tip {info['tip_radius_mm_before']:.2f}→{info['tip_radius_mm_after']:.2f} mm "
            f"gap→{info['tip_gap_mm_after']:.2f} mm",
            flush=True,
        )
        src = aligned
    rig = fan01_rig(src, rpm=rpm)  # tip_gap defaults to published 2.5 mm
    stl, rig = prepare_axial_cfd(src, rig, out, source="external",
                                 mrf_margin_mm=FAN01_MRF_MARGIN_MM)
    meta = json.loads((out / "direction_meta.json").read_text(encoding="utf-8"))
    return stl, rig, meta["orientation"]


def write_rows_json(out_path: Path, rows: list[dict[str, Any]]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def run_pilot(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stl_src = Path(args.stl)
    points = [float(p) for p in args.points.split(",")]

    stl, rig, orientation = prepare_rig_and_stl(stl_src, out, args.rpm, align_tip=bool(args.align_tip))
    print(f"[fan01] direction={orientation!r} spin={rig.spin:+d} "
          f"tip_gap={rig.tip_gap * 1e3:.2f}mm hub_radius={rig.hub_radius * 1e3:.1f}mm",
          flush=True)

    from fansim.cfd.domain import MM_TO_M
    mid_z_mm = 0.5 * (rig.impeller_z_min + rig.impeller_z_max) / MM_TO_M
    ring_z_center_mm = mid_z_mm + RING_CENTER_OFFSET_MM

    mesh_res = _mesh(args.base_cell, args.min_wall_mm, args.layers)
    pilot_n = pilot_iters(args.iters)

    runner = OpenFOAMRunner(out)
    build_case(
        out, stl, rig, mesh=mesh_res, n_iters=pilot_n, n_subdomains=args.procs,
        back_pressure_pa=points[0], duct="ring",
        ring_length_mm=RING_LENGTH_MM, ring_z_center_mm=ring_z_center_mm,
    )
    t_mesh = time.time()
    run_mesh(runner)
    mesh_s = time.time() - t_mesh

    t_solve = time.time()
    run_solve(runner, n_procs=args.procs)
    wall_s = time.time() - t_solve
    sec_per_iter = wall_s / pilot_n if pilot_n else 0.0
    cells = mesh_cells(out)

    payload = write_pilot_json(
        out / "pilot.json",
        cells=cells, mesh_s=mesh_s, sec_per_iter=sec_per_iter,
        iters=args.iters, points=max(1, len(points)),
        extra={"pilot_iters": pilot_n, "backs": points, "direction": orientation,
              "note": "fan01 pq sweep: 1 mesh x N solves"},
    )
    print(
        f"[pilot] cells={cells} mesh={mesh_s:.0f}s sec/iter={sec_per_iter:.3f} "
        f"({pilot_n} pilot iters) -> full run ({len(points)} points x {args.iters} iters) "
        f"~{payload['estimated_full_run_eta']} ({payload['estimated_full_run_s']:.0f}s)",
        flush=True,
    )
    print(f"-> {out / 'pilot.json'}")
    return 0


def run_pilot_urans(args) -> int:
    """mesh once; run a short transient solve; report sim-time rate + full-run/full-sweep ETA."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stl_src = Path(args.stl)
    points = [float(p) for p in args.points.split(",")]

    stl, rig, orientation = prepare_rig_and_stl(stl_src, out, args.rpm, align_tip=bool(args.align_tip))
    print(f"[fan01-urans-pilot] direction={orientation!r} spin={rig.spin:+d} "
          f"tip_gap={rig.tip_gap * 1e3:.2f}mm hub_radius={rig.hub_radius * 1e3:.1f}mm",
          flush=True)

    from fansim.cfd.domain import MM_TO_M
    mid_z_mm = 0.5 * (rig.impeller_z_min + rig.impeller_z_max) / MM_TO_M
    ring_z_center_mm = mid_z_mm + RING_CENTER_OFFSET_MM

    mesh_res = _mesh(args.base_cell, args.min_wall_mm, args.layers)
    runner = OpenFOAMRunner(out)
    build_case(
        out, stl, rig, mesh=mesh_res, n_iters=args.iters, n_subdomains=args.procs,
        back_pressure_pa=points[0], duct="ring",
        ring_length_mm=RING_LENGTH_MM, ring_z_center_mm=ring_z_center_mm,
    )
    t_mesh = time.time()
    run_mesh(runner)
    mesh_s = time.time() - t_mesh

    pilot_end_time = URANS_PILOT_REV_FRAC * 60.0 / args.rpm
    apply_urans_transient(
        out, end_time=pilot_end_time, delta_t=args.delta_t, max_co=args.max_co,
        n_outer=args.n_outer,
    )

    t_solve = time.time()
    run_solve_urans(runner, n_procs=args.procs)
    wall_s = time.time() - t_solve

    times = read_fo_time_column(out)
    mean_dt = mean_time_step(times)
    reached_time_s = times[-1] if times else 0.0
    cells = mesh_cells(out)

    # Rate from what was actually reached (a slow first step can undershoot end_time within
    # --pilot-seconds); fall back to the requested end_time if nothing was written yet.
    est = urans_pilot_estimate(
        pilot_end_time=reached_time_s if reached_time_s > 0 else pilot_end_time,
        wall_s=wall_s, revs=args.revs, rpm=args.rpm, n_points=max(1, len(points)),
    )

    payload = {
        "mode": "urans",
        "cells": cells,
        "mesh_s": mesh_s,
        "pilot_end_time_s": pilot_end_time,
        "reached_time_s": reached_time_s,
        "wall_s": wall_s,
        "mean_dt_s": mean_dt,
        "revs": args.revs,
        "max_co": args.max_co,
        "n_outer": args.n_outer,
        "delta_t": args.delta_t,
        "points": max(1, len(points)),
        "backs": points,
        "direction": orientation,
        **est,
    }
    out_path = Path("runs/fan01_urans/pilot.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(
        f"[urans-pilot] cells={cells} mesh={mesh_s:.0f}s reached t={reached_time_s:.3g}s "
        f"({wall_s:.0f}s wall) mean_dt={mean_dt:.2e}s sim/wall={est['sim_s_per_wall_s']:.3g} "
        f"-> per-point ({args.revs} revs) ~{est['estimated_per_point_eta']}, "
        f"full sweep ({len(points)} points) ~{est['estimated_total_eta']}",
        flush=True,
    )
    print(f"-> {out_path}")
    return 0


def run_urans(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stl_src = Path(args.stl)
    points = [float(p) for p in args.points.split(",")]
    characteristic = load_characteristic()

    stl, rig, orientation = prepare_rig_and_stl(stl_src, out, args.rpm, align_tip=bool(args.align_tip))
    print(f"[fan01-urans] direction={orientation!r} spin={rig.spin:+d} "
          f"tip_gap={rig.tip_gap * 1e3:.2f}mm hub_radius={rig.hub_radius * 1e3:.1f}mm "
          f"points={points} revs={args.revs} max_co={args.max_co} n_outer={args.n_outer}",
          flush=True)

    from fansim.cfd.domain import MM_TO_M
    mid_z_mm = 0.5 * (rig.impeller_z_min + rig.impeller_z_max) / MM_TO_M
    ring_z_center_mm = mid_z_mm + RING_CENTER_OFFSET_MM

    mesh_res = _mesh(args.base_cell, args.min_wall_mm, args.layers)
    runner = OpenFOAMRunner(out)
    end_time = args.revs * 60.0 / args.rpm

    build_case(
        out, stl, rig, mesh=mesh_res, n_iters=args.iters, n_subdomains=args.procs,
        back_pressure_pa=points[0], duct="ring",
        ring_length_mm=RING_LENGTH_MM, ring_z_center_mm=ring_z_center_mm,
    )
    run_mesh(runner)

    rows: list[dict[str, Any]] = []
    for b in points:
        build_case(
            out, stl, rig, mesh=mesh_res, n_iters=args.iters, n_subdomains=args.procs,
            back_pressure_pa=b, duct="ring",
            ring_length_mm=RING_LENGTH_MM, ring_z_center_mm=ring_z_center_mm,
        )
        apply_urans_transient(
            out, end_time=end_time, delta_t=args.delta_t, max_co=args.max_co,
            n_outer=args.n_outer,
        )
        t = time.time()
        run_solve_urans(runner, n_procs=args.procs)
        wall_s = time.time() - t
        m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
        sanity_checks = run_sanity(out, metrics=m, omega_signed=rig.omega_signed)
        times = read_fo_time_column(out)
        reached_time_s = times[-1] if times else None
        row: dict[str, Any] = {
            "mode": "urans",
            "back_pa": b,
            "q_m3s": m.flow_m3s,
            "cfm": m.cfm,
            "converged": m.converged,
            "osc": round(m.oscillation_pct, 1),
            "sanity": [asdict(c) for c in sanity_checks],
            "sanity_status": sanity_overall(sanity_checks),
            "cells": mesh_cells(out),
            "wall_s": wall_s,
            "revs": args.revs,
            "max_co": args.max_co,
            "n_outer": args.n_outer,
            "delta_t": args.delta_t,
            "end_time_s": end_time,
            "reached_time_s": reached_time_s,
        }
        row.update(measured_q_report(characteristic, b))
        rows.append(row)
        out_json = resolve_out_json(args)
        write_rows_json(out_json, rows)
        print(
            f"  back={b:6.1f} Pa -> {m.cfm:6.1f} CFM ({m.flow_m3s:.3f} m3/s)  "
            f"measured~{row.get('measured_q_m3s')}  "
            f"{'converged' if m.converged else 'UNCONVERGED'} osc={m.oscillation_pct:.0f}%  "
            f"reached t={reached_time_s} ({wall_s:.0f}s)",
            flush=True,
        )

    print(f"-> {resolve_out_json(args)}")
    return 0


def main() -> int:
    args = build_parser().parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    if args.urans and args.pilot:
        return run_pilot_urans(args)
    if args.pilot:
        return run_pilot(args)
    if args.urans:
        return run_urans(args)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stl_src = Path(args.stl)
    points = [float(p) for p in args.points.split(",")]
    characteristic = load_characteristic()

    stl, rig, orientation = prepare_rig_and_stl(stl_src, out, args.rpm, align_tip=bool(args.align_tip))
    print(f"[fan01] direction={orientation!r} spin={rig.spin:+d} "
          f"tip_gap={rig.tip_gap * 1e3:.2f}mm hub_radius={rig.hub_radius * 1e3:.1f}mm "
          f"points={points}", flush=True)

    from fansim.cfd.domain import MM_TO_M
    mid_z_mm = 0.5 * (rig.impeller_z_min + rig.impeller_z_max) / MM_TO_M
    ring_z_center_mm = mid_z_mm + RING_CENTER_OFFSET_MM

    mesh_res = _mesh(args.base_cell, args.min_wall_mm, args.layers)
    runner = OpenFOAMRunner(out)

    build_case(
        out, stl, rig, mesh=mesh_res, n_iters=args.iters, n_subdomains=args.procs,
        back_pressure_pa=points[0], duct="ring",
        ring_length_mm=RING_LENGTH_MM, ring_z_center_mm=ring_z_center_mm,
    )
    run_mesh(runner)

    rows: list[dict[str, Any]] = []
    for b in points:
        build_case(
            out, stl, rig, mesh=mesh_res, n_iters=args.iters, n_subdomains=args.procs,
            back_pressure_pa=b, duct="ring",
            ring_length_mm=RING_LENGTH_MM, ring_z_center_mm=ring_z_center_mm,
        )
        t = time.time()
        run_solve(runner, n_procs=args.procs)
        wall_s = time.time() - t
        m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
        sanity_checks = run_sanity(out, metrics=m, omega_signed=rig.omega_signed)
        row: dict[str, Any] = {
            "back_pa": b,
            "q_m3s": m.flow_m3s,
            "cfm": m.cfm,
            "converged": m.converged,
            "osc": round(m.oscillation_pct, 1),
            "sanity": [asdict(c) for c in sanity_checks],
            "sanity_status": sanity_overall(sanity_checks),
            "cells": mesh_cells(out),
            "wall_s": wall_s,
        }
        row.update(measured_q_report(characteristic, b))
        rows.append(row)
        out_json = resolve_out_json(args)
        write_rows_json(out_json, rows)
        print(
            f"  back={b:6.1f} Pa -> {m.cfm:6.1f} CFM ({m.flow_m3s:.3f} m3/s)  "
            f"measured~{row.get('measured_q_m3s')}  "
            f"{'converged' if m.converged else 'UNCONVERGED'} osc={m.oscillation_pct:.0f}%  "
            f"({wall_s:.0f}s)",
            flush=True,
        )

    print(f"-> {resolve_out_json(args)}")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
