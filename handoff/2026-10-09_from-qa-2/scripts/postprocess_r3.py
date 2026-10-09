"""Rank/de-duplicate the BEM screen, write shortlist + per-design files + cockpit/CFD job files.
Run from the project root with the project venv:  python <screen>/postprocess.py"""
from __future__ import annotations
import csv, json, math, os, shutil, subprocess, sys
from collections import Counter
from pathlib import Path
import numpy as np

sys.path.insert(0, os.getcwd()); sys.path.insert(0, "/workspace/fansim/screen")
import functools                                                           # noqa: E402
import fansim.fan_bem as FB                                                # noqa: E402
from fansim.optimize import search_space as SS                             # noqa: E402
import bem_screen as S                                                     # noqa: E402
# round 3: same settings as screen_r3.py (axial-force pressure, max_camber <= 0.10)
S.pq_curve = functools.partial(FB.pq_curve, pressure_model="axial_force")
S.operating_point = functools.partial(FB.operating_point, pressure_model="axial_force")
SS.BOUNDS[S.SPACE]["max_camber"] = (SS.BOUNDS[S.SPACE]["max_camber"][0], 0.10)
from fansim.geometry.config import save_blade_params                       # noqa: E402
from fansim.fan_spec import fan_spec_to_dict                                # noqa: E402
from fansim.optimize.search_space import stock_blade_flat                   # noqa: E402

SCR = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/fansim/research/screen_r3")
N_SHORT, N_CFD, D_MIN = 30, 5, 0.12
rows = [json.loads(l) for l in open(SCR / "all_designs.jsonl")]
base = json.loads((SCR / "stock_baseline.json").read_text())
stock = base["stock_7station_yaml"]
B = S.param_bounds()
# Extra QA-4 guard applied post hoc: every element runs on the ANALYTIC polar here (Re < 4e4, below the
# lowest table), whose post-stall drag never rises (cd = cd0), so stalled span is scored optimistically.
STALL_FRAC_MAX = 0.5
GUARDS = list(S.GUARDS) + ["aoa_stalled_span"]
S.GUARDS = tuple(GUARDS)
for r in rows:
    r["flags"]["aoa_stalled_span"] = bool(r.get("aoa_stalled_frac", 1.0) <= STALL_FRAC_MAX)
    r["first_fail"] = next((g for g in GUARDS if not r["flags"].get(g, False)), None)
    r["feasible"] = r["first_fail"] is None

def vec(flat):
    return np.array([(float(flat[k]) - B[k][0]) / (B[k][1] - B[k][0]) for k in S.PARAM_KEYS])

# ---------- guard accounting
summary = {"sampled": len(rows), "sobol": sum(r["stage"] == "S" for r in rows),
           "tpe": sum(r["stage"] == "T" for r in rows)}
summary["first_fail"] = dict(Counter(str(r["first_fail"]) for r in rows))
anyf = Counter(); sob_any = Counter()
for r in rows:
    for g in S.GUARDS:
        if not r["flags"].get(g, False):
            anyf[g] += 1
            if r["stage"] == "S":
                sob_any[g] += 1
summary["any_fail_all"] = {g: anyf[g] for g in S.GUARDS}
summary["any_fail_sobol_only"] = {g: sob_any[g] for g in S.GUARDS}
summary["sobol_first_fail"] = dict(Counter(str(r["first_fail"]) for r in rows if r["stage"] == "S"))
feas = [r for r in rows if r["feasible"]]
summary["feasible"] = len(feas)
summary["feasible_sobol"] = sum(r["stage"] == "S" for r in feas)
# would-be-feasible if a guard were removed (shows what each BEM guard is protecting against)
def only_fail(g):
    return [r for r in rows if [x for x in S.GUARDS if not r["flags"].get(x, False)] == [g]]
summary["only_failing_guard"] = {g: len(only_fail(g)) for g in S.GUARDS}
for g in ("aoa_table_edge", "loadcap_solidity", "aoa_stalled_span"):
    xs = [r for r in only_fail(g) if "score" in r and r["score"] == r["score"]]
    if xs:
        best = max(xs, key=lambda r: r["score"])
        summary[f"best_score_rejected_only_by_{g}"] = {"id": best["id"], "score": best["score"],
            "cfm_free": best["cfm_free"], "cfm_load": best["cfm_load"], "eff": best["efficiency"],
            "aoa_edge_frac": best.get("aoa_edge_frac"), "sol": best.get("sol"), "flat": best["flat"]}
# QA-3 exploit check: what free CFM did the raw pq_curve report for 'never positive' designs?
np_ = [r for r in rows if not r["flags"].get("bem_no_positive_static", True)]
summary["qa3_never_positive_raw_free_cfm"] = (
    {"n": len(np_), "median_raw_free_cfm": float(np.median([r["bem_free_cfm_raw"] for r in np_])),
     "max_raw_free_cfm": float(max(r["bem_free_cfm_raw"] for r in np_))} if np_ else {"n": 0})

