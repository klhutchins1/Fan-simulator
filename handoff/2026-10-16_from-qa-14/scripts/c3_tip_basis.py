"""QA r14 C3, report-only: tip-station stagger error against the design stagger linearly interpolated (mid->tip) at the
actual measuring radius 0.99 R (instead of the r_frac 1.0 value). tip = r_mm(tip)/0.99, r0 = 2 r_mm(mid) - tip."""
import json, statistics as S, sys
R = [json.loads(l) for l in open(sys.argv[1])]
rows = []
for r in R:
    s1, s2 = [s for s in r["stations"] if s["k"] == 1][0], [s for s in r["stations"] if s["k"] == 2][0]
    tip = s2["r_mm"] / 0.99; r0 = 2 * s1["r_mm"] - tip; rf = (s2["r_mm"] - r0) / (tip - r0)
    st_i = s1["stagger_p"] + (s2["stagger_p"] - s1["stagger_p"]) * (rf - 0.5) / 0.5
    rows.append({"i": r["i"], "rf_meas": rf, "err_vs_station": s2["stagger_err"], "err_vs_interp": s2["stagger_m"] - st_i})
e1 = [x["err_vs_station"] for x in rows]; e2 = [x["err_vs_interp"] for x in rows]
out = {"rf_meas_range": [min(x["rf_meas"] for x in rows), max(x["rf_meas"] for x in rows)],
       "vs_station": {"mean": S.mean(e1), "max": max(e1), "n_over_1.5": sum(abs(v) > 1.5 for v in e1)},
       "vs_interp": {"mean": S.mean(e2), "max": max(e2), "n_over_1.5": sum(abs(v) > 1.5 for v in e2)}, "rows": rows}
json.dump(out, open(sys.argv[2], "w"), indent=1); print({k: v for k, v in out.items() if k != "rows"})
