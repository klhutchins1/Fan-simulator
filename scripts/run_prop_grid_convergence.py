"""Honest 3-level open-air GCI ladder for prop STLs (roadmap §4.3).

Usage:
    uv run python scripts/run_prop_grid_convergence.py \\
      --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \\
      --rpm 38100 --out runs/drone_radial_cfd/gci/obj_1

    uv run python scripts/run_prop_grid_convergence.py --both
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cfd.runner import image_available  # noqa: E402
from fansim.prop_spec import get_prop_spec  # noqa: E402
from fansim.propeller.cfd_fixture import force_z_tail_drift_pct  # noqa: E402
from fansim.propeller.gci_ladder import build_gci_summary, parse_cells  # noqa: E402
from fansim.propeller.stl_import import spin_hint_from_name  # noqa: E402

BOTH = (
    {
        "stl": PROJECT / "validation/reference/drone_radial/obj_1_ccw_impeller.stl",
        "rpm": 38100.0,
        "out": PROJECT / "runs/drone_radial_cfd/gci/obj_1",
    },
    {
        "stl": PROJECT / "validation/reference/drone_radial/obj_2_ccw.stl",
        "rpm": 25257.0,
        "out": PROJECT / "runs/drone_radial_cfd/gci/obj_2",
    },
)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Prop open-air GCI mesh ladder")
    ap.add_argument("--stl", type=Path, default=None)
    ap.add_argument("--rpm", type=float, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--cells", default="0.005,0.0035,0.0025")
    ap.add_argument("--iters", type=int, default=800)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--spec", default="fpv_5inch", help="PropSpec key for stamps only")
    ap.add_argument("--force", action="store_true", help="re-solve even if result.json exists")
    ap.add_argument("--both", action="store_true", help="run obj_1 then obj_2 at locked RPMs")
    return ap


def _spin_for(stl: Path) -> int:
    hint = spin_hint_from_name(stl.name)
    return int(hint if hint is not None else -1)


def _rung_done(result_path: Path) -> bool:
    if not result_path.is_file():
        return False
    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
        tg = float(data["thrust_g"])
        return math.isfinite(tg)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_ladder(
    *,
    stl: Path,
    rpm: float,
    out: Path,
    cells: list[float],
    iters: int,
    procs: int,
    spec_key: str,
    force: bool,
) -> dict:
    from fansim.propeller.cfd import evaluate_prop_cfd

    spec = get_prop_spec(spec_key)
    spin = _spin_for(stl)
    out.mkdir(parents=True, exist_ok=True)
    levels: list[dict] = []

    for h in cells:
        rung = out / f"{h:g}"
        rung.mkdir(parents=True, exist_ok=True)
        result_path = rung / "result.json"
        level: dict = {"base_cell": float(h), "workdir": str(rung)}
        try:
            if force or not _rung_done(result_path):
                if not image_available():
                    raise RuntimeError("OpenFOAM Docker image not available")
                data = evaluate_prop_cfd(
                    spec,
                    rung,
                    rpm=float(rpm),
                    iters=int(iters),
                    procs=int(procs),
                    base_cell=float(h),
                    spec_key=spec_key,
                    stl_mm=stl,
                    spin=spin,
                )
                result_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            else:
                data = json.loads(result_path.read_text(encoding="utf-8"))
            level["thrust_g"] = float(data["thrust_g"])
            level["shaft_power_w"] = data.get("shaft_power_w")
            level["tip_mach"] = data.get("tip_mach")
            try:
                level["force_tail_drift_pct"] = force_z_tail_drift_pct(rung)
            except (OSError, ValueError, FileNotFoundError):
                level["force_tail_drift_pct"] = None
            level["ok"] = math.isfinite(float(level["thrust_g"]))
            if not level["ok"]:
                level["error"] = "non-finite thrust_g"
        except Exception as exc:  # noqa: BLE001 — rung isolation
            level["ok"] = False
            level["thrust_g"] = None
            level["error"] = str(exc)
        levels.append(level)

    summary = build_gci_summary(
        stl=str(stl), rpm=float(rpm), iters=int(iters), levels=levels,
    )
    summary_path = out.parent / f"{out.name}_gci_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    args = build_parser().parse_args()
    cells = parse_cells(args.cells)

    jobs = []
    if args.both:
        jobs = list(BOTH)
    else:
        if args.stl is None or args.rpm is None or args.out is None:
            print("ERROR: need --stl --rpm --out (or --both)", file=sys.stderr)
            return 2
        jobs = [{"stl": args.stl, "rpm": float(args.rpm), "out": args.out}]

    rc = 0
    for job in jobs:
        stl = Path(job["stl"])
        if not stl.is_file():
            print(f"ERROR: STL not found: {stl}", file=sys.stderr)
            rc = 2
            continue
        try:
            run_ladder(
                stl=stl,
                rpm=float(job["rpm"]),
                out=Path(job["out"]),
                cells=cells,
                iters=int(args.iters),
                procs=int(args.procs),
                spec_key=args.spec,
                force=bool(args.force),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: ladder failed for {stl}: {exc}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