# ---------- Pareto + rank + diversity
F = np.array([[r["cfm_free"], r["cfm_load"], r["efficiency"]] for r in feas])
for i, r in enumerate(feas):
    r["pareto"] = not bool(np.any(np.all(F >= F[i], axis=1) & np.any(F > F[i], axis=1)))
feas.sort(key=lambda r: -r["score"])
picked = []
for r in feas:
    v = vec(r["flat"])
    if all(np.sqrt(np.mean((v - p["_v"]) ** 2)) >= D_MIN for p in picked):
        r["_v"] = v; picked.append(r)
    if len(picked) >= N_SHORT:
        break
summary["dedup_threshold_rms_norm"] = D_MIN
summary["stall_frac_max"] = STALL_FRAC_MAX
summary["pareto_feasible"] = int(sum(r["pareto"] for r in feas))
summary["shortlist_max_camber_gt_0.0625_s1223_tables"] = sum(float(p["flat"]["max_camber"]) > 0.0625 for p in picked)
summary["feasible_max_camber_gt_0.06"] = sum(float(r["flat"]["max_camber"]) > 0.06 for r in feas)

stock_flat = stock_blade_flat()
def at_bounds(flat):
    out = []
    for k in S.PARAM_KEYS:
        lo, hi = B[k]; x = (float(flat[k]) - lo) / (hi - lo)
        if x <= 0.02: out.append(f"{k}=min")
        elif x >= 0.98: out.append(f"{k}=max")
    return ";".join(out)

# ---------- outputs
for d in ("designs", "cockpit_import", "quick_cfd_jobs"):
    shutil.rmtree(SCR / d, ignore_errors=True)
(SCR / "designs").mkdir()
cols = ["rank", "id", "cfd_tier", "stage", "pareto", "score", "d_score_vs_stock_pct",
        "bem_cfm_free", "d_cfm_free_pct", "bem_cfm_load_case8Pa", "d_cfm_load_pct", "bem_eff_op_pct",
        "d_eff_pct", "bem_free_cfm_raw", "bem_shutoff_pa", "bem_peak_eff", "derate",
        "aoa_stalled_frac", "aoa_edge_frac", "aoa_min_deg", "aoa_max_deg", "sol_mid", "sol_tip",
        "depth_mm_est", "tip_gap_mm", "at_bounds"] + S.PARAM_KEYS
def row_out(rank, r, tier):
    pct = lambda a, b: round(100 * (a / b - 1), 1)
    return {"rank": rank, "id": r["id"], "cfd_tier": tier, "stage": r.get("stage", ""),
            "pareto": r.get("pareto", ""), "score": round(r["score"], 4),
            "d_score_vs_stock_pct": pct(r["score"], 1.0),
            "bem_cfm_free": round(r["cfm_free"], 2), "d_cfm_free_pct": pct(r["cfm_free"], stock["cfm_free"]),
            "bem_cfm_load_case8Pa": round(r["cfm_load"], 2), "d_cfm_load_pct": pct(r["cfm_load"], stock["cfm_load"]),
            "bem_eff_op_pct": round(r["efficiency"], 2), "d_eff_pct": pct(r["efficiency"], stock["efficiency"]),
            "bem_free_cfm_raw": r["bem_free_cfm_raw"], "bem_shutoff_pa": r["bem_shutoff_pa"],
            "bem_peak_eff": r["bem_peak_eff"], "derate": round(r["derate"], 3),
            "aoa_stalled_frac": r["aoa_stalled_frac"], "aoa_edge_frac": r["aoa_edge_frac"],
            "aoa_min_deg": round(r["aoa_range_deg"][0], 1), "aoa_max_deg": round(r["aoa_range_deg"][1], 1),
            "sol_mid": round(r["sol"]["mid"], 3), "sol_tip": round(r["sol"]["tip"], 3),
            "depth_mm_est": round(r["depth_mm"], 2), "tip_gap_mm": round(r["tip_gap_mm"], 2),
            "at_bounds": at_bounds(r["flat"]) if r.get("stage") else "",
            **{k: (round(float(r["flat"][k]), 4) if k in r["flat"] else "") for k in S.PARAM_KEYS}}
stock_row = dict(stock, score=1.0, id="STOCK_A12x25_7station_yaml", stage="", flat={})
stock_row_out = row_out(0, stock_row, "baseline")
for k in S.PARAM_KEYS:
    stock_row_out[k] = round(float(stock_flat[k]), 4) if k in stock_flat else ""
