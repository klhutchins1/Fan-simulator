"""Isolate the effect of bio-inspired features on a fixed base blade.

Takes a base design (e.g. the winner of a geometry optimization), evaluates it SMOOTH as a
control, then searches only the feature layer (tubercles/serrations/dimples) on that exact
geometry. Any change vs the control is attributable to the features -- the scientific-method
test of whether the golf-ball-dimple idea actually helps this fan.

Usage:
    uv run --extra optim --extra viz python scripts/run_feature_study.py \
        --base-json runs/opt_run1/pareto.json --base-trial 2 --trials 20 --out runs/feat_study
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
from fansim.optimize.search_space import OBJECTIVE_NAMES, blade_from_flat  # noqa: E402
from fansim.optimize.study import pareto_summary, run_study  # noqa: E402

_t0 = time.time()


def _progress(trial, params, result):
    f = params.features
    tag = "OK  " if result.feasible else "GATE"
    feat = (f"tub({f.tubercle_amp:.2f},{f.tubercle_waves}) "
            f"ser({f.serration_amp:.2f},{f.serration_waves}) "
            f"dim({f.dimple_amp:.2f},{f.dimple_rows}x{f.dimple_cols})")
    obj = (f"cfm_free={result.cfm_free:6.1f} cfm_load={result.cfm_load:6.1f} "
           f"eff={result.efficiency:5.1f}%") if result.feasible else result.reason
    print(f"[trial {trial.number:03d}] {tag} {obj}  [{feat}] "
          f"({result.runtime_s:.0f}s, wall {time.time()-_t0:.0f}s)")
    sys.stdout.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description="fansim feature-isolation study")
    ap.add_argument("--base-json", required=True, help="pareto.json from a geometry run")
    ap.add_argument("--base-trial", type=int, required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--out", default="runs/feat_study")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--iters", type=int, default=1000)   # plateau by ~500; 1000 = safety
    ap.add_argument("--load-pa", type=float, default=1.0)  # 1 Pa = STABLE curve (2 Pa is near-stall,
    #                                                        non-convergent -> voided earlier rankings)
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # --- Reconstruct the base (smooth) design ---
    pareto = json.loads(Path(args.base_json).read_text())
    row = next(r for r in pareto if r["trial"] == args.base_trial)
    base = blade_from_flat(row["params"])  # features off
    print(f"[base] trial {args.base_trial}, nB={base.n_blades} (smooth control)")

    # --- Control: evaluate the smooth base at finer fidelity ---
    ctrl = evaluate_candidate(base, out / "control", procs=args.procs,
                              base_cell=args.base_cell, iters=args.iters, load_pa=args.load_pa)
    print(f"[control] cfm_free={ctrl.cfm_free:.1f} cfm_load={ctrl.cfm_load:.1f} "
          f"eff={ctrl.efficiency:.1f}%  ({ctrl.runtime_s:.0f}s)")
    sys.stdout.flush()

    # --- Feature-only search on the fixed base geometry ---
    study = run_study(args.trials, out, study_name="features", procs=args.procs,
                      base_cell=args.base_cell, iters=args.iters, load_pa=args.load_pa,
                      base_params=base, on_trial=_progress)

    pareto_feat = pareto_summary(study)
    control = {n: getattr(ctrl, n) for n in OBJECTIVE_NAMES}
    verdict = {"control": control, "featured_pareto": pareto_feat}
    (out / "feature_verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")

    print(f"\n===== FEATURE VERDICT (vs smooth control) =====")
    print(f"  control:  cfm_free={control['cfm_free']:.1f}  "
          f"cfm_load={control['cfm_load']:.1f}  eff={control['efficiency']:.1f}%")
    improved = False
    for r in pareto_feat:
        d_free = r["cfm_free"] - control["cfm_free"]
        d_load = r["cfm_load"] - control["cfm_load"]
        d_eff = r["efficiency"] - control["efficiency"]
        if d_free > 0.5 or d_load > 0.5 or d_eff > 0.5:
            improved = True
        print(f"  trial {r['trial']:3d}: cfm_free {r['cfm_free']:.1f} ({d_free:+.1f})  "
              f"cfm_load {r['cfm_load']:.1f} ({d_load:+.1f})  eff {r['efficiency']:.1f}% "
              f"({d_eff:+.1f})")
    print("  => features HELPED on the Pareto front." if improved
          else "  => no feature design beat the smooth control (features didn't help here).")
    print(f"  -> {out/'feature_verdict.json'}  (total {time.time()-_t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
