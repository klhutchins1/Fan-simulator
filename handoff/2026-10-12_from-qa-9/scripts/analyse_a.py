"""Score Task A against PREREG_R9 (a0260c0 + amendment A1): W1-W5. Usage: python analyse_a.py <designs.jsonl>"""
import json, statistics, sys
from collections import Counter, defaultdict
R = [json.loads(l) for l in open(sys.argv[1])]
O = {"n": len(R), "groups": dict(Counter(r["group"] for r in R)), "job_errors": [r["id"] for r in R if r.get("job_error") or r.get("job_status")]}
W1f, W2f, W3f, W3strict, W3x, vols, ratios, w5 = [], [], [], [], [], [], [], defaultdict(Counter)
cam = defaultdict(list); plan_fail = []
for r in R:
    b, m = r["builds"], r["meas"]; pp, pc = b.get("Pp", {}), b.get("Pc", {})
    if pp.get("outcome") != "OK": plan_fail.append((r["id"], pp.get("outcome"), (pp.get("err") or "")[-150:]))
    if pc.get("outcome") != "OK":
        if pp.get("outcome") == "OK" or (pp.get("outcome") != pc.get("outcome")):
            W1f.append((r["id"], r["group"], "cyl build " + str(pc.get("outcome")), (pc.get("err") or "")[-200:]))
    else:
        M = m.get("Pc", {})
        bad = [k for k in ("k2", "k3", "k4") if not M.get(k)]
        if bad: W1f.append((r["id"], r["group"], bad, {k: M.get(k) for k in ("watertight", "bodies", "degenerate", "zmin", "rmax", "ring_r")}, m.get("hub_face_z")))
    for k in ("Pp", "Pc"):
        K = m.get(k, {}).get("K5")
        if K:
            w5[k][K.get("k5")] += 1
            if K.get("k5") == "INCONCLUSIVE": cam[k].append(K.get("camber_ratio_median"))
            if K.get("k5") == "FAIL" and k == "Pc": O.setdefault("W5_wrong", []).append((r["id"], r["group"], K.get("refusal")))
    if pp.get("outcome") == "OK" and pc.get("outcome") == "OK":
        vp, vc = m["Pp"]["volume"], m["Pc"]["volume"]; d = vc / vp - 1; vols.append(d)
        if abs(d) > 0.05: W2f.append((r["id"], r["group"], round(100 * d, 2)))
        if pp.get("suspect_suspend") or pc.get("suspect_suspend"): W3x.append(r["id"]); continue
        tp, tc = pp["mono_s"], pc["mono_s"]; ratios.append(tc / tp)
        if tc > 2 * tp:
            W3strict.append((r["id"], round(tc, 1), round(tp, 1)))
            if tc - tp > 5: W3f.append((r["id"], r["group"], round(tc, 1), round(tp, 1)))
k7 = Counter(r["checks"].get("K7") for r in R if r.get("kind_C"))
O["W1"] = {"verdict": "PASS" if not W1f else "FAIL", "fails": W1f, "planar_side_failures": plan_fail}
O["W2"] = {"verdict": "PASS" if not W2f else "FAIL", "fails": W2f, "n": len(vols),
           "dV_pct": {"min": round(100 * min(vols), 2), "median": round(100 * statistics.median(vols), 2), "max": round(100 * max(vols), 2)} if vols else None}
O["W3"] = {"verdict": "PASS" if not W3f else "FAIL", "fails": W3f, "strict_ratio_only_fails": W3strict, "excluded_suspend": W3x,
           "ratio": {"median": round(statistics.median(ratios), 3), "max": round(max(ratios), 3), "min": round(min(ratios), 3)} if ratios else None}
O["W4"] = {"verdict": "PASS" if k7.get("FAIL", 0) == 0 and k7.get("FAIL_BUILD", 0) == 0 else "FAIL", "K7": dict(k7),
           "fails": [(r["id"], r["checks"].get("K7"), r["meas"].get("C")) for r in R if r.get("kind_C") and str(r["checks"].get("K7", "")).startswith("FAIL")]}
O["W5"] = {"verdict": "PASS" if not O.get("W5_wrong") else "FAIL", "K5": {k: dict(v) for k, v in w5.items()},
           "inconclusive_camber_median": {k: (round(statistics.median([c for c in v if c is not None]), 4) if any(c is not None for c in v) else None) for k, v in cam.items()},
           "inconclusive_reasons": {k: dict(Counter(r["meas"].get(k, {}).get("K5", {}).get("reason") for r in R if r["meas"].get(k, {}).get("K5", {}).get("k5") == "INCONCLUSIVE")) for k in ("Pp", "Pc")}}
O["by_group_Pc_K5"] = {g: dict(Counter(r["meas"].get("Pc", {}).get("K5", {}).get("k5") for r in R if r["group"] == g)) for g in O["groups"]}
O["by_group_Pp_K5"] = {g: dict(Counter(r["meas"].get("Pp", {}).get("K5", {}).get("k5") for r in R if r["group"] == g)) for g in O["groups"]}
O["peak_mb"] = {k: max((r["builds"].get(k, {}).get("peak_mb") or 0) for r in R) for k in ("Pp", "Pc", "C")}
print(json.dumps(O, indent=1, default=str))
