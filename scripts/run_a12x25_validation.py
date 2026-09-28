"""Phase 3 entry: validate NF-A12x25 P–Q against published data using the reference stock recipe.

Defaults to ``config/problems/a12x25_reference.yaml`` (cockpit Stock / Phase 2 reference), not the
legacy approximate-only ``a12x25.yaml`` path. Runs a multi-back-pressure sweep at ``--base-cell``,
optionally a free-air-only mesh ladder via ``--mesh-ladder``. Writes ``validation.json`` and a
P–Q plot under ``--out``.

Usage:
    uv run python scripts/run_a12x25_validation.py --backs 0,5,10,15,20 \\
        --base-cell 0.005 --iters 1000 --procs 8

    uv run python scripts/run_a12x25_validation.py --mesh-ladder 0.008,0.005,0.003 \\
        --backs 0,5,10,15,20
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

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from fansim.analyze.grid_convergence import grid_convergence_index  # noqa: E402
from fansim.cfd.domain import rig_for_impeller  # noqa: E402
from fansim.cfd.frame import export_frame_stl  # noqa: E402
from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.orientation import prepare_axial_cfd  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.cfd.sanity import overall as sanity_overall, run_sanity  # noqa: E402
from fansim.cfd.timing import mesh_cells, pilot_iters, write_pilot_json  # noqa: E402
from fansim.cfd.wall_roughness import FDM_WALL_KS_MM  # noqa: E402
from fansim.geometry import build_impeller, export_stl  # noqa: E402
from fansim.geometry.blade import min_blade_wall_mm  # noqa: E402
from fansim.geometry.config import load_blade_params  # noqa: E402
from fansim.validation.pq_shutoff import shutoff_report_from_pq_rows  # noqa: E402
from fansim.validation.reference_stl import (  # noqa: E402
    DEFAULT_REFERENCE_STL,
    rig_for_reference_stl,
)

DEFAULT_PARAMS = "config/problems/a12x25_reference.yaml"
DEFAULT_BACKS = "0,5,10,15,20"
NEAR_SHUTOFF_BACKS = "0,5,10,12,14,15,16,17,18,20,22,24,26"
NEAR_SHUTOFF_ITERS = 1200

# Published NF-A12x25 PWM (docs/a12x25-reference.md).
PUB_FREE_AIR_CFM = 60.1
PUB_SHUTOFF_PA = 22.9


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="A12x25 reference-stock CFD validation (P–Q vs published)")
    ap.add_argument("--params", default=DEFAULT_PARAMS,
                    help="blade recipe YAML (default: cockpit reference stock)")
    ap.add_argument("--backs", default=DEFAULT_BACKS,
                    help="back-pressure sweep [Pa], comma-separated")
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument(
        "--near-shutoff",
        action="store_true",
        help=(
            f"§1.5 dense near-stall campaign: backs={NEAR_SHUTOFF_BACKS} "
            f"and iters={NEAR_SHUTOFF_ITERS} when those flags are left at defaults"
        ),
    )
    ap.add_argument("--base-cell", type=float, default=0.005,
                    help="base_cell [m] for the multi-back P–Q sweep")
    ap.add_argument("--mesh-ladder", default=None, metavar="SIZES",
                    help="optional free-air-only ladder: base_cell sizes [m], coarse->fine "
                         "(e.g. 0.008,0.005,0.003); three sizes enable GCI stamp when computed")
    ap.add_argument("--ladder-only", action="store_true",
                    help="run --mesh-ladder only (skip the multi-back P–Q sweep)")
    ap.add_argument("--tip-gap-mm", type=float, default=0.5,
                    help="radial tip clearance [mm] for the duct (published A12x25 = 0.5; "
                         "Phase 3 screening accidentally used domain default 1.0)")
    ap.add_argument("--tip-gap-study", default=None, metavar="GAPS",
                    help="free-air A/B at fixed --base-cell for tip gaps [mm], e.g. 1.0,0.5,0.25")
    ap.add_argument("--with-frame", action="store_true",
                    help="include four-bar exhaust frame STL (optimizer default geometry)")
    ap.add_argument("--wall-ks-mm", type=float, default=None,
                    help="sand-grain roughness [mm] on impeller/frame (default smooth; "
                         f"FDM order-of-magnitude ~= {FDM_WALL_KS_MM:g})")
    ap.add_argument("--physics-study", action="store_true",
                    help="free-air A/B at --base-cell/--tip-gap-mm: open, frame, wall_ks, "
                         "frame+wall_ks (wall_ks from --wall-ks-mm or FDM default)")
    ap.add_argument("--physics-only", action="store_true",
                    help="run --physics-study only (skip multi-back P–Q unless also requested)")
    ap.add_argument(
        "--stl",
        default=None,
        metavar="PATH",
        help="use this impeller STL instead of build_impeller(params); "
             f"default when flag is bare: {DEFAULT_REFERENCE_STL.as_posix()}",
        nargs="?",
        const=str(DEFAULT_REFERENCE_STL),
    )
    ap.add_argument("--layers", action="store_true",
                    help="grow prism layers on the impeller (snappy addLayers; off by default)")
    ap.add_argument("--surf-max", type=int, default=None,
                    help="snappy surface refinement level on the impeller. Default: auto from "
                         "the recipe's thinnest wall (finest cell <= wall/3) so thin blades are "
                         "resolved -- surf 2 at 5 mm under-reads the a12x25 refit ~30%%")
    ap.add_argument("--feature-level", type=int, default=None,
                    help="snappy feature (edge) refinement level; default follows --surf-max/auto")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/validate_a12x25_phase3")
    ap.add_argument("--pilot", action="store_true",
                    help="mesh once, solve ONE point at max(50, iters//10) iterations, "
                         "print/write <out>/pilot.json with the estimated full-run time, "
                         "then exit without running the full sweep")
    return ap


def apply_near_shutoff_defaults(args) -> None:
    """Apply dense near-stall backs/iters when ``--near-shutoff`` and defaults remain."""
    if not getattr(args, "near_shutoff", False):
        return
    if args.backs == DEFAULT_BACKS:
        args.backs = NEAR_SHUTOFF_BACKS
    if int(args.iters) == 1000:
        args.iters = NEAR_SHUTOFF_ITERS


def _mesh(
    base_cell: float,
    add_layers: bool = False,
    *,
    min_wall_mm: float | None = None,
    surf_max: int | None = None,
    feature_level: int | None = None,
) -> MeshResolution:
    """Mesh resolution for a run.

    ``surf_max`` (CLI override) forces the snappy surface level; otherwise, when
    ``min_wall_mm`` is known, the surface level is auto-picked to resolve the thin blade
    (finest cell <= wall/3, see openfoam_case.surface_level_for_wall) so validation reads the
    true CFM instead of an under-resolved one. ``feature_level`` overrides edge refinement.
    """
    if surf_max is not None:
        return MeshResolution(
            base_cell=base_cell, surf_min=max(1, int(surf_max) - 1), surf_max=int(surf_max),
            feature_level=int(feature_level) if feature_level is not None else int(surf_max),
            add_layers=bool(add_layers))
    if min_wall_mm is not None:
        m = MeshResolution.for_blade(base_cell, min_wall_mm, add_layers=bool(add_layers))
        if feature_level is not None:
            m.feature_level = int(feature_level)
        return m
    return MeshResolution(base_cell=base_cell, add_layers=bool(add_layers))


def _resolve_impeller_stl(
    out_root: Path,
    params: Any,
    stl_src: Path | None,
) -> Path:
    """Copy shared impeller into out_root; build from params when no --stl."""
    out_root.mkdir(parents=True, exist_ok=True)
    dest = out_root / "impeller.stl"
    if dest.exists():
        return dest
    if stl_src is not None:
        src = Path(stl_src)
        if not src.is_file():
            raise FileNotFoundError(f"--stl not found: {src}")
        dest.write_bytes(src.read_bytes())
        return dest
    return export_stl(build_impeller(params), dest)


def _rig_for_case(params: Any, tip_gap_mm: float, stl_path: Path | None) -> Any:
    if stl_path is not None:
        return rig_for_reference_stl(
            stl_path,
            rpm=float(params.rpm),
            tip_gap_mm=tip_gap_mm,
            inlet_diameters=2.0,
            outlet_diameters=4.0,
            params=params,
        )
    return rig_for_impeller(
        params, tip_gap_mm=tip_gap_mm, inlet_diameters=2.0, outlet_diameters=4.0)



def _run_free_air_at_cell(
    *,
    out: Path,
    stl: Path,
    rig: Any,
    base_cell: float,
    n_iters: int,
    n_procs: int,
    frame_stl: Path | None = None,
    wall_ks_mm: float | None = None,
    add_layers: bool = False,
    min_wall_mm: float | None = None,
    surf_max: int | None = None,
    feature_level: int | None = None,
) -> dict[str, Any]:
    """Mesh + solve at 0 Pa back-pressure for one base_cell size."""
    runner = OpenFOAMRunner(out)
    build_case(
        out, stl, rig,
        mesh=_mesh(base_cell, add_layers, min_wall_mm=min_wall_mm,
                   surf_max=surf_max, feature_level=feature_level),
        n_iters=n_iters,
        n_subdomains=n_procs,
        back_pressure_pa=0.0,
        frame_stl_mm=frame_stl,
        wall_ks_mm=wall_ks_mm,
    )
    run_mesh(runner)
    t_solve = time.time()
    run_solve(runner, n_procs=n_procs)
    wall_s = time.time() - t_solve
    m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
    return {
        "base_cell": base_cell,
        "back_pa": 0.0,
        "cfm": m.cfm,
        "converged": m.converged,
        "drift_pct": round(m.flow_drift_pct, 1),
        "oscillation_pct": round(m.oscillation_pct, 1),
        "tip_gap_mm": float(rig.tip_gap) / 1e-3,
        "with_frame": frame_stl is not None,
        "wall_ks_mm": float(wall_ks_mm) if wall_ks_mm is not None else 0.0,
        "add_layers": bool(add_layers),
        "cells": mesh_cells(out),
        "wall_s": wall_s,
        "sec_per_iter": wall_s / n_iters if n_iters else None,
    }


def run_mesh_ladder(
    *,
    params_path: str,
    cells: list[float],
    out_root: Path,
    n_iters: int,
    n_procs: int,
    tip_gap_mm: float = 0.5,
    stl_src: Path | None = None,
    add_layers: bool = False,
    surf_max: int | None = None,
    feature_level: int | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    params = load_blade_params(params_path)
    min_wall = min_blade_wall_mm(params)
    stl_shared = _resolve_impeller_stl(out_root, params, stl_src)
    base_rig = _rig_for_case(params, tip_gap_mm, stl_shared if stl_src else None)
    for bc in cells:
        cell_out = out_root / f"ladder_{bc:g}"
        cell_out.mkdir(parents=True, exist_ok=True)
        stl = cell_out / "impeller.stl"
        if not stl.exists():
            stl.write_bytes(stl_shared.read_bytes())
        stl, rig = prepare_axial_cfd(stl, base_rig, cell_out)
        t = time.time()
        row = _run_free_air_at_cell(
            out=cell_out,
            stl=stl,
            rig=rig,
            base_cell=bc,
            n_iters=n_iters,
            n_procs=n_procs,
            add_layers=add_layers,
            min_wall_mm=min_wall,
            surf_max=surf_max,
            feature_level=feature_level,
        )
        row["tip_gap_mm"] = float(tip_gap_mm)
        print(
            f"  ladder base_cell={bc:g} tip_gap={tip_gap_mm:g} mm -> {row['cfm']:.1f} CFM  "
            f"({'converged' if row['converged'] else 'UNCONVERGED'})  "
            f"({time.time() - t:.0f}s)",
            flush=True,
        )
        rows.append(row)
    return rows


def run_free_air_tip_gap_study(
    *,
    params_path: str,
    tip_gaps_mm: list[float],
    base_cell: float,
    out_root: Path,
    n_iters: int,
    n_procs: int,
    stl_src: Path | None = None,
    add_layers: bool = False,
    surf_max: int | None = None,
    feature_level: int | None = None,
) -> list[dict[str, Any]]:
    """Free-air A/B at fixed mesh for several tip clearances."""
    rows: list[dict[str, Any]] = []
    params = load_blade_params(params_path)
    min_wall = min_blade_wall_mm(params)
    stl_shared = _resolve_impeller_stl(out_root, params, stl_src)
    for gap in tip_gaps_mm:
        gap_out = out_root / f"tipgap_{gap:g}mm"
        gap_out.mkdir(parents=True, exist_ok=True)
        stl = gap_out / "impeller.stl"
        if not stl.exists():
            stl.write_bytes(stl_shared.read_bytes())
        rig = _rig_for_case(params, gap, stl_shared if stl_src else None)
        stl, rig = prepare_axial_cfd(stl, rig, gap_out)
        t = time.time()
        row = _run_free_air_at_cell(
            out=gap_out, stl=stl, rig=rig,
            base_cell=base_cell, n_iters=n_iters, n_procs=n_procs,
            add_layers=add_layers,
            min_wall_mm=min_wall, surf_max=surf_max, feature_level=feature_level,
        )
        row["tip_gap_mm"] = float(gap)
        print(
            f"  tip_gap={gap:g} mm base_cell={base_cell:g} -> {row['cfm']:.1f} CFM  "
            f"({'converged' if row['converged'] else 'UNCONVERGED'})  "
            f"({time.time() - t:.0f}s)",
            flush=True,
        )
        rows.append(row)
    return rows


def run_free_air_physics_study(
    *,
    params_path: str,
    base_cell: float,
    out_root: Path,
    n_iters: int,
    n_procs: int,
    tip_gap_mm: float = 0.5,
    wall_ks_mm: float = FDM_WALL_KS_MM,
    stl_src: Path | None = None,
    add_layers: bool = False,
    surf_max: int | None = None,
    feature_level: int | None = None,
) -> list[dict[str, Any]]:
    """Free-air A/B for open duct vs frame / wall_ks idealizations."""
    configs: list[tuple[str, bool, float | None]] = [
        ("open", False, None),
        ("frame", True, None),
        ("wall_ks", False, wall_ks_mm),
        ("frame_wall_ks", True, wall_ks_mm),
    ]
    rows: list[dict[str, Any]] = []
    params = load_blade_params(params_path)
    min_wall = min_blade_wall_mm(params)
    stl_shared = _resolve_impeller_stl(out_root, params, stl_src)
    base_rig = _rig_for_case(params, tip_gap_mm, stl_shared if stl_src else None)

    for label, with_frame, ks in configs:
        case_out = out_root / f"physics_{label}"
        case_out.mkdir(parents=True, exist_ok=True)
        stl = case_out / "impeller.stl"
        if not stl.exists():
            stl.write_bytes(stl_shared.read_bytes())
        stl, rig = prepare_axial_cfd(stl, base_rig, case_out)
        frame_path: Path | None = None
        if with_frame:
            frame_path = case_out / "frame.stl"
            if not frame_path.exists():
                export_frame_stl(params, rig, frame_path)
        t = time.time()
        row = _run_free_air_at_cell(
            out=case_out, stl=stl, rig=rig,
            base_cell=base_cell, n_iters=n_iters, n_procs=n_procs,
            frame_stl=frame_path, wall_ks_mm=ks,
            add_layers=add_layers,
            min_wall_mm=min_wall, surf_max=surf_max, feature_level=feature_level,
        )
        row["label"] = label
        row["tip_gap_mm"] = float(tip_gap_mm)
        print(
            f"  physics={label} tip_gap={tip_gap_mm:g} mm base_cell={base_cell:g} "
            f"-> {row['cfm']:.1f} CFM  "
            f"({'converged' if row['converged'] else 'UNCONVERGED'})  "
            f"({time.time() - t:.0f}s)",
            flush=True,
        )
        rows.append(row)
    return rows


def maybe_stamp_gci(ladder_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """If three ladder free-air points exist, run Roache GCI (fine→coarse by base_cell)."""
    if len(ladder_rows) != 3:
        return {
            "gci_computed": False,
            "reason": f"need exactly 3 ladder points for GCI; got {len(ladder_rows)}",
        }
    ordered = sorted(ladder_rows, key=lambda r: r["base_cell"])
    h1, h2, h3 = (r["base_cell"] for r in ordered)
    f1, f2, f3 = (r["cfm"] for r in ordered)
    try:
        gci = grid_convergence_index(h1, h2, h3, f1, f2, f3)
    except ValueError as exc:
        return {"gci_computed": False, "reason": str(exc)}
    return {
        "gci_computed": True,
        "grid_converged_claim": False,
        "note": "GCI computed from free-air ladder; not a full grid-converged campaign "
                "until Task 3.2 documents mesh counts and asymptotic range.",
        **asdict(gci),
    }


def run_pq_sweep(
    *,
    params_path: str,
    backs: list[float],
    base_cell: float,
    out: Path,
    n_iters: int,
    n_procs: int,
    tip_gap_mm: float = 0.5,
    with_frame: bool = False,
    wall_ks_mm: float | None = None,
    stl_src: Path | None = None,
    add_layers: bool = False,
    surf_max: int | None = None,
    feature_level: int | None = None,
) -> list[dict[str, Any]]:
    params = load_blade_params(params_path)
    min_wall = min_blade_wall_mm(params)
    stl = _resolve_impeller_stl(out, params, stl_src)
    rig = _rig_for_case(params, tip_gap_mm, stl if stl_src else None)
    stl, rig = prepare_axial_cfd(stl, rig, out)
    frame_path: Path | None = None
    if with_frame:
        frame_path = out / "frame.stl"
        export_frame_stl(params, rig, frame_path)
    runner = OpenFOAMRunner(out)
    mesh_res = _mesh(base_cell, add_layers, min_wall_mm=min_wall,
                     surf_max=surf_max, feature_level=feature_level)

    build_case(
        out, stl, rig,
        mesh=mesh_res,
        n_iters=n_iters,
        n_subdomains=n_procs,
        back_pressure_pa=backs[0],
        frame_stl_mm=frame_path,
        wall_ks_mm=wall_ks_mm,
    )
    run_mesh(runner)

    rows: list[dict[str, Any]] = []
    for b in backs:
        build_case(
            out, stl, rig,
            mesh=mesh_res,
            n_iters=n_iters,
            n_subdomains=n_procs,
            back_pressure_pa=b,
            frame_stl_mm=frame_path,
            wall_ks_mm=wall_ks_mm,
        )
        t = time.time()
        run_solve(runner, n_procs=n_procs)
        wall_s = time.time() - t
        m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
        sanity_checks = run_sanity(out, metrics=m, omega_signed=rig.omega_signed)
        rows.append({
            "back_pa": b,
            "cfm": m.cfm,
            "converged": m.converged,
            "drift_pct": round(m.flow_drift_pct, 1),
            "oscillation_pct": round(m.oscillation_pct, 1),
            "base_cell": base_cell,
            "tip_gap_mm": float(tip_gap_mm),
            "with_frame": with_frame,
            "wall_ks_mm": float(wall_ks_mm) if wall_ks_mm is not None else 0.0,
            "add_layers": bool(add_layers),
            "sanity": [asdict(c) for c in sanity_checks],
            "sanity_status": sanity_overall(sanity_checks),
            "cells": mesh_cells(out),
            "wall_s": wall_s,
            "sec_per_iter": wall_s / n_iters if n_iters else None,
        })
        print(
            f"  back={b:5.1f} Pa -> {m.cfm:6.1f} CFM  "
            f"{'converged' if m.converged else 'UNCONVERGED %.0f%% shift' % m.flow_drift_pct}"
            f" osc={m.oscillation_pct:.0f}%"
            f"  ({time.time() - t:.0f}s)",
            flush=True,
        )
    return rows


def write_outputs(
    *,
    out: Path,
    params_path: str,
    pq_rows: list[dict[str, Any]],
    ladder_rows: list[dict[str, Any]] | None,
    gci: dict[str, Any] | None,
    tip_gap_rows: list[dict[str, Any]] | None = None,
    tip_gap_mm: float | None = None,
    physics_rows: list[dict[str, Any]] | None = None,
    stl_src: str | None = None,
    add_layers: bool = False,
) -> None:
    free_air = next((r["cfm"] for r in pq_rows if r.get("back_pa") == 0.0), None)
    if free_air is None and ladder_rows:
        fine = min(ladder_rows, key=lambda r: r["base_cell"])
        free_air = fine["cfm"]
    if free_air is None and physics_rows:
        open_row = next((r for r in physics_rows if r.get("label") == "open"), physics_rows[0])
        free_air = open_row["cfm"]
    payload: dict[str, Any] = {
        "params": params_path,
        "published": {"free_air_cfm": PUB_FREE_AIR_CFM, "shutoff_pa": PUB_SHUTOFF_PA},
        "pq_rows": pq_rows,
        "add_layers": bool(add_layers),
    }
    if stl_src is not None:
        payload["stl"] = stl_src
    if tip_gap_mm is not None:
        payload["tip_gap_mm"] = tip_gap_mm
    if ladder_rows is not None:
        payload["mesh_ladder"] = ladder_rows
    if tip_gap_rows is not None:
        payload["tip_gap_study"] = tip_gap_rows
    if physics_rows is not None:
        payload["physics_study"] = physics_rows
    if gci is not None:
        payload["gci"] = gci
    if pq_rows:
        payload["shutoff"] = shutoff_report_from_pq_rows(
            pq_rows, published_pa=PUB_SHUTOFF_PA,
        )

    (out / "validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(7.5, 5))
    if pq_rows:
        conv = [r for r in pq_rows if r["converged"]]
        unconv = [r for r in pq_rows if not r["converged"]]
        if conv:
            ax.plot(
                [r["cfm"] for r in conv],
                [r["back_pa"] for r in conv],
                "o-",
                color="tab:blue",
                label="sim (converged)",
            )
        if unconv:
            ax.scatter(
                [r["cfm"] for r in unconv],
                [r["back_pa"] for r in unconv],
                facecolors="none",
                edgecolors="gray",
                label="sim (unconverged, near stall)",
            )
    if ladder_rows:
        ax.scatter(
            [r["cfm"] for r in ladder_rows],
            [0.0] * len(ladder_rows),
            marker="s",
            color="tab:green",
            label="mesh ladder (free-air)",
            zorder=4,
        )
    if physics_rows:
        ax.scatter(
            [r["cfm"] for r in physics_rows],
            [0.0] * len(physics_rows),
            marker="D",
            color="tab:orange",
            label="physics A/B (free-air)",
            zorder=4,
        )
    ax.scatter(
        [PUB_FREE_AIR_CFM, 0.0],
        [0.0, PUB_SHUTOFF_PA],
        color="crimson",
        s=80,
        marker="*",
        zorder=5,
        label="published A12x25",
    )
    ax.set_xlabel("Flow  [CFM]")
    ax.set_ylabel("Static pressure / back-pressure  [Pa]")
    ax.set_title("A12x25 reference validation: sim vs published")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "validation.png", dpi=130)

    print("\n===== VALIDATION vs published NF-A12x25 =====")
    print(f"  params: {params_path}")
    print(f"  published free-air: {PUB_FREE_AIR_CFM} CFM ; shut-off: {PUB_SHUTOFF_PA} Pa")
    if free_air is not None:
        ratio = free_air / PUB_FREE_AIR_CFM
        print(
            f"  sim free-air (0 Pa): {free_air:.1f} CFM  "
            f"=> {ratio:.2f}x published ({(ratio - 1) * 100:+.0f}%)"
        )
    if physics_rows:
        for r in physics_rows:
            print(
                f"  physics {r.get('label')}: {r['cfm']:.1f} CFM "
                f"(frame={r.get('with_frame')} wall_ks={r.get('wall_ks_mm')} mm)"
            )
    if gci and gci.get("gci_computed"):
        print(
            f"  GCI: p={gci.get('p')}, f_extrap={gci.get('f_extrapolated')}, "
            f"GCI_fine={gci.get('gci_fine_pct')}%, asymptotic={gci.get('asymptotic_ratio')}"
        )
    elif gci:
        print(f"  GCI: not computed ({gci.get('reason', 'n/a')})")
    shut = payload.get("shutoff") if pq_rows else None
    if shut and shut.get("shutoff_pa") is not None:
        flag = "PASS" if shut.get("interim_pass") else "FAIL"
        print(
            f"  shut-off: {shut['shutoff_pa']:.1f} Pa "
            f"(published {shut['published_pa']:.1f}; interim {flag}; {shut['method']})"
        )
    print(f"-> {out / 'validation.png'} , {out / 'validation.json'}")


def run_pilot(args) -> int:
    """Mesh once, solve ONE point at a fraction of --iters, and estimate the full run.

    Writes ``<out>/pilot.json`` and prints a summary, then returns without running the
    requested sweep -- lets an operator judge whether the full run is worth the wait before
    committing hours (or days) of wall time to it.
    """
    backs = [float(b) for b in args.backs.split(",")]
    out = Path(args.out)
    tip_gap_mm = float(args.tip_gap_mm)
    stl_src = Path(args.stl) if args.stl else None
    add_layers = bool(args.layers)

    params = load_blade_params(args.params)
    min_wall = min_blade_wall_mm(params)
    stl = _resolve_impeller_stl(out, params, stl_src)
    rig = _rig_for_case(params, tip_gap_mm, stl if stl_src else None)
    stl, rig = prepare_axial_cfd(stl, rig, out)

    mesh_res = _mesh(args.base_cell, add_layers, min_wall_mm=min_wall,
                     surf_max=args.surf_max, feature_level=args.feature_level)
    pilot_n = pilot_iters(args.iters)

    runner = OpenFOAMRunner(out)
    build_case(
        out, stl, rig, mesh=mesh_res, n_iters=pilot_n, n_subdomains=args.procs,
        back_pressure_pa=backs[0],
    )
    t_mesh = time.time()
    run_mesh(runner)
    mesh_s = time.time() - t_mesh

    t_solve = time.time()
    run_solve(runner, n_procs=args.procs)
    wall_s = time.time() - t_solve
    sec_per_iter = wall_s / pilot_n if pilot_n else 0.0
    cells = mesh_cells(out)

    points = max(1, len(backs))
    payload = write_pilot_json(
        out / "pilot.json",
        cells=cells, mesh_s=mesh_s, sec_per_iter=sec_per_iter,
        iters=args.iters, points=points,
        extra={"pilot_iters": pilot_n, "backs": backs, "note": "pq sweep: 1 mesh x N solves"},
    )
    print(
        f"[pilot] cells={cells} mesh={mesh_s:.0f}s sec/iter={sec_per_iter:.3f} "
        f"({pilot_n} pilot iters) -> full run ({points} points x {args.iters} iters) "
        f"~{payload['estimated_full_run_eta']} ({payload['estimated_full_run_s']:.0f}s)",
        flush=True,
    )
    print(f"-> {out / 'pilot.json'}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    apply_near_shutoff_defaults(args)

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    if getattr(args, "pilot", False):
        return run_pilot(args)

    backs = [float(b) for b in args.backs.split(",")]
    out = Path(args.out)
    tip_gap_mm = float(args.tip_gap_mm)
    stl_src = Path(args.stl) if args.stl else None
    add_layers = bool(args.layers)
    t0 = time.time()

    ladder_rows: list[dict[str, Any]] | None = None
    tip_gap_rows: list[dict[str, Any]] | None = None
    physics_rows: list[dict[str, Any]] | None = None
    gci: dict[str, Any] | None = None
    if args.mesh_ladder:
        cells = [float(c) for c in args.mesh_ladder.split(",")]
        print(
            f"[mesh-ladder] free-air at base_cell={cells} tip_gap={tip_gap_mm:g} mm"
            + (f" stl={stl_src}" if stl_src else "")
            + (" layers=on" if add_layers else ""),
            flush=True,
        )
        ladder_rows = run_mesh_ladder(
            params_path=args.params,
            cells=cells,
            out_root=out,
            n_iters=args.iters,
            n_procs=args.procs,
            tip_gap_mm=tip_gap_mm,
            stl_src=stl_src,
            add_layers=add_layers,
            surf_max=args.surf_max,
            feature_level=args.feature_level,
        )
        gci = maybe_stamp_gci(ladder_rows)

    if args.tip_gap_study:
        gaps = [float(g) for g in args.tip_gap_study.split(",")]
        print(
            f"[tip-gap-study] free-air gaps={gaps} base_cell={args.base_cell}",
            flush=True,
        )
        tip_gap_rows = run_free_air_tip_gap_study(
            params_path=args.params,
            tip_gaps_mm=gaps,
            base_cell=args.base_cell,
            out_root=out,
            n_iters=args.iters,
            n_procs=args.procs,
            stl_src=stl_src,
            add_layers=add_layers,
            surf_max=args.surf_max,
            feature_level=args.feature_level,
        )

    if args.physics_study:
        ks = float(args.wall_ks_mm) if args.wall_ks_mm is not None else FDM_WALL_KS_MM
        print(
            f"[physics-study] free-air open/frame/wall_ks={ks:g} "
            f"base_cell={args.base_cell} tip_gap={tip_gap_mm:g} mm",
            flush=True,
        )
        physics_rows = run_free_air_physics_study(
            params_path=args.params,
            base_cell=args.base_cell,
            out_root=out,
            n_iters=args.iters,
            n_procs=args.procs,
            tip_gap_mm=tip_gap_mm,
            wall_ks_mm=ks,
            stl_src=stl_src,
            add_layers=add_layers,
            surf_max=args.surf_max,
            feature_level=args.feature_level,
        )

    skip_pq = bool(args.ladder_only or args.physics_only)
    pq_rows: list[dict[str, Any]] = []
    if not skip_pq:
        print(
            f"[pq-sweep] backs={backs} base_cell={args.base_cell} "
            f"tip_gap={tip_gap_mm:g} mm frame={args.with_frame} "
            f"wall_ks={args.wall_ks_mm}"
            + (f" stl={stl_src}" if stl_src else "")
            + (" layers=on" if add_layers else ""),
            flush=True,
        )
        pq_rows = run_pq_sweep(
            params_path=args.params,
            backs=backs,
            base_cell=args.base_cell,
            out=out,
            n_iters=args.iters,
            n_procs=args.procs,
            tip_gap_mm=tip_gap_mm,
            with_frame=bool(args.with_frame),
            wall_ks_mm=args.wall_ks_mm,
            stl_src=stl_src,
            add_layers=add_layers,
            surf_max=args.surf_max,
            feature_level=args.feature_level,
        )
    write_outputs(
        out=out,
        params_path=args.params,
        pq_rows=pq_rows,
        ladder_rows=ladder_rows,
        gci=gci,
        tip_gap_rows=tip_gap_rows,
        tip_gap_mm=tip_gap_mm,
        physics_rows=physics_rows,
        stl_src=str(stl_src) if stl_src else None,
        add_layers=add_layers,
    )
    print(f"  total {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
