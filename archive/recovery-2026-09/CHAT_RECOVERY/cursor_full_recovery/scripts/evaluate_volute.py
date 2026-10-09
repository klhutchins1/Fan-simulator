"""Evaluate one volute / radial blower (radial MRF domain, free + load).

Usage:
    uv run python scripts/evaluate_volute.py [--out-dir DIR] [--load-pa PA]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.runner import image_available  # noqa: E402
from fansim.volute.domain import DEFAULT_VOLUTE_RPM  # noqa: E402
from fansim.volute.evaluate import evaluate_volute  # noqa: E402
from fansim.volute.geometry import VoluteParams  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Evaluate a volute / radial blower (sealed-enclosure radial MRF)")
    ap.add_argument("--out-dir", default="build/volute_eval",
                    help="workdir for STL + OpenFOAM case")
    ap.add_argument("--load-pa", type=float, default=50.0,
                    help="system-curve Pa at 50 CFM (default 50)")
    ap.add_argument("--rpm", type=float, default=DEFAULT_VOLUTE_RPM)
    ap.add_argument("--iters", type=int, default=800)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.006)
    ap.add_argument("--mesh-only", action="store_true",
                    help="write case + mesh, skip free/load solves")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2
    out = Path(args.out_dir)
    result = evaluate_volute(
        VoluteParams(),
        out,
        procs=args.procs,
        base_cell=args.base_cell,
        iters=args.iters,
        load_pa=args.load_pa,
        rpm=args.rpm,
        mesh_only=args.mesh_only,
    )
    print(f"\nfeasible={result.feasible}  reason={result.reason!r}")
    print(f"{'metric':<18}value")
    for k in ("cfm_free", "cfm_load", "efficiency", "actual_rpm", "runtime_s"):
        print(f"{k:<18}{getattr(result, k)}")
    print(f"{'topology':<18}{result.raw.get('topology')}")
    print(f"{'honesty':<18}{result.raw.get('honesty')}")
    (out / "result.json").write_text(
        json.dumps(result.to_dict(), indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {out / 'result.json'}")
    if args.mesh_only:
        return 0 if result.raw.get("meshed") else 1
    return 0 if result.feasible else 1


if __name__ == "__main__":
    raise SystemExit(main())
