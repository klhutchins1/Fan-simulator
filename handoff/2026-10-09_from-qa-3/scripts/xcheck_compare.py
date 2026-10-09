"""Compare /tmp/r4_mine.jsonl (QA clone, e48a32d+axial patch) vs /tmp/r4_claude.jsonl (5396796)."""
import json, sys
import numpy as np
from scipy.stats import spearmanr
A = {r["id"]: r for r in map(json.loads, open("/tmp/r4_mine.jsonl"))}
B = {r["id"]: r for r in map(json.loads, open("/tmp/r4_claude.jsonl"))}
out = {"n_common": len(set(A) & set(B))}
sp = {}
for k in ("stock7", "paddle89", "rev-45", "rev-60", "zero_blades"):
    a, b = A[k]["default_gap"], B[k]["default_gap"]
    sp[k] = {"mine": a, "claude": b, "guard_fn_claude": B[k].get("guard_fn")}
out["specials"] = sp
ids = [i for i in A if A[i]["kind"] == "screen"]
d = {q: [] for q in ("free", "shut", "peak_eff")}; gdis = []; fdis = []; sc_a = []; sc_b = []; dsc = []; gfn_vs_rule = []
for i in ids:
    a, b = A[i], B[i]
    if "curve" in a and "curve" in b:
        for q in d: d[q].append(abs(a["curve"][q] - b["curve"][q]))
        if a["curve"]["guard_rule"] != b["curve"]["guard_rule"]: gdis.append(i)
    elif ("curve" in a) != ("curve" in b): gdis.append(i)
    if bool(b.get("guard_fn")) != bool(b.get("curve", {}).get("guard_rule")) and "curve" in b: gfn_vs_rule.append((i, b.get("guard_fn"), b["curve"]["guard_rule"]))
    if a["feasible"] != b["feasible"] or a["first_fail"] != b["first_fail"]: fdis.append((i, a["first_fail"], b["first_fail"]))
    if a["score"] is not None and b["score"] is not None:
        sc_a.append(a["score"]); sc_b.append(b["score"]); dsc.append(abs(a["score"] - b["score"]))
for q, v in d.items():
    v = np.array(v); out[f"d_{q}"] = dict(n=len(v), max=float(v.max()), median=float(np.median(v)), n_nonzero=int((v > 1e-12).sum()))
dsc = np.array(dsc); out["d_score"] = dict(n=len(dsc), max=float(dsc.max()), median=float(np.median(dsc)), n_nonzero=int((dsc > 1e-12).sum()))
out["spearman_score"] = float(spearmanr(sc_a, sc_b).correlation)
out["guard_rule_disagreements"] = gdis
out["claude_guard_fn_vs_rule_mismatch"] = gfn_vs_rule[:20]; out["n_claude_guard_fn_vs_rule_mismatch"] = len(gfn_vs_rule)
out["feasibility_disagreements"] = fdis[:20]; out["n_feasibility_disagreements"] = len(fdis)
out["n_guard_refused_claude_screen"] = sum(1 for i in ids if B[i].get("guard_fn"))
out["guard_refused_and_screen_feasible"] = [i for i in ids if B[i].get("guard_fn") and B[i]["feasible"]]
out["n_guard_refused_by_reason"] = {}
for i in ids:
    g = B[i].get("guard_fn") or ""
    if g: key = g.split("(")[0].strip(); out["n_guard_refused_by_reason"][key] = out["n_guard_refused_by_reason"].get(key, 0) + 1
pe = sorted((B[i]["curve"]["peak_eff"], i) for i in ids if "curve" in B[i] and B[i]["curve"]["status"] != "no_rise")
out["lowest_peak_eff_screen"] = pe[:5]
json.dump(out, open("/workspace/fansim/research/proto/r4/xcheck_result.json", "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in out.items() if k not in ("specials",)}, default=float)[:3000])
for k, v in sp.items(): print(k, "mine", {x: (round(y, 4) if isinstance(y, float) else y) for x, y in v["mine"].items()}, "| claude", {x: (round(y, 4) if isinstance(y, float) else y) for x, y in v["claude"].items()}, "| guard:", v["guard_fn_claude"])
