"""Do WINGLETS help? — CFD test + directions.

Curling the blade tip (a winglet) can cut tip-leakage losses on real fans and props — or just add drag.
This runs real CFD on a base design vs several winglet configs, laid out so the deltas ISOLATE the two
knobs: axial sweep (tip curls up/forward) and circumferential lean (tip wraps around the axis). Reading
sweep-only vs lean-only vs both tells you which direction to push.

Depth leeway is relaxed for the study (a curled tip reaches further in Z and would otherwise be gated),
so we measure the pure aero effect; a real design would still have to fit the 25 mm frame.

Usage:  uv run python scripts/run_winglet_study.py --design-id opt_extended2_t36 --out runs/winglet_study
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.runner import image_available  # noqa: E402
from fansim.fan_spec import A12X25  # noqa: E402
from fansim.catalog import get_entry  # noqa: E402
from fansim.optimize.objectives import evaluate_candidate  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402

_t0 = time.time()
# (label, winglet_sweep mm, winglet_lean deg) — factorial-ish to isolate each knob's direction.
CONFIGS = [
    ("control (none)", 0.0, 0.0),
    ("sweep only", 8.0, 0.0),
    ("lean only", 0.0, 15.0),
    ("both mild", 5.0, 8.0),
    ("both strong", 10.0, 20.0),
]
SPAN = 0.85


def main() -> int:
    ap = argparse.ArgumentParser(description="winglet CFD study")
    ap.add_argument("--design-id", required=True)
    ap.add_argument("--out", default="runs/winglet_study")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--iters", type=int, default=1000)
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2

    e = get_entry(args.design_id)
    if e is None:
        print(f"'{args.design_id}' not in the catalog. Run `catalog build`.")
        return 2
    flat = e.params
    spec = dataclasses.replace(A12X25, leeway_depth_mm=20.0)   # let curled tips run (measure aero, not fit)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"[base] {args.design_id}, nB={flat.get('n_blades')} — winglet directions (depth leeway on)", flush=True)

    results = []
    for label, sw, ln in CONFIGS:
        f = dict(flat)
        if sw or ln:
            f.update(winglet_span=SPAN, winglet_sweep=sw, winglet_lean=ln)
        params = blade_from_flat(f)
        res = evaluate_candidate(params, out / label.split()[0], procs=args.procs,
                                 base_cell=args.base_cell, iters=args.iters, spec=spec)
        rec = {"label": label, "winglet_sweep": sw, "winglet_lean": ln,
               "feasible": res.feasible, "cfm_free": round(res.cfm_free, 1),
               "cfm_load": round(res.cfm_load, 1), "efficiency": round(res.efficiency, 1),
               "reason": res.reason}
        results.append(rec)
        tag = "OK  " if res.feasible else "GATE"
        print(f"  {label:16s} sw={sw:>4} ln={ln:>4}: {tag} "
              + (f"cfm {res.cfm_free:6.1f}/{res.cfm_load:6.1f}  eff {res.efficiency:5.1f}%"
                 if res.feasible else res.reason)
              + f"  (wall {time.time()-_t0:.0f}s)", flush=True)

    (out / "winglet_verdict.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    ctrl = next((r for r in results if r["winglet_sweep"] == 0 and r["winglet_lean"] == 0), None)
    print("\n===== WINGLET DIRECTIONS (vs control) =====")
    if ctrl and ctrl["feasible"]:
        print(f"  control: cfm {ctrl['cfm_free']}/{ctrl['cfm_load']}  eff {ctrl['efficiency']}%")
        best = None
        for r in results:
            if r is ctrl or not r["feasible"]:
                continue
            df, dl, de = (r["cfm_free"] - ctrl["cfm_free"], r["cfm_load"] - ctrl["cfm_load"],
                          r["efficiency"] - ctrl["efficiency"])
            print(f"  {r['label']:16s}: cfm {df:+.1f}/{dl:+.1f}  eff {de:+.1f}")
            score = df + dl + de
            if best is None or score > best[1]:
                best = (r["label"], score, df, de)
        if best and (best[2] > 0.5 or best[3] > 0.5):
            print(f"\n  => DIRECTION: '{best[0]}' is the best move (+{best[2]:.1f} CFM, {best[3]:+.1f}% eff). "
                  "Push further that way.")
        else:
            print("\n  => No winglet config beat the plain tip (winglets don't help this design here).")
    print(f"  -> {out/'winglet_verdict.json'}  (total {time.time()-_t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
