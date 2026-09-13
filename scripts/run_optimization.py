# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Phase-3 entry point: multi-objective blade optimization.

Runs an Optuna NSGA-II search over the design vector, maximizing
(cfm_free, cfm_load, efficiency). Writes a resumable SQLite study, a Pareto summary JSON,
a scatter plot, and copies the Pareto-front impeller STLs to <out>/pareto/.

Usage:
    uv run --extra optim python scripts/run_optimization.py --trials 30 --out runs/opt
        [--procs 8] [--base-cell 0.005] [--iters 800] [--load-pa 5]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from fansim.cfd.runner import image_available  # noqa: E402
from fansim.optimize.study import pareto_summary, run_study  # noqa: E402
from fansim.optimize.search_space import OBJECTIVE_NAMES  # noqa: E402

_t0 = time.time()


def _progress(trial, params, result):
    tag = "OK  " if result.feasible else "GATE"
    obj = (f"cfm_free={result.cfm_free:6.1f}  cfm_load={result.cfm_load:6.1f}  "
           f"eff={result.efficiency:5.1f}%") if result.feasible else result.reason
    print(f"[trial {trial.number:03d}] {tag} nB={params.n_blades} {obj} "
          f"({result.runtime_s:.0f}s, wall {time.time()-_t0:.0f}s)")
    sys.stdout.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description="fansim multi-objective optimization")
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--out", default="runs/opt")
    ap.add_argument("--study-name", default="fansim")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--load-pa", type=float, default=1.0)
    ap.add_argument("--features", action="store_true",
                    help="also search the bio-inspired feature layer (tubercles/serrations/dimples)")
    ap.add_argument("--guided", action="store_true",
                    help="narrow the search to the data-driven recipe in docs/design-rules.md")
    ap.add_argument("--space", choices=["open", "guided", "guided_lc"], default=None,
                    help="search space; 'guided_lc' = guided + load-spreading (pair with --loadcap)")
    ap.add_argument("--loadcap", action="store_true",
                    help="per-blade-loading cap: solidity floor (sol_mid>=0.9, sol_tip>=0.6)")
    ap.add_argument("--spacing", action="store_true",
                    help="add an uneven-but-balanced blade-spacing DOF (spreads the blade-pass tone)")
    ap.add_argument("--extended", action="store_true",
                    help="also tune hub radius, per-station thickness, and camber position")
    ap.add_argument("--noise", action="store_true",
                    help="add a 4th objective: minimize a per-candidate noise proxy")
    ap.add_argument("--noise-model", choices=["loading", "proudman"], default="loading",
                    help="noise proxy: 'loading' (cheap, tracks LBM dipole) or 'proudman' (broadband)")
    ap.add_argument("--fan-model", default="a12x25",
                    help="fan-model constraint spec to gate on (envelope + motor power + weight)")
    ap.add_argument("--min-sol-mid", type=float, default=None)
    ap.add_argument("--min-sol-tip", type=float, default=None)
    ap.add_argument("--winglet", action="store_true",
                    help="search a tip winglet too (CFD: mild winglet ~+4%% airflow; adds tip depth). "
                         "Coupled to --shroud (roadmap 7.5): a full-span ring disables the winglet - "
                         "a full ring already kills the tip leak, so a winglet there is pure blockage.")
    ap.add_argument("--sickle", action="store_true",
                    help="stamp a forward-swept LE (sickle, le_skew) on every trial for tone control.")
    ap.add_argument("--notched-tips", action="store_true",
                    help="stamp tip-only trailing-edge notches on every trial (blade-pass tone trick).")
    ap.add_argument("--mountable", action="store_true",
                    help="only search designs whose hub can house the fan model's motor (real-mount "
                         "constraint: hub radius >= motor cavity/2 + wall). Needs a model with a motor_mount.")
    ap.add_argument("--bem-prescreen", type=float, default=0.0, metavar="CFM_FLOOR",
                    help="skip CFD on designs the instant fan-BEM predicts below CFM_FLOOR free-delivery "
                         "(roadmap 7.1c). CONSERVATIVE: the BEM ranks CFD ~0.62, so set the floor well "
                         "below any viable design (e.g. 30-35 for a 120mm fan). 0 = off.")
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2

    out = Path(args.out)
    space = args.space or ("guided" if args.guided else "open")
    min_sol_mid = args.min_sol_mid if args.min_sol_mid is not None else (0.9 if args.loadcap else None)
    min_sol_tip = args.min_sol_tip if args.min_sol_tip is not None else (0.6 if args.loadcap else None)
    if space != "open":
        print(f"SEARCH space={space}"
              + (f", per-blade-loading cap: sol_mid>={min_sol_mid}, sol_tip>={min_sol_tip}"
                 if min_sol_mid or min_sol_tip else ""))
    study = run_study(args.trials, out, study_name=args.study_name, procs=args.procs,
                      base_cell=args.base_cell, iters=args.iters, load_pa=args.load_pa,
                      with_features=args.features, space=space, with_spacing=args.spacing,
                      with_extended=args.extended,
                      with_noise=args.noise, noise_model=args.noise_model, fan_model=args.fan_model,
                      mountable=args.mountable, with_winglet=args.winglet,
                      bem_prescreen_cfm=args.bem_prescreen,
                      min_sol_mid=min_sol_mid, min_sol_tip=min_sol_tip, on_trial=_progress)

    pareto = pareto_summary(study)
    (out / "pareto.json").write_text(json.dumps(pareto, indent=2), encoding="utf-8")

    # Copy Pareto-front STLs.
    pdir = out / "pareto"
    pdir.mkdir(exist_ok=True)
    for row in pareto:
        src = out / "trials" / f"trial_{row['trial']:04d}" / "impeller.stl"
        if src.exists():
            shutil.copy(src, pdir / f"trial_{row['trial']:04d}_"
                        f"cfmF{row['cfm_free']:.0f}_cfmL{row['cfm_load']:.0f}.stl")

    # Scatter plot: cfm_free vs cfm_load, colored by efficiency; Pareto highlighted.
    feas = [t for t in study.trials if t.user_attrs.get("feasible")]
    if feas:
        xf = [t.values[0] for t in feas]
        yf = [t.values[1] for t in feas]
        ef = [t.values[2] for t in feas]
        pareto_nums = {r["trial"] for r in pareto}
        fig, ax = plt.subplots(figsize=(8, 6))
        sc = ax.scatter(xf, yf, c=ef, cmap="viridis", s=45, label="feasible")
        px = [t.values[0] for t in feas if t.number in pareto_nums]
        py = [t.values[1] for t in feas if t.number in pareto_nums]
        ax.scatter(px, py, facecolors="none", edgecolors="red", s=140, linewidths=1.6,
                   label="Pareto front")
        ax.set_xlabel("CFM at free delivery")
        ax.set_ylabel("CFM at load")
        ax.set_title(f"Design space ({len(feas)} feasible / {len(study.trials)} trials)")
        fig.colorbar(sc, label="efficiency [%]")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out / "pareto.png", dpi=130)

    print(f"\n===== PARETO FRONT ({len(pareto)} designs) =====")
    for r in sorted(pareto, key=lambda d: -d["cfm_free"]):
        print(f"  trial {r['trial']:3d}  nB={r['n_blades']}  "
              f"cfm_free={r['cfm_free']:6.1f}  cfm_load={r['cfm_load']:6.1f}  "
              f"eff={r['efficiency']:5.1f}%")
    print(f"  -> {out/'pareto.json'} , {out/'pareto.png'} , {pdir}/")
    print(f"  total wall time {time.time()-_t0:.0f}s")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
