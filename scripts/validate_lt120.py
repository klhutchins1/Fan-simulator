"""lt120 validation campaign (R1.1a). Freeze geometry, then 4 ΔP × 2 meshes.

    python scripts/validate_lt120.py --freeze
    python scripts/validate_lt120.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.domain import rig_for_impeller
from fansim.cfd.frame import export_frame_stl
from fansim.cfd.metrics import CFM_PER_M3S, parse_fan_metrics
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve
from fansim.cfd.orientation import prepare_axial_cfd
from fansim.cfd.runner import OpenFOAMRunner, image_available
from fansim.cfd.sanity import run_sanity
from fansim.geometry.blade import min_blade_wall_mm
from fansim.validation.lt120 import (
    DUCT_ID_MM,
    FREEZE_DIR,
    MESHES_MM,
    POINTS,
    TIP_GAP_MM,
    freeze_geometry,
    lt120_params,
    past_cutoff,
    point_converged,
)

OUT = ROOT / "runs" / "lt120"


def _write_progress(out: Path, payload: dict) -> None:
    (out / "progress.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _mass_imbalance_pct(case: Path) -> float | None:
    for c in run_sanity(case):
        if c.name == "mass_balance":
            return None if c.value is None else float(c.value)
    return None


def parse_cli(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="lt120 CFD campaign (R1.1a)")
    ap.add_argument("--freeze", action="store_true", help="build STL and write geometry_freeze.json")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=8)
    # Tip-gap follow-up (docs/validation/audits/2026-10-30-lt120-tip-gap-prereg.md): rotor frozen, only the duct grows.
    ap.add_argument("--tip-gap", type=float, default=TIP_GAP_MM, help="mm; duct ID = 2 r_tip + 2 gap")
    ap.add_argument("--dp", type=float, nargs="+", default=None, help="subset of the frozen points (Pa)")
    ap.add_argument("--meshes", type=float, nargs="+", default=list(MESHES_MM), help="base cells (mm)")
    return ap.parse_args(argv)


def duct_id_mm(tip_gap_mm: float) -> float:
    """Duct ID for a tip gap around the frozen rotor (121 mm at the frozen 0.5 mm gap)."""
    return float(DUCT_ID_MM) + 2.0 * (float(tip_gap_mm) - float(TIP_GAP_MM))


def select_points(dps) -> list[dict]:
    if not dps:
        return list(POINTS)
    out = []
    for dp in dps:
        hit = [p for p in POINTS if abs(p["dp_pa"] - float(dp)) < 1e-6]
        if not hit:
            raise ValueError(f"{dp} Pa is not one of the frozen lt120 points")
        out.append(hit[0])
    return out


def _unit_key(dp_pa: float, mesh_mm: float) -> str:
    return f"p{dp_pa:g}_m{mesh_mm:g}"


def _mesh_ready(mesh_dir: Path) -> bool:
    return (mesh_dir / "constant" / "polyMesh" / "points").is_file()


def main(argv: list[str] | None = None) -> int:
    a = parse_cli(argv)
    if a.freeze:
        doc = freeze_geometry()
        print(json.dumps({
            "stl": doc["stl"],
            "cut_measurable_pass": doc["cut_measurable_pass"],
            "n_bodies": doc["n_bodies"],
            "direction": doc["direction"],
        }))
        if doc["direction"] != "CONCLUSIVE":
            print("direction is not CONCLUSIVE; CFD will not start.", file=sys.stderr)
            return 1
        return 0 if doc["cut_measurable_pass"] and doc["n_bodies"] == 1 else 1

    if not image_available():
        print("OpenFOAM image not available.", file=sys.stderr)
        return 2

    freeze_stl = FREEZE_DIR / "lt120.stl"
    freeze_json = FREEZE_DIR / "geometry_freeze.json"
    if not freeze_stl.is_file() or not freeze_json.is_file():
        freeze_geometry()
    freeze_doc = json.loads(freeze_json.read_text(encoding="utf-8"))
    if freeze_doc.get("direction") != "CONCLUSIVE":
        print("lt120 freeze direction is not CONCLUSIVE; stop.", file=sys.stderr)
        return 1

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summ_path = out / "summary.json"
    try:
        summary = json.loads(summ_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        summary = {"fan": "lt120", "points": select_points(a.dp), "meshes_mm": list(a.meshes),
                   "tip_gap_mm": a.tip_gap, "duct_id_mm": duct_id_mm(a.tip_gap), "units": {}}
    units = summary.setdefault("units", {})
    params = lt120_params()

    for mesh_mm in a.meshes:
        mesh_dir = out / f"mesh_{mesh_mm:g}"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        stl = mesh_dir / "impeller.stl"
        if not stl.is_file():
            stl.write_bytes(freeze_stl.read_bytes())
        rig = rig_for_impeller(
            params, tip_gap_mm=a.tip_gap, inlet_diameters=2.0, outlet_diameters=4.0,
            casing_id_mm=duct_id_mm(a.tip_gap))
        stl, rig = prepare_axial_cfd(stl, rig, mesh_dir, source="builder")
        frame = mesh_dir / "frame.stl"
        if not frame.is_file():
            export_frame_stl(params, rig, frame)
        mesh_res = MeshResolution.for_blade(
            mesh_mm * 1e-3, min_blade_wall_mm(params), add_layers=True)
        runner = OpenFOAMRunner(mesh_dir)

        if not _mesh_ready(mesh_dir):
            if past_cutoff():
                _write_progress(out, {"stopped": "cutoff", "next": f"mesh_{mesh_mm:g}"})
                summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                print("stopped before 15:30 local")
                return 0
            build_case(
                mesh_dir, stl, rig, mesh=mesh_res, n_iters=a.iters,
                n_subdomains=a.procs, back_pressure_pa=select_points(a.dp)[0]["dp_pa"],
                frame_stl_mm=frame)
            run_mesh(runner, n_procs=a.procs)

        for pt in select_points(a.dp):
            key = _unit_key(pt["dp_pa"], mesh_mm)
            if units.get(key, {}).get("cfm") is not None:
                continue
            if past_cutoff():
                _write_progress(out, {"stopped": "cutoff", "next": key})
                summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                print("stopped before 15:30 local")
                return 0
            _write_progress(out, {"current": key, "t0": time.time()})
            build_case(
                mesh_dir, stl, rig, mesh=mesh_res, n_iters=a.iters,
                n_subdomains=a.procs, back_pressure_pa=pt["dp_pa"],
                frame_stl_mm=frame)
            t0 = time.time()
            run_solve(runner, n_procs=a.procs)
            m = parse_fan_metrics(mesh_dir, omega_rad_s=rig.omega_rad_s)
            mass = _mass_imbalance_pct(mesh_dir)
            ok = point_converged(m.oscillation_pct, mass)
            q_meas = pt["q_m3s"] * CFM_PER_M3S
            units[key] = {
                "dp_pa": pt["dp_pa"], "mesh_mm": mesh_mm, "role": pt["role"],
                "cfm": m.cfm, "q_meas_cfm": q_meas,
                "err": None if q_meas == 0 else m.cfm / q_meas - 1.0,
                "oscillation_pct": m.oscillation_pct,
                "mass_imbalance_pct": mass,
                "converged_gate": ok,
                "inconclusive": not ok,
                "wall_s": time.time() - t0,
            }
            summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(f"{key} CFM={m.cfm:.2f} osc={m.oscillation_pct:.2f} mass={mass} ok={ok}")

    _write_progress(out, {"stopped": "complete", "n_units": len(units)})
    print(json.dumps({"units": len(units)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
