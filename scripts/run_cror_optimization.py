"""CROR NSGA screen (BEMT proxy) + optional thin-to-25mm report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cror.geometry import CrorParams  # noqa: E402
from fansim.cror.optimize import (  # noqa: E402
    cror_stack_depth_mm,
    run_cror_study,
    thin_cror_for_frame,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="CROR NSGA stage 1 (BEMT proxy, thin envelope)")
    ap.add_argument("--trials", type=int, default=60)
    ap.add_argument("--rpm", type=float, default=2000.0)
    ap.add_argument("--max-depth", type=float, default=25.0)
    ap.add_argument("--out", type=Path, default=Path("runs/cror_nsga"))
    ap.add_argument(
        "--thin-default",
        action="store_true",
        help="only report default vs thinned stack depth (no Optuna)",
    )
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.thin_default:
        raw = CrorParams()
        thin = thin_cror_for_frame(raw, max_depth_mm=args.max_depth)
        payload = {
            "default_depth_mm": cror_stack_depth_mm(raw),
            "thinned_depth_mm": cror_stack_depth_mm(thin),
            "max_depth_mm": args.max_depth,
            "thinned_gap_mm": thin.axial_gap_mm,
        }
        (args.out / "thin.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    _study, pareto = run_cror_study(
        args.trials, rpm=args.rpm, max_depth_mm=args.max_depth,
    )
    payload = {"n_trials": args.trials, "rpm": args.rpm, "max_depth_mm": args.max_depth,
               "pareto": pareto}
    (args.out / "pareto.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"n_pareto": len(pareto), "top": pareto[:3]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
