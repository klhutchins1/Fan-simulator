"""One compressible AMI smoke on obj_2 (roadmap §4.3).

Usage:
    uv run python scripts/run_prop_ami_smoke.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cfd.openfoam_case import MeshResolution  # noqa: E402
from fansim.cfd.runner import DEFAULT_IMAGE, OpenFOAMRunner, image_available  # noqa: E402
from fansim.propeller.ami_smoke import (  # noqa: E402
    DELTA_T,
    ami_exit_code,
    apply_ami_overlay,
    end_time_s,
    read_force_rows,
    result_is_resumable,
    run_mesh_ami,
    run_solve_ami,
    summary_from_rows,
)
from fansim.propeller.cfd import _turb_from_u, build_prop_case, prop_open_air  # noqa: E402
from fansim.propeller.stl_import import measure_prop_stl, prepare_prop_stl  # noqa: E402

DEFAULT_STL = PROJECT / "validation/reference/drone_radial/obj_2_ccw.stl"
DEFAULT_OUT = PROJECT / "runs/drone_radial_cfd/ami/obj_2"
STAMP = PROJECT / "validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json"
SPIN = -1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="obj_2 compressible AMI smoke")
    ap.add_argument("--stl", type=Path, default=DEFAULT_STL)
    ap.add_argument("--rpm", type=float, default=25257.0)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005, dest="base_cell")
    ap.add_argument("--force", action="store_true")
    return ap


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _maybe_stamp(stl: Path, rpm: float, payload: dict) -> None:
    mean = payload.get("mean_thrust_g")
    if mean is None:
        return
    if stl.name != "obj_2_ccw.stl" or abs(float(rpm) - 25257.0) > 1e-6:
        return
    _write_json(STAMP, payload)


def run_case(stl: Path, rpm: float, out: Path, procs: int, base_cell: float) -> dict:
    if not image_available(DEFAULT_IMAGE):
        raise RuntimeError(f"Docker image not available: {DEFAULT_IMAGE}")
    out.mkdir(parents=True, exist_ok=True)
    prepared = out / "prop.stl"
    prepare_prop_stl(stl, prepared)
    metrics = measure_prop_stl(prepared)
    from fansim.geometry import watertight_report

    rep = watertight_report(prepared)
    (_, _, z0), (_, _, z1) = rep.bounds_mm
    dom = prop_open_air(
        metrics.tip_radius_m,
        z0 / 1000.0,
        z1 / 1000.0,
        rpm=rpm,
        spin=SPIN,
    )
    build_prop_case(
        out,
        prepared,
        dom,
        mesh=MeshResolution(base_cell=float(base_cell)),
        n_iters=100,
        n_subdomains=int(procs),
    )
    k, omega_turb = _turb_from_u(dom.u_freestream, dom.tip_radius)
    apply_ami_overlay(
        out,
        omega_signed=dom.omega_signed,
        ami_radius=1.05 * dom.tip_radius,
        ami_z_min=dom.mrf_z_min,
        ami_z_max=dom.mrf_z_max,
        end_time=end_time_s(rpm),
        delta_t=DELTA_T,
        u_freestream=dom.u_freestream,
        k=k,
        omega_turb=omega_turb,
    )
    runner = OpenFOAMRunner(out)
    run_mesh_ami(runner)
    run_solve_ami(runner, n_procs=int(procs))
    rows = read_force_rows(out)
    return summary_from_rows(
        rows,
        stl=str(stl),
        rpm=rpm,
        base_cell=base_cell,
        reason="mean window has zero samples",
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stl = Path(args.stl)
    out = Path(args.out)
    result_path = out / "result.json"
    if result_is_resumable(result_path) and not args.force:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        print(json.dumps(payload, indent=2))
        return ami_exit_code(payload)
    if not stl.is_file():
        print(f"ERROR: STL not found: {stl}", file=sys.stderr)
        return 1
    try:
        payload = run_case(stl, float(args.rpm), out, int(args.procs), float(args.base_cell))
    except RuntimeError as exc:
        payload = summary_from_rows(
            [],
            stl=str(stl),
            rpm=float(args.rpm),
            base_cell=float(args.base_cell),
            reason=str(exc),
        )
        _write_json(result_path, payload)
        print(json.dumps(payload, indent=2))
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    _write_json(result_path, payload)
    _maybe_stamp(stl, float(args.rpm), payload)
    print(json.dumps(payload, indent=2))
    return ami_exit_code(payload)


if __name__ == "__main__":
    raise SystemExit(main())
