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


def build_parser() -> argparse.ArgumentParser:
    """CLI flags for Optuna study (tests parse this; main() runs it)."""
    ap = argparse.ArgumentParser(description="fansim multi-objective optimization")
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--out", default="runs/opt")
    ap.add_argument("--study-name", default="fansim")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--load-pa", type=float, default=None,
                    help="system-curve Pa at 50 CFM (not a fixed wall). Default 1.0 or the --preset value.")
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
    ap.add_argument("--stator", action="store_true",
                    help="replace the four-bar frame with a staggered vane row (roadmap 2.2). Off.")
    ap.add_argument("--mountable", action="store_true",
                    help="only search designs whose hub can house the fan model's motor (real-mount "
                         "constraint: hub radius >= motor cavity/2 + wall). Needs a model with a motor_mount.")
    ap.add_argument("--bem-prescreen", type=float, default=0.0, metavar="CFM_FLOOR",
                    help="RANKING-ONLY BEM: skip CFD when predicted hose CFM is below CFM_FLOOR "
                         "(not absolute CFM; ignores thickness/lean/wrap/LE-TE/plate; BEM≈0.6× CFD). "
                         "Never quote BEM beside CFD as equivalent. 0 = off.")
    ap.add_argument("--surrogate-prescreen", type=float, default=0.0, metavar="CFM_FLOOR",
                    help="skip CFD when the catalog GP mean+1 std of free-delivery CFM is below "
                         "CFM_FLOOR (roadmap 7.4). Refits after each feasible CFD trial. "
                         "Uncertain predictions still run CFD. 0 = off.")
    ap.add_argument("--surrogate-db", default="catalog/catalog.db",
                    help="SQLite catalog used by --surrogate-prescreen (ignored when the floor is 0).")
    ap.add_argument("--surrogate-boost", action="store_true",
                    help="with --surrogate-prescreen: use HistGradientBoosting for the CFM mean and "
                         "the catalog GP for std (roadmap 7.4). Needs scikit-learn; else falls back "
                         "to GP-only. Off by default.")
    ap.add_argument("--surrogate-nn", action="store_true",
                    help="with --surrogate-prescreen: use a small MLP for the CFM mean and the "
                         "catalog GP for std (roadmap 7.4). Needs torch; else falls back to GP-only. "
                         "Wins over --surrogate-boost when both are set. Off by default.")
    ap.add_argument("--surrogate-guided", action="store_true",
                    help="developer / experimental (roadmap §20.5): DoE → fit GP/ensemble → "
                         "NSGA-II on the surrogate → verify top-k → refit. Needs --verify-cfd "
                         "(catalog + CFD; no synthetic DoE) or --stub-labels "
                         "(synthetic labels, not CFD).")
    ap.add_argument("--verify-cfd", action="store_true",
                    help="with --surrogate-guided: train on catalog rows and CFD-verify top-k "
                         "(needs Docker). Does not label the DoE with synthetic_label.")
    ap.add_argument("--stub-labels", action="store_true",
                    help="with --surrogate-guided: allow synthetic_label ranks (not CFD). "
                         "Required if --verify-cfd is off.")
    ap.add_argument("--doe", type=int, default=24,
                    help="with --surrogate-guided: space-filling DoE sample count.")
    ap.add_argument("--nsga-trials", type=int, default=64,
                    help="with --surrogate-guided: NSGA-II trials on the surrogate.")
    ap.add_argument("--top-k", type=int, default=4,
                    help="with --surrogate-guided: designs to verify each round.")
    ap.add_argument("--rounds", type=int, default=2,
                    help="with --surrogate-guided: fit→NSGA→verify→refit rounds.")
    ap.add_argument("--acq-kappa", type=float, default=1.0,
                    help="with --surrogate-guided: UCB kappa on ensemble/GP spread.")
    ap.add_argument("--preset", choices=["legacy", "case", "heatsink", "radiator"], default=None,
                    help="application hose preset (sets --load-pa unless --load-pa is also given).")
    ap.add_argument("--refine-op", action="store_true",
                    help="third RANS at the system-curve operating pressure (replaces algebraic "
                         "cfm_load / efficiency). Off by default.")
    ap.add_argument("--shroud", action="store_true",
                    help="stamp a tip ring on every trial and shrink tip_radius so the OD still fits "
                         "the frame. Coupled to --winglet: a full-span ring disables the winglet.")
    ap.add_argument("--stator-stack", action="store_true",
                    help="stator row then four-bar frame (cannot combine with --stator).")
    ap.add_argument("--stepped-inlet", action="store_true",
                    help="stepped circular casing inlet lip (Noctua-style SID on casing.stl).")
    ap.add_argument("--search-rpm", action="store_true",
                    help="sample RPM inside the PWM band each trial instead of the fan-model rating.")
    ap.add_argument("--rpm-min", type=float, default=None,
                    help="with --search-rpm: PWM band low RPM (default from pwm_table).")
    ap.add_argument("--rpm-max", type=float, default=None,
                    help="with --search-rpm: PWM band high RPM (default from pwm_table).")
    ap.add_argument("--wall-ks-mm", type=float, default=None,
                    help="opt-in sand-grain roughness on printed impeller/frame/stator walls (mm).")
    ap.add_argument("--material", default="PETG",
                    help="print material for stress / weight gates (default PETG).")
    return ap


