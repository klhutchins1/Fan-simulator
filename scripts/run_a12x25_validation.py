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
from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.geometry import build_impeller, export_stl  # noqa: E402
from fansim.geometry.config import load_blade_params  # noqa: E402

DEFAULT_PARAMS = "config/problems/a12x25_reference.yaml"

# Published NF-A12x25 PWM (docs/a12x25-reference.md).
PUB_FREE_AIR_CFM = 60.1
PUB_SHUTOFF_PA = 22.9


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="A12x25 reference-stock CFD validation (P–Q vs published)")
    ap.add_argument("--params", default=DEFAULT_PARAMS,
                    help="blade recipe YAML (default: cockpit reference stock)")
    ap.add_argument("--backs", default="0,5,10,15,20",
                    help="back-pressure sweep [Pa], comma-separated")
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--base-cell", type=float, default=0.005,
                    help="base_cell [m] for the multi-back P–Q sweep")
    ap.add_argument("--mesh-ladder", default=None, metavar="SIZES",
                    help="optional free-air-only ladder: base_cell sizes [m], coarse→fine "
                         "(e.g. 0.008,0.005,0.003); three sizes enable GCI stamp when computed")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/validate_a12x25_phase3")
    return ap


def _run_free_air_at_cell(
    *,
    out: Path,
    stl: Path,
    rig: Any,
    base_cell: float,
    n_iters: int,
    n_procs: int,
) -> dict[str, Any]:
    """Mesh + solve at 0 Pa back-pressure for one base_cell size."""
    runner = OpenFOAMRunner(out)
    build_case(
        out, stl, rig,
        mesh=MeshResolution(base_cell=base_cell),
        n_iters=n_iters,
        n_subdomains=n_procs,
        back_pressure_pa=0.0,
    )
    run_mesh(runner)
    run_solve(runner, n_procs=n_procs)
    m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
    return {
        "base_cell": base_cell,
        "back_pa": 0.0,
        "cfm": m.cfm,
        "converged": m.converged,
        "drift_pct": round(m.flow_drift_pct, 1),
    }


def run_mesh_ladder(
    *,
    params_path: str,
    cells: list[float],
    out_root: Path,
    n_iters: int,
    n_procs: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    params = load_blade_params(params_path)
    stl_shared = out_root / "impeller.stl"
    if not stl_shared.exists():
        stl_shared = export_stl(build_impeller(params), stl_shared)
    rig = rig_for_impeller(params, inlet_diameters=2.0, outlet_diameters=4.0)
    for bc in cells:
        cell_out = out_root / f"ladder_{bc:g}"
        cell_out.mkdir(parents=True, exist_ok=True)
        stl = cell_out / "impeller.stl"
        if not stl.exists():
            stl.write_bytes(stl_shared.read_bytes())
        t = time.time()
        row = _run_free_air_at_cell(
            out=cell_out,
            stl=stl,
            rig=rig,
            base_cell=bc,
            n_iters=n_iters,
            n_procs=n_procs,
        )
        print(
            f"  ladder base_cell={bc:g} -> {row['cfm']:.1f} CFM  "
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
) -> list[dict[str, Any]]:
    params = load_blade_params(params_path)
    out.mkdir(parents=True, exist_ok=True)
    stl = export_stl(build_impeller(params), out / "impeller.stl")
    rig = rig_for_impeller(params, inlet_diameters=2.0, outlet_diameters=4.0)
    runner = OpenFOAMRunner(out)

    build_case(
        out, stl, rig,
        mesh=MeshResolution(base_cell=base_cell),
        n_iters=n_iters,
        n_subdomains=n_procs,
        back_pressure_pa=backs[0],
    )
    run_mesh(runner)

    rows: list[dict[str, Any]] = []
    for b in backs:
        build_case(
            out, stl, rig,
            mesh=MeshResolution(base_cell=base_cell),
            n_iters=n_iters,
            n_subdomains=n_procs,
            back_pressure_pa=b,
        )
        t = time.time()
        run_solve(runner, n_procs=n_procs)
        m = parse_fan_metrics(out, omega_rad_s=rig.omega_rad_s)
        rows.append({
            "back_pa": b,
            "cfm": m.cfm,
            "converged": m.converged,
            "drift_pct": round(m.flow_drift_pct, 1),
            "base_cell": base_cell,
        })
        print(
            f"  back={b:5.1f} Pa -> {m.cfm:6.1f} CFM  "
            f"{'converged' if m.converged else 'UNCONVERGED %.0f%%' % m.flow_drift_pct}"
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
) -> None:
    free_air = next((r["cfm"] for r in pq_rows if r["back_pa"] == 0.0), None)
    payload: dict[str, Any] = {
        "params": params_path,
        "published": {"free_air_cfm": PUB_FREE_AIR_CFM, "shutoff_pa": PUB_SHUTOFF_PA},
        "pq_rows": pq_rows,
    }
    if ladder_rows is not None:
        payload["mesh_ladder"] = ladder_rows
    if gci is not None:
        payload["gci"] = gci

    (out / "validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(7.5, 5))
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
    if gci and gci.get("gci_computed"):
        print(f"  GCI (free-air ladder): {gci.get('note', '')}")
    elif gci:
        print(f"  GCI: not computed ({gci.get('reason', 'n/a')})")
    print(f"-> {out / 'validation.png'} , {out / 'validation.json'}")


def main() -> int:
    args = build_parser().parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    backs = [float(b) for b in args.backs.split(",")]
    out = Path(args.out)
    t0 = time.time()

    ladder_rows: list[dict[str, Any]] | None = None
    gci: dict[str, Any] | None = None
    if args.mesh_ladder:
        cells = [float(c) for c in args.mesh_ladder.split(",")]
        print(f"[mesh-ladder] free-air at base_cell={cells}", flush=True)
        ladder_rows = run_mesh_ladder(
            params_path=args.params,
            cells=cells,
            out_root=out,
            n_iters=args.iters,
            n_procs=args.procs,
        )
        gci = maybe_stamp_gci(ladder_rows)

    print(f"[pq-sweep] backs={backs} base_cell={args.base_cell}", flush=True)
    pq_rows = run_pq_sweep(
        params_path=args.params,
        backs=backs,
        base_cell=args.base_cell,
        out=out,
        n_iters=args.iters,
        n_procs=args.procs,
    )
    write_outputs(
        out=out,
        params_path=args.params,
        pq_rows=pq_rows,
        ladder_rows=ladder_rows,
        gci=gci,
    )
    print(f"  total {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
