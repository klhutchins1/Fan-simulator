"""OpenFOAM DES + permeable-box FW-H (stage A).

Meshes an impeller STL (MRF + optional frame/casing), overlays pimpleFoam /
kOmegaSSTDES with six fixed permeable-face samplers, collects face loads, and
reduces with Farassat 1A panels. Stamps ``analogy=openfoam_des_fwh``.

MRF freezes blade geometry — indicative spectrum only, not mic-calibrated dB(A).
Do not mix with catalog Curle / LBM fwh_* rows.

Usage:
  uv run python scripts/evaluate_des_fwh.py --csv-only face_loads.csv --box-json box.json
  uv run python scripts/evaluate_des_fwh.py --stl build/a12x25_real_capped.stl \\
      --out runs/campaign_des_fwh --end-time 0.002 --delta-t 2e-5
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.acoustics.fwh import cv_box_from_dia_mm  # noqa: E402
from fansim.cfd.des_fwh import (  # noqa: E402
    read_box_sidecar,
    reduce_des_permeable,
    write_box_sidecar,
)

DEFAULT_STL = PROJECT / "build" / "a12x25_real_capped.stl"


def reduce_only(csv: Path, out: Path, *, box_json: Path | None, dia_mm: float | None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    if box_json is not None:
        box = read_box_sidecar(box_json)
    elif dia_mm is not None:
        box = cv_box_from_dia_mm(dia_mm)
    else:
        box = cv_box_from_dia_mm(110.5)
    m = reduce_des_permeable(csv, box=box)
    shutil.copy2(csv, out / "face_loads.csv")
    write_box_sidecar(out / "des_perm_box.json", box)
    (out / "des_fwh.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    return m


def run_des_fwh(
    stl: Path,
    out: Path,
    *,
    procs: int = 8,
    base_cell: float = 0.005,
    delta_t: float = 2e-5,
    end_time: float = 0.002,
    rpm: float = 2000.0,
    tip_gap_mm: float = 1.0,
    spin: int = -1,
    dia_mm: float | None = None,
    with_frame: bool = True,
    reuse_mesh: bool = False,
) -> dict:
    """Mesh + DES solve + permeable FW-H reduction. Requires OpenFOAM Docker image."""
    import numpy as np
    import trimesh

    from fansim.cfd.casing import export_casing_stl
    from fansim.cfd.des_fwh import box_from_duct, collect_face_loads_csv
    from fansim.cfd.domain import MM_TO_M, TestRig
    from fansim.cfd.frame import export_frame_stl
    from fansim.cfd.openfoam_case import (
        MeshResolution,
        apply_des_transient,
        build_case,
        run_mesh,
        run_solve_des,
    )
    from fansim.cfd.orientation import prepare_axial_cfd
    from fansim.cfd.runner import OpenFOAMRunner, image_available
    from fansim.geometry.blade import BladeParams

    if not image_available():
        raise RuntimeError("OpenFOAM Docker image not available")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    case = out / "case"
    case.mkdir(parents=True, exist_ok=True)

    stl = Path(stl).resolve()
    if dia_mm is None:
        ext = trimesh.load(str(stl), force="mesh").extents
        dia_mm = float(max(ext[0], ext[1]))

    m = trimesh.load(str(stl), force="mesh")
    lo, hi = m.bounds
    tip_r_mm = float(np.max(np.linalg.norm(m.vertices[:, :2], axis=1)))
    duct_r = (tip_r_mm + tip_gap_mm) * MM_TO_M
    diameter = 2.0 * duct_r
    rig = TestRig(
        duct_radius=duct_r,
        tip_gap=tip_gap_mm * MM_TO_M,
        inlet_length=2.0 * diameter,
        outlet_length=4.0 * diameter,
        impeller_z_min=lo[2] * MM_TO_M,
        impeller_z_max=hi[2] * MM_TO_M,
        mrf_z_min=(lo[2] - 2.0) * MM_TO_M,
        mrf_z_max=(hi[2] + 2.0) * MM_TO_M,
        rpm=rpm,
        inlet_velocity=2.0,
        spin=spin,
    )
    stl, rig = prepare_axial_cfd(stl, rig, case)
    half_z = max(0.02, 0.5 * (rig.impeller_z_max - rig.impeller_z_min) + 0.015)
    box = box_from_duct(rig.duct_radius, half_z_m=half_z)
    box["dia_mm"] = float(dia_mm)

    runner = OpenFOAMRunner(case)
    t0 = time.time()
    mesh_ok = (case / "constant" / "polyMesh" / "points").is_file()
    if not (reuse_mesh and mesh_ok):
        frame_path = None
        casing_path = None
        if with_frame:
            params = BladeParams()
            params.rpm = rpm
            frame_path = case / "frame.stl"
            casing_path = case / "casing.stl"
            export_frame_stl(params, rig, frame_path)
            export_casing_stl(rig, casing_path, stepped=False)

        build_case(
            case,
            stl,
            rig,
            mesh=MeshResolution(base_cell=base_cell),
            n_iters=100,
            n_subdomains=procs,
            back_pressure_pa=0.0,
            frame_stl_mm=frame_path,
            casing_stl_mm=casing_path,
        )
        run_mesh(runner)
        print(f"[mesh] {time.time() - t0:.0f}s", flush=True)
    else:
        print(f"[mesh] reuse {case}", flush=True)

    apply_des_transient(case, box=box, delta_t=delta_t, end_time=end_time)
    t1 = time.time()
    run_solve_des(runner, n_procs=procs)
    print(f"[des] {time.time() - t1:.0f}s", flush=True)

    csv = out / "face_loads.csv"
    collect_face_loads_csv(case, csv, box=box)
    metrics = reduce_des_permeable(csv, box=box)
    metrics["delta_t"] = delta_t
    metrics["end_time"] = end_time
    metrics["stl"] = str(stl)
    metrics["dia_mm"] = float(dia_mm)
    write_box_sidecar(out / "des_perm_box.json", box)
    (out / "des_fwh.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OpenFOAM DES + permeable FW-H (stage A)")
    ap.add_argument("--stl", type=Path, default=None, help="impeller STL (default: capped A12x25)")
    ap.add_argument("--out", type=Path, default=Path("runs/campaign_des_fwh"))
    ap.add_argument("--csv-only", type=Path, default=None, help="skip CFD; reduce existing CSV")
    ap.add_argument("--box-json", type=Path, default=None)
    ap.add_argument("--dia-mm", type=float, default=None)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--delta-t", type=float, default=2e-5)
    ap.add_argument("--end-time", type=float, default=0.002)
    ap.add_argument("--rpm", type=float, default=2000.0)
    ap.add_argument("--no-frame", action="store_true", help="impeller-only case (no frame/casing)")
    ap.add_argument("--reuse-mesh", action="store_true", help="skip remesh if polyMesh exists")
    args = ap.parse_args(argv)

    if args.csv_only is not None:
        m = reduce_only(args.csv_only, args.out, box_json=args.box_json, dia_mm=args.dia_mm)
        print(json.dumps(m, indent=2))
        return 0

    stl = args.stl or DEFAULT_STL
    if not Path(stl).exists():
        ap.error(f"STL not found: {stl}")
    m = run_des_fwh(
        Path(stl),
        args.out,
        procs=args.procs,
        base_cell=args.base_cell,
        delta_t=args.delta_t,
        end_time=args.end_time,
        rpm=args.rpm,
        dia_mm=args.dia_mm,
        with_frame=not args.no_frame,
        reuse_mesh=args.reuse_mesh,
    )
    print(json.dumps(m, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
