"""Score Task C (prereg 6b0aedf): increment = VmHWM_exit - VmRSS_at_call; guard safe iff
increment <= 1.15*est - RSS_at_call for every build."""
import json, sys
import numpy as np
from fansim.resources import fuse_peak_estimate_gb, FUSE_MARGIN
R = [json.loads(l) for l in open(sys.argv[1])]
rows = []
for r in R:
    if r.get("outcome") != "OK": rows.append({"id": r["id"], "outcome": r.get("outcome")}); continue
    calls = [e for e in r["events"] if e["ev"] == "call"]; ex = [e for e in r["events"] if e["ev"] == "exit"]
    c, x = calls[0], ex[-1]
    G = 1048576
    rss, hwm_call, hwm, av = c["VmRSS"] / G, c["VmHWM"] / G, x["VmHWM"] / G, c["MemAvailable"] / G
    est = fuse_peak_estimate_gb(c["n_faces"]); inc = hwm - rss
    rows.append({"id": r["id"], "n_faces": c["n_faces"], "rss_call": rss, "hwm_at_call": hwm_call, "hwm": hwm, "inc": inc,
                 "est": est, "allow": FUSE_MARGIN * est - rss, "safe": inc <= FUSE_MARGIN * est - rss,
                 "avail_call": av, "avail_ge_inc": av >= inc, "guard_need": FUSE_MARGIN * est,
                 "guard_would_refuse": FUSE_MARGIN * est > av, "hwm_over_est": hwm / est - 1, "n_calls": len(calls), "mono_s": r["mono_s"]})
ok = [x for x in rows if "inc" in x]
f = np.array([x["n_faces"] for x in ok], float)
def fit(y):
    A = np.column_stack([np.ones_like(f), f]); (a, b), res, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ [a, b]; r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return {"intercept_gb": a, "kb_per_face": b * 1048576, "r2": r2, "max_resid_gb": float(np.abs(y - pred).max())}
O = {"n_ok": len(ok), "not_ok": [x for x in rows if "inc" not in x],
     "fit_increment": fit(np.array([x["inc"] for x in ok])), "fit_hwm": fit(np.array([x["hwm"] for x in ok])),
     "fit_rss_at_call": fit(np.array([x["rss_call"] for x in ok])),
     "guard_safe_all": all(x["safe"] for x in ok), "unsafe": [x["id"] for x in ok if not x["safe"]],
     "avail_lt_inc": [x["id"] for x in ok if not x["avail_ge_inc"]],
     "rows": sorted(ok, key=lambda x: x["n_faces"])}
print(json.dumps(O, indent=1, default=float))
