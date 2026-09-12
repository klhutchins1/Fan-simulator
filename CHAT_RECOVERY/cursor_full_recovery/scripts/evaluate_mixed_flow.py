"""Score one mixed-flow impeller in the axial A12x25 MRF duct (free + load).

Usage:
    uv run python scripts/evaluate_mixed_flow.py [--out-dir DIR] [--load-pa PA]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.centrifugal.evaluate import evaluate_mixed_flow  # noqa: E402
from fansim.centrifugal.geometry import MixedFlowParams  # noqa: E402
from fansim.cfd.runner import image_available  # noqa: E402
from fansim.optimize.presets import resolve_load  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Evaluate a mixed-flow impeller (axial MRF duct, free + load CFD)")
    ap.add_argument("--out-dir", default="build/mixed_flow_eval",
                    help="workdir for STL + OpenFOAM case")
    ap.add_argument("--load-pa", type=float, default=None,
                    help="system-curve Pa at 50 CFM (default 1.0)")
    ap.add_argument("--preset", default=None, help="hose preset name (optional)")
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--refine-op", action="store_true",
                    help="third RANS at the predicted operating pressure")
    ap.add_argument("--bem-prescreen", type=float, default=0.0, metavar="CFM_FLOOR",
                    help="skip CFD when the axial-adapter BEM system-curve op CFM is below "
                         "CFM_FLOOR (approximate mixed-flow screen). 0 = off.")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2
    load_pa, preset_name = resolve_load(args.preset, args.load_pa)
    if preset_name:
        print(f"preset={preset_name} load_pa={load_pa:g}")
    out = Path(args.out_dir)
    result = evaluate_mixed_flow(
        MixedFlowParams(),
        out,
        procs=args.procs,
        base_cell=args.base_cell,
        iters=args.iters,
        load_pa=load_pa,
        refine_op=args.refine_op,
        bem_prescreen_cfm=args.bem_prescreen,
    )
    print(f"\nfeasible={result.feasible}  reason={result.reason!r}")
    print(f"{'metric':<18}value")
    for k in ("cfm_free", "cfm_load", "efficiency", "actual_rpm", "runtime_s"):
        print(f"{k:<18}{getattr(result, k)}")
    print(f"{'topology':<18}{result.raw.get('topology')}")
    (out / "result.json").write_text(
        json.dumps(result.to_dict(), indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {out / 'result.json'}")
    return 0 if result.feasible else 1


if __name__ == "__main__":
    raise SystemExit(main())
