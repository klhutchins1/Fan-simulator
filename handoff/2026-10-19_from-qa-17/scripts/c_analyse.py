"""QA r17 Task C analysis (PREREG_R17 a212b29). Usage: python c_analyse.py"""
import json, math
D = "/workspace/fansim/qa/r17/data"
A = {json.loads(l)["id"]: json.loads(l) for l in open(f"{D}/c300_analytic.jsonl")}
Bt = {json.loads(l)["id"]: json.loads(l) for l in open(f"{D}/c300_built.jsonl")}
R14 = json.load(open(f"{D}/c_r14.json"))
def wil(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return [round(max(0, c - h), 4), round(min(1, c + h), 4)]
errs = [k for k, v in Bt.items() if "error" in v]
for k, a in A.items():
    a["h_bx"] = Bt[k]["h_bx"] if k in Bt and "error" not in Bt[k] else (0.0 if a["h_x"] <= 0 else None)
n = len(A); out = {"n": n, "built_errors": errs, "shares": {}}
for r in ("base", "i", "ii", "both"):
    c = sum(a[r] for a in A.values()); out["shares"][r] = dict(k=c, share=round(c / n, 4), wilson95=wil(c, n))
def acc(rule, hb_key):
    v = [a for a in A.values() if a[hb_key] is not None]
    over = [a for a in v if a[hb_key] > 2.0]; under = [a for a in v if a[hb_key] <= 2.0]
    miss = [a["id"] for a in over if not a[rule]]; fr = [a["id"] for a in under if a[rule]]
    return dict(n=len(v), built_over_2=len(over), missed=len(miss), missed_ids=miss, sens="PASS" if not miss else "FAIL",
                n_under=len(under), false_refusals=len(fr), false_rate=round(len(fr) / max(1, len(under)), 4), spec="PASS" if len(fr) <= 0.03 * len(under) else "FAIL",
                worst_missed=sorted(((a[hb_key], a["id"], a["h_x"] if rule == "both" else a["h_d"]) for a in over if not a[rule]), reverse=True)[:5])
out["C_both_vs_built_export_hub"] = acc("both", "h_bx")
out["C_i_vs_built_auto_hub_r16"] = acc("i", "h_b_auto")
out["C_ii_vs_built_export_hub"] = acc("ii", "h_bx")
rat = sorted(a["h_bx"] / a["h_x"] for a in A.values() if a["h_bx"] is not None and a["h_x"] >= 0.5)
out["ratio_built_over_designed_export_hub"] = dict(n=len(rat), median=round(rat[len(rat) // 2], 3), p05=round(rat[int(.05 * len(rat))], 3), p95=round(rat[int(.95 * len(rat)) - 1], 3)) if rat else None
out["export_hub"] = dict(grown=sum(a["dh"] > 0 for a in A.values()), dh_max=max(a["dh"] for a in A.values()),
                         hang_at_export=sum(a["h_x"] > 0 for a in A.values()), built_hang_export_over2=sum((a["h_bx"] or 0) > 2 for a in A.values()),
                         built_hang_auto_over2=sum((a["h_b_auto"] or 0) > 2 for a in A.values()))
out["r14"] = {k: {q: R14[k][q] for q in ("base", "i", "ii", "both", "other_refused", "grown")} for k in ("guided_14003", "P0_14004")}
out["C_bounds"] = "PASS" if R14["P0_14004"]["both"]["share"] <= 0.05 else "FAIL"
out["C_bounds_wilson_upper_le_5"] = R14["P0_14004"]["both"]["wilson95"][1] <= 0.05
out["ladder"] = R14.get("ladder")
json.dump(out, open(f"{D}/c_summary.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "ladder"}, indent=0, default=str))
