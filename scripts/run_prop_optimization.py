"""Auto-design a propeller blade for a size/RPM envelope, then optionally export the picked design.

BEMT is instant, so this runs hundreds of trials in a second and prints the thrust<->efficiency
Pareto front. Pick a row (by --pick index, default the best-efficiency one at/under the power cap)
and, with --export, build its STL.

    uv run python scripts/run_prop_optimization.py fpv_5inch --trials 400 --max-power 700
    uv run python scripts/run_prop_optimization.py fpv_5inch --export exports/prop_opt.stl --pick 4
"""

from __future__ import annotations

import argparse
import dataclasses

from fansim.prop_spec import get_prop_spec, prop_spec_names
from fansim.propeller.geometry import build_prop
from fansim.propeller.optimize import run_prop_study


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", choices=prop_spec_names(), help="prop envelope to optimize within")
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--max-power", type=float, default=None, help="motor power budget in watts (gates over-budget designs)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--top", type=int, default=12, help="how many Pareto rows to print")
    ap.add_argument("--pick", type=int, default=None, help="Pareto row index to export (default: most efficient)")
    ap.add_argument("--export", type=str, default=None, help="STL path to build the picked design")
    ap.add_argument("--cfd-top", type=int, default=0,
                    help="after BEMT Pareto, run CFD on the top-N thrust rows (0 = off)")
    ap.add_argument("--bemt-floor", type=float, default=0.0,
                    help="skip CFD when BEMT thrust (g) is below this floor")
    ap.add_argument("--cfd-out", type=str, default=None,
                    help="directory for --cfd-top CFD cases + summary.json")
    args = ap.parse_args()

    spec = get_prop_spec(args.spec)
    print(f"Optimizing {spec.name} ({spec.diameter_in}x{spec.pitch_in}) @ {spec.rpm_max} rpm"
          + (f", <= {args.max_power:.0f} W" if args.max_power else "") + " ...")
    study, pareto = run_prop_study(spec, n_trials=args.trials, seed=args.seed, max_power_w=args.max_power)
    print(f"{len(study.trials)} trials -> {len(pareto)} Pareto designs\n")
    print(f"{'idx':>3s} {'thrust':>7s} {'eff':>6s} {'power':>6s} {'FM':>5s} {'nB':>3s}  pitch  chord(r/m/t)")
    for i, r in enumerate(pareto[:args.top]):
        p = r["params"]
        print(f"{i:3d} {r['thrust_g']:6.0f}g {r['eff_g_per_w']:5.2f} {r['power_w']:5.0f}W "
              f"{r['fm']:4.2f} {r['n_blades']:3d}  {p['pitch_in']:.1f}\"  "
              f"{p['chord_root']:.2f}/{p['chord_mid']:.2f}/{p['chord_tip']:.2f}")

    if args.export:
        # default pick = most efficient (last row, since front is sorted by descending thrust)
        idx = args.pick if args.pick is not None else len(pareto) - 1
        r = pareto[idx]
        p = r["params"]
        s2 = dataclasses.replace(spec, n_blades=p["n_blades"], pitch_in=p["pitch_in"])
        res = build_prop(s2, args.export,
                         chord_frac=(p["chord_root"], p["chord_mid"], p["chord_tip"]),
                         camber=p["camber"])
        print(f"\nExported row {idx} ({r['thrust_g']:.0f}g @ {r['eff_g_per_w']:.2f} g/W, "
              f"{r['n_blades']}-blade {p['pitch_in']:.1f}\") -> {args.export}"
              f"  [{'watertight' if res.ok else 'NOT watertight'}]")


if __name__ == "__main__":
    main()
