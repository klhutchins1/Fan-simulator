"""One obj_2 compressible MRF solve with a wall-resolved mesh and prism layers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import trimesh

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.prop_spec import get_prop_spec  # noqa: E402
from fansim.propeller.cfd import evaluate_prop_cfd  # noqa: E402
from fansim.propeller.stl_import import measure_prop_stl, prepare_prop_stl  # noqa: E402
from fansim.propeller.wall_mesh import (  # noqa: E402
    figure_of_merit,
    mesh_for_wall,
    wall_resolved,
    wall_sample,
)

STL = PROJECT / "validation/reference/drone_radial/obj_2_ccw.stl"
SMOKE = PROJECT / "validation/reference/drone_radial/cfd/obj_2_ccw_smoke.json"
STAMP = PROJECT / "validation/reference/drone_radial/cfd/obj_2_ccw_wall.json"
DEFAULT_OUT = PROJECT / "runs/drone_radial_cfd/wall/obj_2"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="obj_2 wall-resolved compressible MRF diagnostic")
    ap.add_argument("--stl", type=Path, default=STL)
    ap.add_argument("--rpm", type=float, default=25257.0)
    ap.add_argument("--spin", type=int, default=-1, choices=(-1, 1))
    ap.add_argument("--base-cell", type=float, default=0.005, dest="base_cell")
    ap.add_argument("--iters", type=int, default=400)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return ap


def _layout_note(sample: dict) -> str:
    note = f"layout={sample['layout']}"
    if sample["faces_outward"]:
        note += "; outer surfaces face outward"
    return note


def run_case(*, stl: Path, rpm: float, spin: int, base_cell: float, iters: int, procs: int, out: Path) -> dict:
    if not stl.is_file():
        raise RuntimeError(f"prop STL not found: {stl}")
    out.mkdir(parents=True, exist_ok=True)
    prepared = out / "prop.stl"
    prepare_prop_stl(stl, prepared)
    mesh_tm = trimesh.load(str(prepared), force="mesh")
    sample = wall_sample(mesh_tm)
    metrics = measure_prop_stl(prepared)
    resolution = mesh_for_wall(base_cell, sample["min_wall_mm"])
    solved = evaluate_prop_cfd(
        get_prop_spec("fpv_5inch"),
        out,
        rpm=rpm,
        iters=iters,
        procs=procs,
        base_cell=base_cell,
        spin=spin,
        stl_mm=prepared,
        prepare_stl=False,
        mesh=resolution,
        spec_key="obj_2_ccw",
    )
    thrust_n = float(solved["thrust_n"])
    power_w = float(solved["shaft_power_w"])
    tip_m = float(metrics.tip_radius_m)
    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    smoke_r = float(smoke["tip_radius_mm"]) / 1000.0
    solved.update(
        {
            "min_wall_mm": sample["min_wall_mm"],
            "abs_min_mm": sample["abs_min_mm"],
            "n_hits": sample["n_hits"],
            "layout": sample["layout"],
            "mean_abs_nr": sample["mean_abs_nr"],
            "mean_abs_nz": sample["mean_abs_nz"],
            "faces_outward": sample["faces_outward"],
            "layout_note": _layout_note(sample),
            "surf_min": resolution.surf_min,
            "surf_max": resolution.surf_max,
            "add_layers": resolution.add_layers,
            "n_surface_layers": resolution.n_surface_layers,
            "wall_resolved": wall_resolved(resolution.base_cell, resolution.surf_max, sample["min_wall_mm"]),
            "figure_of_merit": figure_of_merit(thrust_n, power_w, tip_m),
            "smoke_thrust_g": smoke["metrics"]["thrust_g"],
            "smoke_shaft_power_w": smoke["metrics"]["shaft_power_w"],
            "smoke_figure_of_merit": figure_of_merit(
                smoke["metrics"]["thrust_n"], smoke["metrics"]["shaft_power_w"], smoke_r
            ),
            "stl": str(stl),
        }
    )
    return solved


def _null_payload(message: str) -> dict:
    return {"thrust_g": None, "shaft_power_w": None, "error": message, "band_pass": None}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        payload = run_case(
            stl=args.stl,
            rpm=float(args.rpm),
            spin=int(args.spin),
            base_cell=float(args.base_cell),
            iters=int(args.iters),
            procs=int(args.procs),
            out=args.out,
        )
    except RuntimeError as exc:
        payload = _null_payload(str(exc))
        (args.out / "result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 1
    (args.out / "result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    thrust = payload.get("thrust_g")
    power = payload.get("shaft_power_w")
    if thrust is not None and power is not None and thrust == thrust and power == power:
        STAMP.parent.mkdir(parents=True, exist_ok=True)
        STAMP.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
