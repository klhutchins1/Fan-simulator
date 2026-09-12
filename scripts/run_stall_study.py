# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Near-stall feature test: do leading-edge tubercles DELAY STALL (sustain flow to higher
back-pressure) vs a smooth blade?

The flat feature-isolation study ran on the STABLE curve (1 Pa) and found features neutral on flow —
expected, since tubercles/serrations are stall-delay + noise devices, not bulk-flow devices. This
sweeps back-pressure INTO the stall region on the same base geometry for a few feature variants and
compares where flow collapses. If tubercles delay stall, the tubercled blade holds more flow at high
back-pressure than smooth.

HONEST CAVEAT: steady RANS does NOT converge near stall (flow is inherently unsteady there) — points
are flagged UNCONVERGED and are limit-cycle averages at best. A rigorous stall test needs transient
(URANS/LBM). Read this as a suggestive relative comparison under a consistent (imperfect) method.

Usage:  uv run python scripts/run_stall_study.py --base-json runs/opt_extended2/pareto.json
            --base-trial 36 --out runs/stall_study [--procs 8]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.runner import image_available  # noqa: E402
from fansim.geometry.features import Features  # noqa: E402
from fansim.optimize.objectives import evaluate_candidate  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402

_t0 = time.time()

VARIANTS = {
    "smooth": Features(),
    "tubercles": Features(tubercle_amp=0.08, tubercle_waves=6),          # the stall-delay feature
    "tub+serr": Features(tubercle_amp=0.08, tubercle_waves=6,
                         serration_amp=0.05, serration_waves=8),
}
BACK_PRESSURES = [2.0, 3.0, 4.0, 5.0]   # Pa — beyond the stable 1 Pa, into near-stall


def main() -> int:
    ap = argparse.ArgumentParser(description="near-stall (stall-delay) feature comparison")
    ap.add_argument("--base-json", required=True)
    ap.add_argument("--base-trial", type=int, required=True)
    ap.add_argument("--out", default="runs/stall_study")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--iters", type=int, default=1000)
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pareto = json.loads(Path(args.base_json).read_text())
    row = next(r for r in pareto if r["trial"] == args.base_trial)
    flat = row["params"]
    print(f"[base] trial {args.base_trial} nB={flat.get('n_blades')} — sweeping back-pressure per variant")
    sys.stdout.flush()

    results: dict[str, list[dict]] = {}
    for vname, feat in VARIANTS.items():
        results[vname] = []
        for bp in BACK_PRESSURES:
            params = blade_from_flat(flat, feat)
            wd = out / f"{vname}_bp{bp:g}"
            res = evaluate_candidate(params, wd, procs=args.procs, base_cell=args.base_cell,
                                     iters=args.iters, load_pa=bp)
            conv = "conv" if "UNCONV" not in (res.reason or "").upper() else "UNCONV"
            row_r = {"variant": vname, "back_pa": bp, "cfm_load": round(res.cfm_load, 2),
                     "feasible": res.feasible, "converged": conv == "conv", "reason": res.reason}
            results[vname].append(row_r)
            print(f"  {vname:9s} bp={bp:g}Pa -> cfm_load {res.cfm_load:6.1f}  {conv}  "
                  f"({res.runtime_s:.0f}s, wall {time.time()-_t0:.0f}s)")
            sys.stdout.flush()

    (out / "stall_verdict.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("\n===== STALL-DELAY COMPARISON (cfm_load vs back-pressure; higher = more stall margin) =====")
    header = "  back-Pa | " + " | ".join(f"{v:>10s}" for v in VARIANTS)
    print(header)
    for i, bp in enumerate(BACK_PRESSURES):
        cells = []
        for v in VARIANTS:
            r = results[v][i]
            flag = "" if r["converged"] else "~"
            cells.append(f"{r['cfm_load']:>9.1f}{flag}")
        print(f"  {bp:>6g} | " + " | ".join(cells))
    print("  (~ = unconverged near-stall point; compare TRENDS, not absolute values)")
    print(f"  -> {out/'stall_verdict.json'}  (total {time.time()-_t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