def main() -> int:
    args = build_parser().parse_args()

    out = Path(args.out)
    space = args.space or ("guided" if args.guided else "open")
    from fansim.optimize.presets import resolve_load
    preset = None if args.preset in (None, "legacy") else args.preset
    load_pa, preset_name = resolve_load(preset=preset, load_pa=args.load_pa)
    if preset_name:
        print(f"PRESET {preset_name}: load_pa={load_pa:g}")

    # §20.5 surrogate-guided loop: CFD when --verify-cfd; stub only with --stub-labels (R1.11).
    if args.surrogate_guided:
        from fansim.optimize.cli_argv import surrogate_guided_cli_error

        err = surrogate_guided_cli_error(
            guided=True, verify_cfd=args.verify_cfd, stub_labels=args.stub_labels)
        if err:
            print(err)
            return 2
        if args.verify_cfd and not image_available():
            print("ERROR: --verify-cfd needs the OpenFOAM Docker image.")
            return 2
        from fansim.optimize.surrogate_search import run_surrogate_guided
        print(
            f"SURROGATE-GUIDED Doe={args.doe} nsga={args.nsga_trials} "
            f"top_k={args.top_k} rounds={args.rounds} verify_cfd={args.verify_cfd}"
        )
        if args.stub_labels and not args.verify_cfd:
            print("synthetic labels, not CFD")
        result = run_surrogate_guided(
            out_dir=out,
            n_doe=args.doe,
            n_nsga=args.nsga_trials,
            top_k=args.top_k,
            n_rounds=args.rounds,
            space=space,
            kappa=args.acq_kappa,
            boost=args.surrogate_boost,
            nn=args.surrogate_nn,
            catalog_db=args.surrogate_db,
            verify_cfd=args.verify_cfd,
            stub_labels=args.stub_labels,
            fan_model=args.fan_model,
            procs=args.procs,
            base_cell=args.base_cell,
            iters=args.iters,
            load_pa=load_pa,
            material=args.material,
        )
        for note in result.notes:
            print(f"  {note}")
        print(f"Wrote {out / 'surrogate_guided.json'} "
              f"({len(result.verified)} verified, train n={len(result.X)})")
        return 0

    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2

    min_sol_mid = args.min_sol_mid if args.min_sol_mid is not None else (0.9 if args.loadcap else None)
    min_sol_tip = args.min_sol_tip if args.min_sol_tip is not None else (0.6 if args.loadcap else None)
    if space != "open":
        print(f"SEARCH space={space}"
              + (f", per-blade-loading cap: sol_mid>={min_sol_mid}, sol_tip>={min_sol_tip}"
                 if min_sol_mid or min_sol_tip else ""))
    study = run_study(args.trials, out, study_name=args.study_name, procs=args.procs,
                      base_cell=args.base_cell, iters=args.iters, load_pa=load_pa,
                      with_features=args.features, space=space, with_spacing=args.spacing,
                      with_extended=args.extended,
                      with_noise=args.noise, noise_model=args.noise_model, fan_model=args.fan_model,
                      mountable=args.mountable, with_winglet=args.winglet,
                      with_shroud=args.shroud,
                      with_sickle=args.sickle, with_notched_tips=args.notched_tips,
                      refine_op=args.refine_op,
                      stator=args.stator, stator_stack=args.stator_stack,
                      stepped_inlet=args.stepped_inlet,
                      bem_prescreen_cfm=args.bem_prescreen,
                      surrogate_prescreen_cfm=args.surrogate_prescreen,
                      surrogate_db=args.surrogate_db,
                      surrogate_boost=args.surrogate_boost,
                      surrogate_nn=args.surrogate_nn,
                      search_rpm=args.search_rpm,
                      rpm_min=args.rpm_min,
                      rpm_max=args.rpm_max,
                      wall_ks_mm=args.wall_ks_mm,
                      material=args.material,
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
