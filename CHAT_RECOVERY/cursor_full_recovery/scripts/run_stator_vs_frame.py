"""Head-to-head: four-bar frame vs OGV stator vs stator+frame stack.

Same rotor, same hose (Pa @ 50 CFM system curve), OpenFOAM ``evaluate_candidate``.
No Optuna — fixed baseline A/B/C ranking under pressure (roadmap §2.2 campaign).

Usage:
    uv run python scripts/run_stator_vs_frame.py \\
        --base-json runs/campaign_gci_layers/base.json \\
        --preset heatsink --out runs/campaign_stator_vs_frame
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
from fansim.optimize.presets import resolve_load  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402

_t0 = time.time()

# (folder_slug, label, stator, stator_stack)
VARIANTS = [
    ("frame", "frame (four-bar)", False, False),
    ("stator", "stator (OGV replace)", True, False),
    ("stator_stack", "stator-stack (OGV then frame)", False, True),
]


def _load_base(path: Path, trial: int) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        row = next(r for r in data if int(r["trial"]) == trial)
        return dict(row["params"])
    if isinstance(data, dict) and "params" in data:
        return dict(data["params"])
    raise ValueError(f"unrecognized base json shape in {path}")


def _metric_slice(res) -> dict:
    free = res.raw.get("free") or {}
    load = res.raw.get("load") or {}
    return {
        "feasible": bool(res.feasible),
        "reason": res.reason or "",
        "cfm_free": round(float(res.cfm_free), 2) if res.feasible else None,
        "cfm_load": round(float(res.cfm_load), 2) if res.feasible else None,
        "efficiency_pct": round(float(res.efficiency), 2) if res.feasible else None,
        "dp_op_pa": (round(float(res.raw["dp_op_pa"]), 2)
                     if res.feasible and res.raw.get("dp_op_pa") is not None else None),
        "dp_free_pa": (round(float(free["static_pressure_rise_pa"]), 2)
                       if free.get("static_pressure_rise_pa") is not None else None),
        "dp_probe_pa": (round(float(load["static_pressure_rise_pa"]), 2)
                        if load.get("static_pressure_rise_pa") is not None else None),
        "eta_total_free": free.get("eta_total"),
        "eta_total_load": load.get("eta_total"),
        "converged": bool(res.raw.get("converged")) if res.feasible else False,
        "stator_stamp": res.raw.get("stator"),
        "runtime_s": res.runtime_s,
    }


def _write_summary_md(out: Path, payload: dict) -> None:
    rows = payload["results"]
    lines = [
        "# Stator vs frame campaign",
        "",
        f"**Date:** {payload['date']}",
        f"**Base:** `{payload['base_json']}` trial {payload['base_trial']}",
        f"**Hose:** {payload['preset'] or 'custom'} — "
        f"{payload['load_pa']:g} Pa @ 50 CFM (ΔP = k Q²)",
        f"**Mesh:** base_cell={payload['base_cell']}, iters={payload['iters']}, "
        f"procs={payload['procs']}",
        f"**Duct / tip:** circular duct, default tip gap, print penalty on",
        "",
        "## Variants",
        "",
        "| variant | CFM free | CFM @ hose | η % | ΔP_op Pa | ΔP free | ΔP probe | converged |",
        "|---------|----------|------------|-----|----------|---------|----------|-----------|",
    ]
    for r in rows:
        if not r.get("feasible"):
            lines.append(
                f"| {r['label']} | — | — | — | — | — | — | {r.get('reason', 'fail')} |")
            continue
        lines.append(
            f"| {r['label']} | {r['cfm_free']:.1f} | {r['cfm_load']:.1f} | "
            f"{r['efficiency_pct']:.1f} | {r.get('dp_op_pa') or '—'} | "
            f"{r.get('dp_free_pa') or '—'} | {r.get('dp_probe_pa') or '—'} | "
            f"{r['converged']} |"
        )
    lines.extend(["", "## Ranking", ""])
    feas = [r for r in rows if r.get("feasible")]
    if feas:
        by_load = sorted(feas, key=lambda r: r["cfm_load"], reverse=True)
        by_eff = sorted(feas, key=lambda r: r["efficiency_pct"], reverse=True)
        winner = by_load[0]
        lines.append(
            f"- **Best CFM @ hose:** {winner['label']} "
            f"({winner['cfm_load']:.1f} CFM)"
        )
        lines.append(
            f"- **Best efficiency:** {by_eff[0]['label']} "
            f"({by_eff[0]['efficiency_pct']:.1f}%)"
        )
        frame = next((r for r in feas if r["id"] == "frame"), None)
        if frame:
            for r in feas:
                if r is frame:
                    continue
                d_cfm = r["cfm_load"] - frame["cfm_load"]
                d_eff = r["efficiency_pct"] - frame["efficiency_pct"]
                lines.append(
                    f"- vs frame: `{r['id']}` ΔCFM_load={d_cfm:+.1f}, "
                    f"Δη={d_eff:+.1f} pt"
                )
        lines.append("")
        lines.append(payload.get("takeaway", ""))
    else:
        lines.append("No feasible variants.")
    lines.extend([
        "",
        "## Artifacts",
        "",
        f"- `{out / 'summary.json'}`",
        f"- `{out / 'summary.md'}`",
        f"- per-variant workdirs: `frame/`, `stator/`, `stator_stack/`",
        "",
    ])
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="stator vs frame OpenFOAM campaign")
    ap.add_argument("--base-json", default="runs/campaign_gci_layers/base.json")
    ap.add_argument("--base-trial", type=int, default=0)
    ap.add_argument("--out", default="runs/campaign_stator_vs_frame")
    ap.add_argument("--preset", default="case",
                    help="case|heatsink|radiator (Pa @ 50 CFM). Empty string = use --load-pa only. "
                         "Default case (8 Pa): heatsink 20 Pa can reverse-flow this baseline.")
    ap.add_argument("--load-pa", type=float, default=None,
                    help="override hose Pa @ 50 CFM")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--iters", type=int, default=1000)
    args = ap.parse_args()

    if not image_available():
        print("ERROR: OpenFOAM Docker image not found.")
        return 2

    preset = (args.preset or "").strip() or None
    load_pa, preset_name = resolve_load(preset, args.load_pa)
    flat = _load_base(Path(args.base_json), args.base_trial)
    params = blade_from_flat(flat)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "base.json").write_text(
        json.dumps([{"trial": args.base_trial, "params": flat}], indent=2),
        encoding="utf-8",
    )

    print(
        f"[base] trial {args.base_trial} nB={params.n_blades}  "
        f"hose={preset_name or 'custom'} {load_pa:g} Pa @ 50 CFM  "
        f"cell={args.base_cell} iters={args.iters} procs={args.procs}",
        flush=True,
    )

    results = []
    for slug, label, stator, stator_stack in VARIANTS:
        print(f"\n=== {label} ===", flush=True)
        try:
            res = evaluate_candidate(
                params,
                out / slug,
                procs=args.procs,
                base_cell=args.base_cell,
                iters=args.iters,
                load_pa=load_pa,
                stator=stator,
                stator_stack=stator_stack,
            )
        except Exception as exc:  # noqa: BLE001 — keep campaign rolling
            print(f"  FAIL {type(exc).__name__}: {exc}", flush=True)
            results.append({
                "id": slug, "label": label, "stator": stator,
                "stator_stack": stator_stack, "feasible": False,
                "reason": f"{type(exc).__name__}: {exc}",
            })
            continue
        row = {
            "id": slug,
            "label": label,
            "stator": stator,
            "stator_stack": stator_stack,
            **_metric_slice(res),
        }
        results.append(row)
        if res.feasible:
            print(
                f"  OK  cfm_free={res.cfm_free:.1f} cfm_load={res.cfm_load:.1f} "
                f"eff={res.efficiency:.1f}%  stamp={res.raw.get('stator')}  "
                f"({res.runtime_s:.0f}s, wall {time.time() - _t0:.0f}s)",
                flush=True,
            )
        else:
            print(f"  FAIL {res.reason} ({res.runtime_s:.0f}s)", flush=True)

    feas = [r for r in results if r.get("feasible")]
    takeaway = "No feasible variants."
    if feas:
        best = max(feas, key=lambda r: r["cfm_load"])
        frame = next((r for r in feas if r["id"] == "frame"), None)
        if frame and best["id"] == "frame":
            worst_d = min(
                (r["cfm_load"] - frame["cfm_load"] for r in feas if r["id"] != "frame"),
                default=0.0,
            )
            if worst_d < -0.5:
                takeaway = (
                    f"**Winner under hose: frame** ({frame['cfm_load']:.1f} CFM @ op). "
                    "Default cambered OGVs (`--stator` / `--stator-stack`) lose CFM and η "
                    "vs the four-bar frame on this baseline — keep NSGA on frame unless a "
                    "searched stagger/n_vanes campaign flips it."
                )
            else:
                takeaway = (
                    f"**Best CFM @ hose:** frame ({frame['cfm_load']:.1f} CFM); "
                    "stator deltas within noise."
                )
        elif frame and best["id"] != "frame" and best["cfm_load"] > frame["cfm_load"] + 0.5:
            takeaway = (
                f"**Winner under hose:** `{best['id']}` "
                f"({best['cfm_load']:.1f} CFM @ op vs frame {frame['cfm_load']:.1f}). "
                "OGVs beat the four-bar frame on this baseline at this impedance."
            )
        elif frame and all(
            abs(r["cfm_load"] - frame["cfm_load"]) <= 0.5
            and abs(r["efficiency_pct"] - frame["efficiency_pct"]) <= 0.5
            for r in feas
        ):
            takeaway = (
                "**Null under hose:** stator / stack within ~0.5 CFM / 0.5 pt η of frame "
                "on this baseline — no ranking change yet."
            )
        else:
            takeaway = (
                f"**Best CFM @ hose:** `{best['id']}` ({best['cfm_load']:.1f} CFM). "
                "See deltas vs frame in the table."
            )

    from datetime import date

    payload = {
        "date": date.today().isoformat(),
        "base_json": str(args.base_json),
        "base_trial": args.base_trial,
        "preset": preset_name,
        "load_pa": load_pa,
        "base_cell": args.base_cell,
        "iters": args.iters,
        "procs": args.procs,
        "circular_duct": True,
        "print_penalty": True,
        "wall_s": round(time.time() - _t0, 1),
        "results": results,
        "takeaway": takeaway,
    }
    (out / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_summary_md(out, payload)

    print("\n===== STATOR VS FRAME =====")
    print(takeaway)
    print(f"  -> {out / 'summary.json'}  (total {time.time() - _t0:.0f}s)")
    return 0 if all(r.get("feasible") for r in results) else 1


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
