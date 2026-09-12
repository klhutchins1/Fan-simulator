#!/usr/bin/env python3
"""CFD-refine top-N mixed BEM Pareto finalists (roadmap §8.7 leftover).

Reads ``pareto.json`` from a ``cockpit_mf_opt_*`` (or any mixed_pareto) folder,
runs ``evaluate_mixed_flow`` on the first N rows, writes ``cfd_refine.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fansim.centrifugal.optimize import refine_pareto_cfd
from fansim.centrifugal.persist import load_mixed_pareto
from fansim.optimize.presets import resolve_load


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pareto-dir", type=Path, required=True,
                    help="folder with pareto.json (e.g. runs/cockpit_mf_opt_*)")
    ap.add_argument("--n-top", type=int, default=3, metavar="N",
                    help="refine first N Pareto rows (default 3)")
    ap.add_argument("--out", type=Path, default=None,
                    help="CFD work root (default: <pareto-dir>/cfd_refine)")
    ap.add_argument("--preset", choices=["case", "heatsink", "radiator"], default=None)
    ap.add_argument("--load-pa", type=float, default=None)
    ap.add_argument("--bem-prescreen", type=float, default=0.0, metavar="CFM_FLOOR")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--base-cell", type=float, default=0.005)
    args = ap.parse_args(argv)

    pareto = load_mixed_pareto(args.pareto_dir)
    if not pareto:
        print(f"ERROR: no pareto rows in {args.pareto_dir}")
        return 2
    load_pa, _ = resolve_load(args.preset, args.load_pa)
    out = args.out or (Path(args.pareto_dir) / "cfd_refine")
    print(f"refining top {args.n_top} of {len(pareto)} → {out}  (load_pa={load_pa:g})")
    rows = refine_pareto_cfd(
        pareto,
        out,
        n_top=int(args.n_top),
        load_pa=float(load_pa),
        bem_prescreen_cfm=float(args.bem_prescreen),
        procs=int(args.procs),
        iters=int(args.iters),
        base_cell=float(args.base_cell),
    )
    ok = sum(1 for r in rows if not r.get("skipped"))
    print(json.dumps({"n": len(rows), "feasible": ok, "out": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
