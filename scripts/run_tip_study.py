# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Does ROUNDING THE BLADE TIP help? — CFD test + a graph.

A blunt square tip sheds a strong tip vortex (leakage loss + noise). Rounding/tapering the tip is a
classic fix on props and turbine blades. This runs real CFD on a base design vs several tip-round
configs, isolating the two knobs: how MUCH to round (tip_round) and how far in it STARTS (tip_start).
Reads cleanly as a curve of airflow/efficiency vs tip_round, so we can see whether there's a sweet spot
or whether it just costs blade area.

Depth leeway is relaxed so a curled/rounded tip isn't gated on fit — we measure the pure aero effect.

Usage:  uv run python scripts/run_tip_study.py --design-id opt_extended2_t36 --out runs/tip_study
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

from fansim.catalog import get_entry  # noqa: E402
from fansim.cfd.runner import image_available  # noqa: E402
from fansim.fan_spec import A12X25  # noqa: E402
from fansim.optimize.objectives import evaluate_candidate  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402

_t0 = time.time()

# (label, tip_round, tip_start). Sweep the amount at a fixed start, then vary the start at a fixed
# amount, plus one round+winglet combo to see whether the two tip treatments stack.
CONFIGS = [
    ("control",        0.0, 0.80, 0.0),
    ("round 0.2",      0.2, 0.80, 0.0),
    ("round 0.4",      0.4, 0.80, 0.0),
    ("round 0.6",      0.6, 0.80, 0.0),
    ("round 0.8",      0.8, 0.80, 0.0),
    ("round 0.5 early", 0.5, 0.65, 0.0),   # longer, gentler rounded tip
    ("round 0.6 cap",  0.6, 0.88, 0.0),    # small rounded cap near the very tip
    ("round 0.5 + winglet", 0.5, 0.80, 6.0),  # round + a mild winglet sweep — do they stack?
]


def main() -> int:
    ap = argparse.ArgumentParser(description="tip-round CFD study")
    ap.add_argument("--design-id", default="opt_extended2_t36")
    ap.add_argument("--out", default="runs/tip_study")
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
    spec = dataclasses.replace(A12X25, leeway_depth_mm=20.0)   # measure aero, not fit
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"[base] {args.design_id}, nB={flat.get('n_blades')} — tip-round sweep (depth leeway on)", flush=True)

    results = []
    for label, tr, ts, wl in CONFIGS:
        f = dict(flat)
        if tr:
            f.update(tip_round=tr, tip_round_start=ts)
        if wl:
            f.update(winglet_span=0.85, winglet_sweep=wl, winglet_lean=0.0)
        params = blade_from_flat(f)
        res = evaluate_candidate(params, out / label.split()[0], procs=args.procs,
                                 base_cell=args.base_cell, iters=args.iters, spec=spec)
        rec = {"label": label, "tip_round": tr, "tip_start": ts, "winglet_sweep": wl,
               "feasible": res.feasible, "cfm_free": round(res.cfm_free, 1),
               "cfm_load": round(res.cfm_load, 1), "efficiency": round(res.efficiency, 1),
               "reason": res.reason}
        results.append(rec)
        tag = "OK  " if res.feasible else "GATE"
        print(f"  {label:20s} tr={tr:>3} ts={ts:>4}: {tag} "
              + (f"cfm {res.cfm_free:6.1f}/{res.cfm_load:6.1f}  eff {res.efficiency:5.1f}%"
                 if res.feasible else res.reason)
              + f"  (wall {time.time()-_t0:.0f}s)", flush=True)

    (out / "tip_verdict.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    # ---- verdict + graph -------------------------------------------------------------------------
    ctrl = next((r for r in results if r["tip_round"] == 0 and r["winglet_sweep"] == 0), None)
    print("\n===== TIP-ROUND EFFECT (vs control) =====")
    if ctrl and ctrl["feasible"]:
        print(f"  control: cfm {ctrl['cfm_free']}/{ctrl['cfm_load']}  eff {ctrl['efficiency']}%")
        best = None
        for r in results:
            if r is ctrl or not r["feasible"]:
                continue
            df, dl, de = (r["cfm_free"] - ctrl["cfm_free"], r["cfm_load"] - ctrl["cfm_load"],
                          r["efficiency"] - ctrl["efficiency"])
            print(f"  {r['label']:20s}: cfm {df:+.1f}/{dl:+.1f}  eff {de:+.1f}")
            score = df + dl + de
            if best is None or score > best[1]:
                best = (r["label"], score, df, de)
        if best and (best[2] > 0.5 or best[3] > 0.5):
            print(f"\n  => Best: '{best[0]}' ({best[2]:+.1f} CFM free, {best[3]:+.1f}% eff vs square tip).")
        else:
            print("\n  => Rounding the tip does NOT beat the square tip here (costs blade area at flat gain).")

    try:  # a simple graph: tip_round vs airflow/efficiency (winglet combo excluded from the curve)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        curve = [r for r in results if r["winglet_sweep"] == 0 and r["tip_start"] == 0.80 and r["feasible"]]
        curve.sort(key=lambda r: r["tip_round"])
        if len(curve) >= 3:
            xs = [r["tip_round"] for r in curve]
            fig, ax1 = plt.subplots(figsize=(7, 4.5))
            ax1.plot(xs, [r["cfm_free"] for r in curve], "o-", color="tab:blue", label="CFM free")
            ax1.plot(xs, [r["cfm_load"] for r in curve], "s--", color="tab:cyan", label="CFM load")
            ax1.set_xlabel("tip_round (0 = square tip, 1 = fully rounded)")
            ax1.set_ylabel("airflow (CFM)", color="tab:blue")
            ax2 = ax1.twinx()
            ax2.plot(xs, [r["efficiency"] for r in curve], "^-", color="tab:red", label="efficiency %")
            ax2.set_ylabel("efficiency (%)", color="tab:red")
            ax1.set_title(f"Does rounding the tip help?  base {args.design_id}")
            ax1.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(out / "tip_study.png", dpi=110)
            print(f"  graph -> {out/'tip_study.png'}")
    except Exception as exc:  # noqa: BLE001 - the graph is a nicety
        print(f"  (graph skipped: {exc})")

    print(f"  -> {out/'tip_verdict.json'}  (total {time.time()-_t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