oob = [k for k in S.PARAM_KEYS if k in stock_flat and not (B[k][0] - 1e-9 <= float(stock_flat[k]) <= B[k][1] + 1e-9)]
stock_row_out["at_bounds"] = ("OUT of guided bounds: " + ", ".join(f"{k} {float(stock_flat[k]):.3g}" for k in oob)
                              + "; 3-station flat view shown; scored from the 7-station YAML; fails loadcap_solidity")
# reference: previous round's #4 = bem_9504 (04_T06559), re-scored in this round's settings
ref_flat = json.loads(Path("/workspace/fansim/screen/designs/04_T06559.flat.json").read_text())
ref = S.evaluate(S.blade_from_flat(dict(ref_flat)), dict(ref_flat))
ref["flags"]["aoa_stalled_span"] = bool(ref.get("aoa_stalled_frac", 1.0) <= STALL_FRAC_MAX)
ref["first_fail"] = next((g for g in GUARDS if not ref["flags"].get(g, False)), None)
ref.update(score=S.scalar_score(ref, stock), id="REF_prev04_T06559_bem_9504", stage="ref", flat=ref_flat)
ref_row_out = row_out("ref", ref, "reference")
ref_row_out["at_bounds"] = f"previous-round #4 (CFD 67.7 CFM free); feasible here: {ref['first_fail'] is None} (first_fail {ref['first_fail']})"
v_ref = vec(ref_flat)
summary["ref_9504_rank_among_feasible"] = 1 + sum(r["score"] > ref["score"] for r in feas)
summary["ref_9504_score"] = ref["score"]
summary["n_feasible_beating_stock"] = sum(r["score"] > 1.0 for r in feas)
summary["n_feasible_beating_ref_9504"] = sum(r["score"] > ref["score"] for r in feas)
summary["stock_axial"] = {k: stock[k] for k in ("cfm_free", "cfm_load", "efficiency")}

out_rows = [stock_row_out, ref_row_out]
(SCR / "designs" / "ref_prev04_T06559_bem_9504.flat.json").write_text(json.dumps(ref_flat, indent=2))
save_blade_params(S.blade_from_flat(dict(ref_flat)), SCR / "designs" / "ref_prev04_T06559_bem_9504.blade.yaml")
shutil.copy("config/problems/a12x25_reference.yaml", SCR / "designs" / "ref_STOCK_a12x25_reference.blade.yaml")
for i, r in enumerate(picked, 1):
    tier = "FULL_CFD_top5" if i <= N_CFD else "reserve"
    out_rows.append(row_out(i, r, tier))
    name = f"{i:02d}_{r['id']}"
    flat = dict(r["flat"])
    (SCR / "designs" / f"{name}.flat.json").write_text(json.dumps(flat, indent=2))
    save_blade_params(S.blade_from_flat(flat), SCR / "designs" / f"{name}.blade.yaml")
    # cockpit: runs/<run>/cockpit_assess/design_<trial>/design.json (fan_helpers._load_assessed_designs)
    run = "bem_screen_r3_top5" if i <= N_CFD else "bem_screen_r3_reserve"
    trial = 9600 + i
    dd = SCR / "cockpit_import" / "runs" / run / "cockpit_assess" / f"design_{trial}"
    dd.mkdir(parents=True)
    (dd / "design.json").write_text(json.dumps({
        "trial": trial, "params": flat,
        "objectives": {"cfm_free": r["cfm_free"], "cfm_load": r["cfm_load"], "efficiency": r["efficiency"]},
        "feasible": True,
        "reason": f"BEM SCREEN r3 (axial-force, camber<=0.10) rank {i} ({r['id']}) — BEM-scored, NOT CFD; run Assess",
        "extra": {"bem_screen": True, "bem_rank": i, "bem_id": r["id"], "bem_score_vs_stock": r["score"],
                  "load_preset": "case", "rpm": S.RPM,
                  "pressure_model": "axial_force", "max_camber_bound": 0.10}}, indent=2))
    # coarse CFD (quick tier Q2) job for python -m fansim.optimize.quick_screen <job>
    qj = SCR / "quick_cfd_jobs"; qj.mkdir(exist_ok=True)
    (qj / f"{name}.json").write_text(json.dumps({
        "flat": flat, "workdir": f"runs/bem_screen_quick/{name}",
        "out": f"runs/bem_screen_quick/{name}/result.json", "spec": fan_spec_to_dict(S.SPEC)}, indent=1))
with open(SCR / "shortlist.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(out_rows)
(SCR / "screen_summary.json").write_text(json.dumps(summary, indent=1, default=float))
print(json.dumps(summary, indent=1, default=float)[:6000])
for o in out_rows[:8]:
    print({k: o[k] for k in cols[:26]})
