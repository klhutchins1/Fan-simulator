"""Head-to-head: axial (four-bar frame) vs mixed-flow at high-Pa hose.

Same mesh / hose / print penalty. Axial uses the stator-campaign baseline
(``opt_realframe2``-class params); mixed-flow uses default ``MixedFlowParams``.
No Optuna — fixed A/B ranking under radiator (or heatsink) impedance (roadmap §4.1).

Usage:
    uv run python scripts/run_mixed_vs_axial.py \\
        --base-json runs/opt_realframe2/pareto.json --base-trial 47 \\
        --preset heatsink --out runs/campaign_mixed_vs_axial
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.centrifugal.evaluate import evaluate_mixed_flow  # noqa: E402
from fansim.centrifugal.geometry import MixedFlowParams  # noqa: E402
from fansim.cfd.runner import image_available  # noqa: E402
from fansim.optimize.objectives import evaluate_candidate  # noqa: E402
from fansim.optimize.presets import resolve_load  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402

_t0 = time.time()

# (folder_slug, label, kind)  kind ∈ {"axial", "mixed"}
VARIANTS = [
    ("axial_frame", "axial + frame", "axial"),
    ("mixed_flow", "mixed-flow + frame", "mixed"),
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
    # Free/probe CFM from RANS even when the hose intersection fails (reverse flow).
    cfm_free_cfd = free.get("cfm")
    cfm_probe_cfd = load.get("cfm")
    return {
        "feasible": bool(res.feasible),
        "reason": res.reason or "",
        "cfm_free": (round(float(res.cfm_free), 2) if res.feasible
                     else (round(float(cfm_free_cfd), 2) if cfm_free_cfd is not None else None)),
        "cfm_load": round(float(res.cfm_load), 2) if res.feasible else None,
        "cfm_probe_cfd": (round(float(cfm_probe_cfd), 2)
                          if cfm_probe_cfd is not None else None),
        "efficiency_pct": round(float(res.efficiency), 2) if res.feasible else None,
        "dp_op_pa": (round(float(res.raw["dp_op_pa"]), 2)
                     if res.feasible and res.raw.get("dp_op_pa") is not None else None),
        "dp_free_pa": (round(float(free["static_pressure_rise_pa"]), 2)
                       if free.get("static_pressure_rise_pa") is not None else None),
        "dp_probe_pa": (round(float(load["static_pressure_rise_pa"]), 2)
                        if load.get("static_pressure_rise_pa") is not None else None),
        "eta_total_free": free.get("eta_total"),
        "eta_total_load": load.get("eta_total"),
        "converged": bool(res.raw.get("converged")) if res.raw.get("converged") is not None else False,
        "topology": res.raw.get("topology") or res.raw.get("archetype"),
        "stator_stamp": res.raw.get("stator"),
        "runtime_s": res.runtime_s,
    }


def _write_summary_md(out: Path, payload: dict) -> None:
    rows = payload["results"]
    lines = [
        "# Mixed-flow vs axial campaign",
        "",
        f"**Date:** {payload['date']}",
        f"**Axial base:** `{payload['base_json']}` trial {payload['base_trial']}",
        f"**Mixed-flow:** default `MixedFlowParams` "
        f"(nB={payload['mixed_params'].get('n_blades')}, "
        f"stagger={payload['mixed_params'].get('stagger_deg')}°)",
        f"**Hose:** {payload['preset'] or 'custom'} — "
        f"{payload['load_pa']:g} Pa @ 50 CFM (ΔP = k Q²)",
        f"**Mesh:** base_cell={payload['base_cell']}, iters={payload['iters']}, "
        f"procs={payload['procs']}",
        f"**Stationary:** four-bar frame both sides; circular duct; print penalty on",
        "",
        "## Variants",
        "",
        "| variant | CFM free | CFM @ hose | η % | ΔP_op Pa | ΔP free | ΔP probe | probe CFM | converged |",
        "|---------|----------|------------|-----|----------|---------|----------|-----------|-----------|",
    ]
    for r in rows:
        cfm_f = f"{r['cfm_free']:.1f}" if r.get("cfm_free") is not None else "—"
        cfm_l = f"{r['cfm_load']:.1f}" if r.get("cfm_load") is not None else "—"
        eta = f"{r['efficiency_pct']:.1f}" if r.get("efficiency_pct") is not None else "—"
        probe_q = (f"{r['cfm_probe_cfd']:.1f}"
                   if r.get("cfm_probe_cfd") is not None else "—")
        note = "" if r.get("feasible") else f" ({r.get('reason', 'fail')})"
        lines.append(
            f"| {r['label']}{note} | {cfm_f} | {cfm_l} | {eta} | "
            f"{r.get('dp_op_pa') or '—'} | {r.get('dp_free_pa') or '—'} | "
            f"{r.get('dp_probe_pa') or '—'} | {probe_q} | {r.get('converged')} |"
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
        axial = next((r for r in feas if r["id"] == "axial_frame"), None)
        mixed = next((r for r in feas if r["id"] == "mixed_flow"), None)
        if axial and mixed:
            d_cfm = mixed["cfm_load"] - axial["cfm_load"]
            d_eff = mixed["efficiency_pct"] - axial["efficiency_pct"]
            lines.append(
                f"- mixed vs axial: dCFM_load={d_cfm:+.1f}, "
                f"d_eta={d_eff:+.1f} pt"
            )
        lines.append("")
        lines.append(payload.get("takeaway", ""))
    else:
        lines.append("No feasible variants.")
        if payload.get("takeaway"):
            lines.extend(["", payload["takeaway"]])
    lines.extend([
        "",
        "## Artifacts",
        "",
        f"- `{out / 'summary.json'}`",
        f"- `{out / 'summary.md'}`",
        f"- per-variant workdirs: `axial_frame/`, `mixed_flow/`",
        "",
    ])
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _takeaway(results: list[dict], *, load_pa: float) -> str:
    feas = [r for r in results if r.get("feasible")]
    axial = next((r for r in results if r["id"] == "axial_frame"), None)
    mixed = next((r for r in results if r["id"] == "mixed_flow"), None)

    if not feas:
        # High-Pa reverse-flow: rank on free ΔP / free CFM if CFD stamped them.
        if axial and mixed and axial.get("dp_free_pa") is not None and mixed.get("dp_free_pa") is not None:
            d_p = mixed["dp_free_pa"] - axial["dp_free_pa"]
            d_q = (mixed.get("cfm_free") or 0) - (axial.get("cfm_free") or 0)
            winner = "mixed-flow" if d_p > 0.5 else ("axial" if d_p < -0.5 else "tie")
            return (
                f"**Both reverse-flow at {load_pa:g} Pa probe** "
                f"(system-curve out of range). Free-air ΔP: axial "
                f"{axial['dp_free_pa']:.1f} Pa / {axial.get('cfm_free')} CFM vs mixed "
                f"{mixed['dp_free_pa']:.1f} Pa / {mixed.get('cfm_free')} CFM "
                f"(dP={d_p:+.1f} Pa, dCFM={d_q:+.1f}) — free-air edge: {winner}. "
                "Default mixed-flow does not unlock heatsink/radiator hoses vs this axial "
                "baseline in steady RANS; keep axial for case-class, treat mixed as unproven "
                "at high Pa until a higher-pressure design exists."
            )
        fails = "; ".join(f"{r['id']}: {r.get('reason', '?')}" for r in results)
        return f"No feasible variants ({fails})."

    best = max(feas, key=lambda r: r["cfm_load"])

    # Axial infeasible (e.g. reverse-flow / system-curve) but mixed ok
    if mixed and mixed.get("feasible") and axial and not axial.get("feasible"):
        return (
            f"**Winner under hose: mixed-flow** ({mixed['cfm_load']:.1f} CFM @ op). "
            f"Axial baseline out of range ({axial.get('reason', 'infeasible')}) — "
            "default mixed-flow holds positive flow at this high-Pa impedance where "
            "the axial frame design does not."
        )
    if axial and axial.get("feasible") and mixed and not mixed.get("feasible"):
        return (
            f"**Winner under hose: axial + frame** ({axial['cfm_load']:.1f} CFM @ op). "
            f"Mixed-flow failed ({mixed.get('reason', 'infeasible')})."
        )
    if not (axial and mixed and axial.get("feasible") and mixed.get("feasible")):
        return f"**Best CFM @ hose:** `{best['id']}` ({best['cfm_load']:.1f} CFM)."

    d = mixed["cfm_load"] - axial["cfm_load"]
    de = mixed["efficiency_pct"] - axial["efficiency_pct"]
    if d > 0.5:
        return (
            f"**Winner under hose: mixed-flow** ({mixed['cfm_load']:.1f} CFM @ op vs "
            f"axial {axial['cfm_load']:.1f}; d_eta={de:+.1f} pt). "
            "At this high-Pa hose the diagonal impeller beats the axial frame baseline — "
            "keep mixed-flow in the archetype toolbox for radiator-class impedance."
        )
    if d < -0.5:
        return (
            f"**Winner under hose: axial + frame** ({axial['cfm_load']:.1f} CFM @ op vs "
            f"mixed {mixed['cfm_load']:.1f}; d_eta={-de:+.1f} pt axial). "
            "Default mixed-flow does not beat this axial baseline at this hose — "
            "axial remains the screening default; mixed-flow stays for higher-Pa "
            "re-opts / different defaults."
        )
    return (
        f"**Null under hose:** mixed vs axial within ~0.5 CFM "
        f"(axial {axial['cfm_load']:.1f}, mixed {mixed['cfm_load']:.1f}; "
        f"d_eta={de:+.1f} pt) — no clear archetype flip on defaults alone."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="mixed-flow vs axial OpenFOAM campaign")
    ap.add_argument("--base-json", default="runs/opt_realframe2/pareto.json",
                    help="axial BladeParams source (same as stator campaign)")
    ap.add_argument("--base-trial", type=int, default=47)
    ap.add_argument("--out", default="runs/campaign_mixed_vs_axial")
    ap.add_argument("--preset", default="heatsink",
                    help="case|heatsink|radiator (Pa @ 50 CFM). Default heatsink (20 Pa): "
                         "BEM/CFD show axial shutoff below radiator 35 Pa; heatsink is the "
                         "high-Pa hose where mixed still scores and axial typically fails.")
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
    axial_params = blade_from_flat(flat)
    mixed_params = MixedFlowParams()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "base.json").write_text(
        json.dumps([{"trial": args.base_trial, "params": flat}], indent=2),
        encoding="utf-8",
    )
    mixed_flat = {
        "n_blades": mixed_params.n_blades,
        "r_eye_mm": mixed_params.r_eye_mm,
        "r_back_mm": mixed_params.r_back_mm,
        "r_tip_mm": mixed_params.r_tip_mm,
        "z_span_mm": mixed_params.z_span_mm,
        "chord_mm": mixed_params.chord_mm,
        "stagger_deg": mixed_params.stagger_deg,
        "thickness": mixed_params.thickness,
        "max_camber": mixed_params.max_camber,
    }
    (out / "mixed_params.json").write_text(
        json.dumps(mixed_flat, indent=2), encoding="utf-8")

    print(
        f"[base] axial trial {args.base_trial} nB={axial_params.n_blades}  "
        f"mixed nB={mixed_params.n_blades} stagger={mixed_params.stagger_deg}°  "
        f"hose={preset_name or 'custom'} {load_pa:g} Pa @ 50 CFM  "
        f"cell={args.base_cell} iters={args.iters} procs={args.procs}",
        flush=True,
    )

    results = []
    for slug, label, kind in VARIANTS:
        print(f"\n=== {label} ===", flush=True)
        try:
            if kind == "axial":
                res = evaluate_candidate(
                    axial_params,
                    out / slug,
                    procs=args.procs,
                    base_cell=args.base_cell,
                    iters=args.iters,
                    load_pa=load_pa,
                    stator=False,
                    stator_stack=False,
                )
            else:
                res = evaluate_mixed_flow(
                    mixed_params,
                    out / slug,
                    procs=args.procs,
                    base_cell=args.base_cell,
                    iters=args.iters,
                    load_pa=load_pa,
                )
        except Exception as exc:  # noqa: BLE001 — keep campaign rolling
            print(f"  FAIL {type(exc).__name__}: {exc}", flush=True)
            results.append({
                "id": slug, "label": label, "kind": kind,
                "feasible": False, "reason": f"{type(exc).__name__}: {exc}",
            })
            continue
        row = {"id": slug, "label": label, "kind": kind, **_metric_slice(res)}
        results.append(row)
        if res.feasible:
            print(
                f"  OK  cfm_free={res.cfm_free:.1f} cfm_load={res.cfm_load:.1f} "
                f"eff={res.efficiency:.1f}%  ({res.runtime_s:.0f}s, "
                f"wall {time.time() - _t0:.0f}s)",
                flush=True,
            )
        else:
            print(f"  FAIL {res.reason} ({res.runtime_s:.0f}s)", flush=True)

    takeaway = _takeaway(results, load_pa=load_pa)
    payload = {
        "date": date.today().isoformat(),
        "base_json": str(args.base_json),
        "base_trial": args.base_trial,
        "mixed_params": mixed_flat,
        "preset": preset_name,
        "load_pa": load_pa,
        "base_cell": args.base_cell,
        "iters": args.iters,
        "procs": args.procs,
        "circular_duct": True,
        "print_penalty": True,
        "stationary": "frame",
        "wall_s": round(time.time() - _t0, 1),
        "results": results,
        "takeaway": takeaway,
    }
    (out / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_summary_md(out, payload)

    print("\n===== MIXED-FLOW VS AXIAL =====")
    print(takeaway.encode("ascii", "replace").decode("ascii"))
    print(f"  -> {out / 'summary.json'}  (total {time.time() - _t0:.0f}s)")
    return 0 if all(r.get("feasible") for r in results) else 1


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
