"""QA r10b Task C.2 analysis (PREREG_R10 26aa359). Usage: analyse_c2.py <c2.jsonl>"""
import json, sys
from collections import Counter
R = [json.loads(l) for l in open(sys.argv[1])]
st = [(r["id"], r.get("family"), y) for r in R if "stations" in r for y in r["stations"]]
rd = [(i, f, y) for i, f, y in st if "chord_err" in y]
fails = [(i, f, y["i"], round(y["chord_err"], 4), round(y["camber_gap_net"], 4), round(y["stagger_err"], 2), y["clip_reached"], y["touched"]) for i, f, y in rd if y["fail"]]
mx = lambda k, sub: max((abs(y[k]) for _, _, y in sub), default=None)
out = {"designs": len(R), "errors": [(r["id"], r["error"]) for r in R if "error" in r], "families": Counter(r.get("family") for r in R),
       "stations": len(st), "readable": len(rd), "unread_n0": sum(1 for *_, y in st if "chord_err" not in y), "fails": fails,
       "designs_failing": sorted({f[0] for f in fails}), "verdict": "PASS" if not fails and all("error" not in r for r in R) else "FAIL",
       "clip_reached": sum(y["clip_reached"] for *_, y in rd), "touched": sum(y["touched"] for *_, y in rd)}
for lab, sub in (("all", rd), ("clip_reached", [x for x in rd if x[2]["clip_reached"]]), ("touched", [x for x in rd if x[2]["touched"]])):
    out[f"max_{lab}"] = {k: mx(k, sub) for k in ("chord_err", "camber_gap_net", "stagger_err")}
print(json.dumps(out, default=str, indent=0)[:3000])
