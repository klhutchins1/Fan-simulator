"""QA r10b Task B analysis (PREREG_R10 26aa359) -> b_analysis.json. Usage: analyse_b.py <designs.jsonl> <out.json>"""
import json, sys
from collections import Counter
R = [json.loads(l) for l in open(sys.argv[1])]
A = {"n": len(R), "groups": Counter(r["group"] for r in R)}
oc = Counter(); W = {k: [] for k in ("W1", "W2", "W3", "W3_strict", "W4", "W5", "W6")}; refused = []; fb = []; susp = []; inconc = Counter()
for r in R:
    B = r["builds"]; M = r["meas"]; i = r["id"]
    for k in ("Pp", "Pc", "C"):
        if k in B: oc[f"{k}:{B[k]['outcome']}"] += 1
    pc, pp = B.get("Pc", {}), B.get("Pp", {})
    if pc.get("outcome") == "REFUSED_HANG": refused.append((i, r.get("designed_hang"))); continue
    if pp.get("outcome") == "OK" or pc:
        mc = M.get("Pc")
        ok = pc.get("outcome") == "OK" and mc and mc["k2"] and mc["k3"] and mc["k4"]
        if pp.get("outcome") in ("OK",) or pc.get("outcome") == "OK" or pc:
            if not ok: W["W1"].append({"id": i, "group": r["group"], "Pc": pc.get("outcome"), "Pp": pp.get("outcome"), "err": (pc.get("err") or "")[-200:], "peak_mb": pc.get("peak_mb"), "meas": {k: mc.get(k) for k in ("watertight", "bodies", "degenerate", "k3", "k4")} if mc else None, "job": r.get("job_status")})
    mp = M.get("Pp"); mc = M.get("Pc")
    if mp and mc:
        dv = mc["volume"] / mp["volume"] - 1
        if abs(dv) > 0.05: W["W2"].append((i, round(dv, 4)))
        if pc.get("suspect_suspend") or pp.get("suspect_suspend"): susp.append(i)
        else:
            tc, tp = pc["mono_s"], pp["mono_s"]
            if tc > 2 * tp and tc - tp > 5: W["W3"].append((i, r["group"], tc, tp))
            if tc > 2 * tp: W["W3_strict"].append((i, tc, tp))
    if mc:
        k5 = mc.get("K5", {}).get("k5")
        if k5 == "FAIL": W["W5"].append(i)
        inconc[f"Pc:{k5}"] += 1
    if mp: inconc[f"Pp:{mp.get('K5', {}).get('k5')}"] += 1
    if pc.get("outcome") == "OK":
        calls = pc.get("fuse_calls") or []
        hb = [c for c in calls if c["n_tools"] > 1]
        ring = [c for c in calls if c["n_tools"] == 1 and not c["one_by_one"]]
        fired = len(hb) >= 2; fb.append(fired)
        last = hb[-1]["solids"] if hb else None
        good = (last == 1) and all(c["solids"] == 1 for c in ring[-1:]) and mc and mc["watertight"] and mc["bodies"] == 1
        if not good: W["W6"].append({"id": i, "calls": calls, "wt": mc and mc["watertight"], "bodies": mc and mc["bodies"]})
    if pc.get("err") and "did not join into one solid" in pc["err"]: W["W6"].append({"id": i, "err": pc["err"][-200:]})
    k7 = r["checks"].get("K7")
    if k7 and k7 not in ("PASS", "N/A", "N/A_SKIPPED_MEM"): W["W4"].append((i, k7, M.get("C")))
A.update(outcomes=oc, refused_hang=refused, suspect_suspend=susp, K5=inconc, K7=Counter(r["checks"].get("K7") for r in R if "K7" in r["checks"]),
         fallback_fired=sum(fb), fallback_of=len(fb), fails=W, verdict={k: ("PASS" if not v else f"FAIL x{len(v)}") for k, v in W.items()},
         ratios_time=sorted(round(r["builds"]["Pc"]["mono_s"] / r["builds"]["Pp"]["mono_s"], 2) for r in R if r["builds"].get("Pc", {}).get("outcome") == "OK" and r["builds"].get("Pp", {}).get("outcome") == "OK"),
         peak_mb_max=max((r["builds"].get("Pc", {}).get("peak_mb") or 0) for r in R))
json.dump(A, open(sys.argv[2], "w"), indent=1, default=str)
print(json.dumps({k: A[k] for k in ("n", "outcomes", "refused_hang", "fallback_fired", "fallback_of", "verdict", "K7", "suspect_suspend", "peak_mb_max")}, default=str))
