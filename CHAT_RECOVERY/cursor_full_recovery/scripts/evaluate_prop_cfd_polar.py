"""CFD forward-flight polar for a prop (mesh once, re-solve per V∞).

Primary stage-1 polar product. Slow / Docker-heavy.

Usage:
    uv run python scripts/evaluate_prop_cfd_polar.py [--out runs/prop_cfd_polar]
    uv run python scripts/evaluate_prop_cfd_polar.py --v-inf 0,10,20 --iters 200
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cfd.runner import image_available  # noqa: E402
from fansim.prop_spec import get_prop_spec  # noqa: E402
from fansim.propeller.polar import (  # noqa: E402
    parse_float_list,
    resolve_sweep,
    run_cfd_polar,
    write_polar_artifacts,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Prop compressible CFD forward-flight polar (mesh once, re-solve)"
    )
    ap.add_argument("--out", type=Path, default=Path("runs/prop_cfd_polar"))
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--iters", type=int, default=400)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument(
        "--bemt-floor",
        type=float,
        default=0.0,
        help="skip CFD if static BEMT thrust_g < this floor (default 0 = off)",
    )
    ap.add_argument("--spec", default="fpv_5inch", help="prop spec key (default fpv_5inch)")
    ap.add_argument("--rpm", type=float, default=None, help="RPM (default 0.7 * rpm_max)")
    ap.add_argument(
        "--v-inf",
        default=None,
        help="comma-separated freestream speeds [m/s] (default 0,5,10,15,20)",
    )
    ap.add_argument(
        "--j",
        default=None,
        help="comma-separated advance ratios J (converted to V∞ and merged with --v-inf)",
    )
    ap.add_argument(
        "--no-hover",
        action="store_true",
        help="do not force-include V∞=0 when absent from the sweep",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve sweep + write empty polar skeleton (no Docker)",
    )
    args = ap.parse_args()

    spec = get_prop_spec(args.spec)
    rpm = float(0.7 * spec.rpm_max if args.rpm is None else args.rpm)
    diameter_m = float(spec.diameter_mm) / 1000.0
    v_infs = resolve_sweep(
        v_inf=parse_float_list(args.v_inf),
        j=parse_float_list(args.j),
        rpm=rpm,
        diameter_m=diameter_m,
        include_hover=not args.no_hover,
    )
    args.out.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        meta = {
            "dry_run": True,
            "spec": args.spec,
            "rpm": rpm,
            "tip_mach": spec.tip_mach(rpm),
            "source": "cfd",
            "v_inf": v_infs,
            "solver": "rhoSimpleFoam",
            "domain": "open_air",
            "regime": "compressible-MRF",
        }
        csv_path, json_path = write_polar_artifacts(args.out, [], meta=meta)
        print(json.dumps({"meta": meta, "csv": str(csv_path), "json": str(json_path)}, indent=2))
        return 0

    if not image_available():
        print("OpenFOAM Docker image not available", file=sys.stderr)
        return 2

    result = run_cfd_polar(
        spec,
        args.out,
        v_infs,
        rpm=rpm,
        iters=args.iters,
        procs=args.procs,
        base_cell=args.base_cell,
        spec_key=args.spec,
        bemt_floor_g=args.bemt_floor,
    )
    if result.get("skipped"):
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0

    meta = {k: v for k, v in result.items() if k != "points"}
    meta["v_inf"] = v_infs
    meta["source"] = "cfd"
    csv_path, json_path = write_polar_artifacts(args.out, result["points"], meta=meta)
    summary = {"meta": meta, "csv": str(csv_path), "json": str(json_path),
               "n_points": len(result["points"])}
    (args.out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
