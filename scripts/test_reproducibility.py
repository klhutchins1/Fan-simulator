"""Measure screening reproducibility: evaluate the SAME design N times, report the spread.

If nominally-identical evaluations of one design scatter, the screening pipeline cannot rank
designs reliably — the deepest threat flagged by the adversarial review.

Usage:
    uv run python scripts/test_reproducibility.py --base-json runs/opt_run1/pareto.json \
        --base-trial 2 --repeats 3 --iters 700 --base-cell 0.005
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
from fansim.optimize.objectives import evaluate_candidate  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="screening reproducibility probe")
    ap.add_argument("--base-json", required=True)
    ap.add_argument("--base-trial", type=int, required=True)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--iters", type=int, default=700)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--load-pa", type=float, default=2.0)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/repro")
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM image not found.")
        return 2

    pareto = json.loads(Path(args.base_json).read_text())
    row = next(r for r in pareto if r["trial"] == args.base_trial)
    params = blade_from_flat(row["params"])
    out = Path(args.out)
    t0 = time.time()
    print(f"Reproducibility: trial {args.base_trial} (nB={params.n_blades}) x{args.repeats} "
          f"@ base_cell={args.base_cell}, iters={args.iters}, load={args.load_pa} Pa")

    rows = []
    for i in range(args.repeats):
        r = evaluate_candidate(params, out / f"rep_{i}", procs=args.procs,
                               base_cell=args.base_cell, iters=args.iters, load_pa=args.load_pa)
        conv = r.raw.get("converged") if r.raw else None
        rows.append({"rep": i, "cfm_free": r.cfm_free, "cfm_load": r.cfm_load,
                     "eff": r.efficiency, "converged": conv})
        print(f"  rep {i}: cfm_free={r.cfm_free:6.1f}  cfm_load={r.cfm_load:6.1f}  "
              f"eff={r.efficiency:5.1f}%  converged={conv}  ({r.runtime_s:.0f}s)", flush=True)

    loads = [r["cfm_load"] for r in rows]
    spread = max(loads) - min(loads)
    rel = spread / (sum(loads) / len(loads) + 1e-9) * 100
    verdict = (f"NON-REPRODUCIBLE: cfm_load spans {min(loads):.1f}–{max(loads):.1f} "
               f"({rel:.0f}%) across identical runs — screening rankings unreliable."
               if rel > 5 else
               f"reproducible: cfm_load {min(loads):.1f}–{max(loads):.1f} ({rel:.1f}%).")
    print(f"  => {verdict}")
    (out / "repro.json").write_text(json.dumps({"rows": rows, "verdict": verdict}, indent=2),
                                    encoding="utf-8")
    print(f"-> {out/'repro.json'}  (total {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
