"""Audit #1, proof 3: bias-free free-air CFD matrix for one rotor STL.

Meshes each orientation once ({as_built, flipped 180° about X}), then solves spin -1 and +1 at
0 Pa back-pressure on that mesh, and writes the rows + verdict JSON.

Usage:
    uv run python scripts/audit_direction_cfd.py --rotor stock
    uv run python scripts/audit_direction_cfd.py --rotor reference_stl --iters 1500 --procs 8
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import trimesh  # noqa: E402

from fansim.audit.direction import flip_about_x  # noqa: E402
from fansim.audit.direction_verdict import MatrixRow, matrix_verdict  # noqa: E402
from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.validation.reference_stl import rig_for_reference_stl  # noqa: E402

import math

ROOT = Path(__file__).resolve().parents[1]
ROTORS = {
    "stock": ROOT / "runs" / "audit_direction" / "stock_impeller.stl",   # written by Task 6 script
    "reference_stl": ROOT / "validation" / "reference" / "a12x25_impeller.stl",
}
GEOM_JSON = ROOT / "docs" / "validation" / "audits" / "direction_geometry.json"


def _none_for_nan(v: float) -> float | None:
    """Convert NaN/inf to None for JSON serialization."""
    if not math.isfinite(v):
        return None
    return v


def _write_payload(out: Path, rotor: str, rpm: float, iters: int, mesh_res, rows: list[MatrixRow],
                   errors: list[str], geometry: dict, verdict: dict) -> None:
    """Write partial results to JSON with NaN converted to None."""
    payload = {
        "rotor": rotor, "rpm": rpm, "iters": iters,
        "mesh": asdict(mesh_res),
        "rows": [
            {
                "orientation": r.orientation,
                "spin": r.spin,
                "cfm": _none_for_nan(r.cfm),
                "converged": r.converged,
                "shaft_power_w": _none_for_nan(r.shaft_power_w),
                "moment_z_nm": _none_for_nan(r.moment_z_nm),
                "omega_signed": r.omega_signed,
            }
            for r in rows
        ],
        "errors": errors,
        "geometry": geometry,
        "verdict": verdict,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rotor", choices=sorted(ROTORS), required=True)
    ap.add_argument("--rpm", type=float, default=2000.0)
    ap.add_argument("--base-cell", type=float, default=0.006)
    ap.add_argument("--min-wall-mm", type=float, default=None,
                    help="thinnest blade wall for mesh sizing (default: Stock recipe value)")
    ap.add_argument("--iters", type=int, default=1500)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/audit_direction")
    args = ap.parse_args(argv)
    if not image_available():
        print("SKIPPED: OpenFOAM image not available")
        return 2
    src = ROTORS[args.rotor]
    if not src.is_file():
        print(f"missing {src}; run scripts/audit_direction_geometry.py first")
        return 2
    if not GEOM_JSON.is_file():
        print(f"missing {GEOM_JSON}; run scripts/audit_direction_geometry.py first")
        return 2
    geom_data = json.loads(GEOM_JSON.read_text(encoding="utf-8"))
    if "rotors" not in geom_data or args.rotor not in geom_data["rotors"]:
        print(f"rotor '{args.rotor}' not found in {GEOM_JSON}; run scripts/audit_direction_geometry.py first")
        return 2
    geom = geom_data["rotors"][args.rotor]
    base = Path(args.out) / args.rotor
    min_wall = args.min_wall_mm
    if min_wall is None:
        from fansim.geometry.blade import min_blade_wall_mm
        from fansim.geometry.config import load_blade_params
        min_wall = min_blade_wall_mm(load_blade_params(
            ROOT / "config" / "problems" / "a12x25_reference.yaml"))
    mesh_res = MeshResolution.for_blade(float(args.base_cell), float(min_wall))
    rows: list[MatrixRow] = []
    errors: list[str] = []
    out = ROOT / "docs" / "validation" / "audits" / f"direction_cfd_{args.rotor}.json"
    for orientation in ("as_built", "flipped"):
        case = base / orientation
        case.mkdir(parents=True, exist_ok=True)
        stl = case / "impeller_mm.stl"
        rig0 = None
        try:
            mesh = trimesh.load(str(src), force="mesh")
            (flip_about_x(mesh) if orientation == "flipped" else mesh).export(str(stl))
            rig0 = rig_for_reference_stl(stl, rpm=args.rpm)
            runner = OpenFOAMRunner(case)
            build_case(case, stl, rig0, mesh=mesh_res, n_iters=args.iters,
                       n_subdomains=args.procs, back_pressure_pa=0.0)
            t0 = time.time()
            run_mesh(runner)
            print(f"[{orientation}] meshed in {time.time() - t0:.0f}s", flush=True)
        except Exception as e:
            msg = f"[{orientation}] meshing failed: {e}"
            errors.append(msg)
            print(msg, flush=True)
            omega_rad_s = args.rpm * 2 * math.pi / 60 if rig0 is None else rig0.omega_rad_s
            for spin in (-1, 1):
                rows.append(MatrixRow(orientation, spin, float("nan"), False, float("nan"),
                                    float("nan"), omega_rad_s * spin))
                verdict = matrix_verdict(rows, geometry_omega=geom.get("omega_sign"),
                                       geometry_pump=geom.get("pump_sign"))
                _write_payload(out, args.rotor, args.rpm, args.iters, mesh_res, rows, errors, geom, verdict)
            continue
        for spin in (-1, 1):
            try:
                rig = replace(rig0, spin=spin)
                build_case(case, stl, rig, mesh=mesh_res, n_iters=args.iters,
                           n_subdomains=args.procs, back_pressure_pa=0.0)
                t0 = time.time()
                run_solve(runner, n_procs=args.procs)
                m = parse_fan_metrics(case, omega_rad_s=rig.omega_rad_s)
                row = MatrixRow(orientation, spin, m.cfm, m.converged, m.shaft_power_w,
                                m.moment_z_nm, rig.omega_signed)
                rows.append(row)
                print(f"[{orientation} spin {spin:+d}] CFM {m.cfm:+.1f} conv={m.converged} "
                      f"drift={m.flow_drift_pct:.1f}% P={m.shaft_power_w:.3f} W "
                      f"Mz={m.moment_z_nm:+.5f} ({time.time() - t0:.0f}s)", flush=True)
            except Exception as e:
                msg = f"[{orientation} spin {spin:+d}] solve failed: {e}"
                errors.append(msg)
                print(msg, flush=True)
                rows.append(MatrixRow(orientation, spin, float("nan"), False, float("nan"),
                                    float("nan"), rig0.omega_rad_s * spin))
            verdict = matrix_verdict(rows, geometry_omega=geom.get("omega_sign"),
                                   geometry_pump=geom.get("pump_sign"))
            _write_payload(out, args.rotor, args.rpm, args.iters, mesh_res, rows, errors, geom, verdict)
    print(f"\nVERDICT {verdict['verdict']}: {verdict}\n-> {out}", flush=True)
    return 3 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
