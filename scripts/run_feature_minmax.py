# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""How big is each lever's effect? — a one-at-a-time (OAT) MIN/MAX sweep.

Takes the best design from a run, and for each key parameter evaluates it at its MIN and its MAX (all
others fixed at the base), so you see each feature's EFFECT RANGE on airflow/efficiency — a tornado.
Real-frame-aware: extremes that leave the fan's envelope are gated (and reported), so you also see
which levers are already at their buildable limit.

Usage:  uv run python scripts/run_feature_minmax.py --run runs/opt_realframe --out runs/feature_minmax
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
from fansim.fan_spec import get_fan_spec  # noqa: E402
from fansim.optimize.objectives import evaluate_candidate  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402

_t0 = time.time()
# (param, min, max) — the key geometry levers, over their guided/search ranges.
SWEEPS = [
    ("n_blades", 5, 11), ("stagger_mid", 28, 46), ("stagger_tip", 18, 36),
    ("chord_mid", 22, 40), ("chord_tip", 24, 40), ("sweep_tip", 0, 12),
    ("lean_tip", 0, 40), ("max_camber", 0.0, 0.03), ("hub_radius", 20, 30),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="runs/opt_realframe")
    ap.add_argument("--fan-model", default="a12x25")
    ap.add_argument("--out", default="runs/feature_minmax")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.006)
    ap.add_argument("--iters", type=int, default=800)
    a = ap.parse_args()
    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2

    pj = json.loads((Path(a.run) / "pareto.json").read_text())
    if not pj:
        print(f"{a.run}/pareto.json is empty — no base design to sweep.")
        return 2
    base = max(pj, key=lambda r: r.get("cfm_free", 0.0))["params"]
    spec = get_fan_spec(a.fan_model)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"[base] best of {a.run} (nB={base.get('n_blades')}) on {spec.name}", flush=True)

    def ev(flat, tag):
        return evaluate_candidate(blade_from_flat(flat), out / tag, procs=a.procs,
                                  base_cell=a.base_cell, iters=a.iters, spec=spec)

    b = ev(dict(base), "base")
    base_cfm = b.cfm_free if b.feasible else 0.0
    results = [{"param": "base", "value": "", "feasible": b.feasible,
                "cfm_free": round(b.cfm_free, 1), "cfm_load": round(b.cfm_load, 1),
                "eff": round(b.efficiency, 1)}]
    print(f"  base: {b.cfm_free:.1f}/{b.cfm_load:.1f}  eff {b.efficiency:.1f}%", flush=True)

    for param, lo, hi in SWEEPS:
        for val in (lo, hi):
            flat = dict(base)
            flat[param] = int(val) if param == "n_blades" else float(val)
            r = ev(flat, f"{param}_{val}")
            results.append({"param": param, "value": val, "feasible": r.feasible,
                            "cfm_free": round(r.cfm_free, 1), "cfm_load": round(r.cfm_load, 1),
                            "eff": round(r.efficiency, 1), "reason": r.reason})
            tag = (f"{r.cfm_free:5.1f}/{r.cfm_load:5.1f}  eff {r.efficiency:4.1f}%"
                   if r.feasible else f"GATE {r.reason}")
            print(f"  {param}={val}: {tag}  ({time.time()-_t0:.0f}s)", flush=True)

    (out / "minmax.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    # ranked tornado: each lever's CFM span from min->max (feasible points), around the base
    print("\n===== FEATURE MIN/MAX EFFECT (CFM free span, ranked) =====")
    spans = []
    for param, _, _ in SWEEPS:
        vals = [r["cfm_free"] for r in results if r.get("param") == param and r["feasible"]]
        if len(vals) >= 2:
            spans.append((param, min(vals), max(vals), max(vals) - min(vals)))
    spans.sort(key=lambda s: -s[3])
    for p, lo, hi, span in spans:
        print(f"  {p:14s}: {lo:5.1f} … {hi:5.1f} CFM  (span {span:4.1f})")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 5))
        for i, (p, lo, hi, _) in enumerate(spans):
            ax.plot([lo, hi], [i, i], "o-", lw=3)
        ax.set_yticks(range(len(spans)))
        ax.set_yticklabels([s[0] for s in spans])
        ax.axvline(base_cfm, ls="--", color="gray", label="base")
        ax.set_xlabel("CFM free (min → max of each lever)")
        ax.set_title(f"Feature min/max effect — {spec.name} frame")
        ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(out / "minmax_tornado.png", dpi=110)
        print(f"  graph -> {out/'minmax_tornado.png'}")
    except Exception as exc:  # noqa: BLE001
        print(f"  (graph skipped: {exc})")

    print(f"  -> {out/'minmax.json'}  (total {time.time()-_t0:.0f}s)")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
