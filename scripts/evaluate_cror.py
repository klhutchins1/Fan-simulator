"""Smoke / CLI for CROR dual-MRF evaluate.

Default stack is ~33 mm deep — too thick for A12x25 (25 mm). Smoke defaults to
``delta_afc1212de`` (38 mm envelope). Override with ``--spec``.

Usage:
    uv run python scripts/evaluate_cror.py [--out runs/cror_smoke] [--procs 8]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cror.evaluate import evaluate_cror  # noqa: E402
from fansim.cror.geometry import CrorParams  # noqa: E402
from fansim.cfd.runner import image_available  # noqa: E402
from fansim.fan_spec import get_fan_spec  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="CROR dual-MRF evaluate (stage 1)")
    ap.add_argument("--out", type=Path, default=Path("runs/cror_smoke"))
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--iters", type=int, default=800)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--load-pa", type=float, default=8.0)
    ap.add_argument(
        "--spec", default="delta_afc1212de",
        help="fan envelope key (default delta_afc1212de — CROR needs depth ≳33 mm)",
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="write dual-MRF case dicts only (no Docker solve)")
    args = ap.parse_args()

    spec = get_fan_spec(args.spec)
    params = CrorParams()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        from fansim.cror.evaluate import prepare_cror_cfd, remaining_cror_tip_gap_mm, rig_for_cror
        from fansim.cfd.openfoam_case import MeshResolution, build_case
        from fansim.cror.geometry import export_cror_stl
        casing_id = float(spec.tip_dia_mm[1])
        stl = export_cror_stl(params, args.out / "impeller.stl")
        rig = rig_for_cror(
            params, tip_gap_mm=remaining_cror_tip_gap_mm(params, casing_id),
            casing_id_mm=casing_id, rpm=spec.rpm)
        stl, rig, dmrf = prepare_cror_cfd(params, stl, rig, args.out)
        build_case(args.out / "case", stl, rig, mesh=MeshResolution(base_cell=args.base_cell),
                   n_iters=args.iters, n_subdomains=args.procs, back_pressure_pa=0.0,
                   dual_mrf=dmrf)
        payload = {
            "dry_run": True, "spec": args.spec, "dual_mrf": dmrf,
            "case": str(args.out / "case"),
        }
        (args.out / "dry_run.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    if not image_available():
        print("ERROR: OpenFOAM Docker image not available", file=sys.stderr)
        return 2

    res = evaluate_cror(
        params, args.out,
        spec=spec,
        load_pa=args.load_pa,
        iters=args.iters,
        procs=args.procs,
        base_cell=args.base_cell,
    )
    out = {
        "feasible": res.feasible,
        "reason": res.reason,
        "spec": args.spec,
        "cfm_free": res.cfm_free,
        "cfm_load": res.cfm_load,
        "efficiency": res.efficiency,
        "runtime_s": res.runtime_s,
        "raw_rotation": (res.raw or {}).get("rotation"),
        "dual_mrf": (res.raw or {}).get("dual_mrf"),
    }
    (args.out / "result.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if res.feasible else 1


if __name__ == "__main__":
    raise SystemExit(main())
