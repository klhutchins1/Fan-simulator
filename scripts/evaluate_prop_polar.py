"""BEMT forward-flight polar for a prop spec.

Usage:
    uv run python scripts/evaluate_prop_polar.py [--out runs/prop_bemt_polar]
    uv run python scripts/evaluate_prop_polar.py --v-inf 0,5,10,15 --j 0.2,0.4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.prop_spec import get_prop_spec  # noqa: E402
from fansim.propeller.geometry import prop_blade_params  # noqa: E402
from fansim.propeller.polar import (  # noqa: E402
    parse_float_list,
    resolve_sweep,
    run_bemt_polar,
    write_polar_artifacts,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Prop BEMT forward-flight polar")
    ap.add_argument("--out", type=Path, default=Path("runs/prop_bemt_polar"))
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
    blade = prop_blade_params(spec)
    points = run_bemt_polar(blade, rpm, v_infs, diameter_m=diameter_m)
    meta = {
        "spec": args.spec,
        "rpm": rpm,
        "tip_mach": spec.tip_mach(rpm),
        "source": "bemt",
        "v_inf": v_infs,
    }
    csv_path, json_path = write_polar_artifacts(args.out, points, meta=meta)
    print(json.dumps({"meta": meta, "csv": str(csv_path), "json": str(json_path),
                      "n_points": len(points)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
