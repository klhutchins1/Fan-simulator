"""FAN-01 external CFD-method benchmark runner (.superpowers/sdd/fan01-runner-brief.md).

FAN-01 (Kroemer et al., Zenodo 10787093, CC-BY-4.0) is a low-pressure axial fan with a
published watertight rotor STL and a measured 20-point back-pressure/flow characteristic,
used here as an external-method validation: geometry and measurement are independent of
anything in this repo, unlike the NF-A12x25 recipe-fit validation.

Direction is derived from the rotor mesh alone (no hand-set spin) via
``fansim.validation.fan01.fan01_direction`` -> ``fansim.cfd.orientation.orientation_from_proof``.

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
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.orientation import fit_rig_to_stl, orient_impeller_for_cfd  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.cfd.sanity import overall as sanity_overall, run_sanity  # noqa: E402
from fansim.cfd.timing import mesh_cells, pilot_iters, write_pilot_json  # noqa: E402
from fansim.validation.fan01 import (  # noqa: E402
    DEFAULT_OUT_STL,
    fan01_direction,
    fan01_rig,
    load_characteristic,
    measured_q_report,
)

DEFAULT_POINTS = "7,64,126,135,205,253"
DEFAULT_MIN_WALL_MM = 3.0  # not measured from the STL (would need a chord-normal thickness
# probe via a cylinder cut at r=185mm, per the brief's fallback) -- pass --min-wall-mm if a
# measured value is available; 3.0 mm is a conservative placeholder for a fan this size (~4x
# the Noctua a12x25).
RING_LENGTH_MM = 201.0  # rig casing sleeve: 96.5mm upstream + 104.5mm downstream of rotor mid
RING_CENTER_OFFSET_MM = (104.5 - 96.5) / 2.0  # +4mm downstream of the rotor mid-plane
OUT_JSON = Path("docs/validation/fan01/fan01_cfd.json")


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
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--base-cell", type=float, default=0.02)
    ap.add_argument("--out", default="runs/fan01")
    ap.add_argument("--pilot", action="store_true",
                    help="mesh once, solve ONE point briefly, print the estimate for all "
                         "points, then exit without running the full sweep")
    return ap


def _mesh(base_cell: float, min_wall_mm: float, add_layers: bool) -> MeshResolution:
    return MeshResolution.for_blade(base_cell, min_wall_mm, add_layers=add_layers)


def prepare_rig_and_stl(stl_src: Path, out: Path, rpm: float) -> tuple[Path, Any, str]:
    """fan01_rig -> fan01_direction -> oriented rig+STL (flip is a no-op when as_built)."""
    rig = fan01_rig(stl_src, rpm=rpm)
    orientation, spin = fan01_direction(stl_src)
    rig = replace(rig, spin=spin)
    if orientation == "flipped":
        stl = out / "impeller_cfd.stl"
        orient_impeller_for_cfd(stl_src, stl, orientation="flipped")
        rig = fit_rig_to_stl(rig, stl)
    else:
        stl = Path(stl_src)
    return stl, rig, orientation


def write_rows_json(out_path: Path, rows: list[dict[str, Any]]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def run_pilot(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stl_src = Path(args.stl)
    points = [float(p) for p in args.points.split(",")]

    stl, rig, orientation = prepare_rig_and_stl(stl_src, out, args.rpm)
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


def main() -> int:
    args = build_parser().parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    if args.pilot:
        return run_pilot(args)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stl_src = Path(args.stl)
    points = [float(p) for p in args.points.split(",")]
    characteristic = load_characteristic()

    stl, rig, orientation = prepare_rig_and_stl(stl_src, out, args.rpm)
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
        write_rows_json(OUT_JSON, rows)
        print(
            f"  back={b:6.1f} Pa -> {m.cfm:6.1f} CFM ({m.flow_m3s:.3f} m3/s)  "
            f"measured~{row.get('measured_q_m3s')}  "
            f"{'converged' if m.converged else 'UNCONVERGED'} osc={m.oscillation_pct:.0f}%  "
            f"({wall_s:.0f}s)",
            flush=True,
        )

    print(f"-> {OUT_JSON}")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
