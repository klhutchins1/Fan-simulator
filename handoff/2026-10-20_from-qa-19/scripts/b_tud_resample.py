"""QA r19 B: resample digitised Fig 4 to stations (prereg: first point, 0.20..1.00 step 0.05; tip by linear extrapolation over the last 0.02).
Usage: python b_tud_resample.py <tud_geom_raw.json> <out geom.txt> <out.json>"""
import json, sys
import numpy as np
g = json.load(open(sys.argv[1])); out = {}
def series(k):
    r = np.array(g[k]["r_over_R"]); v = np.array(g[k]["val"]); o = np.argsort(r); r, v = r[o], v[o]
    vs = np.array([np.median(v[max(0, i - 2): i + 3]) for i in range(len(v))])  # 5-px running median
    return r, vs
rc, c = series("chord_c_over_R"); rt, t = series("twist_deg")
r0 = round(max(rc.min(), rt.min()) + 0.002, 3)
st = [r0] + [x for x in np.round(np.arange(0.20, 1.0001, 0.05), 3) if x > r0 + 0.004]
def at(r, rr, vv):
    if r <= rr.max(): return float(np.interp(r, rr, vv))
    m = rr > rr.max() - 0.02; p = np.polyfit(rr[m], vv[m], 1); return float(np.polyval(p, r))
rows = [(r, at(r, rc, c), at(r, rt, t)) for r in st]
u_c = 1.5 * 0.25 / (g["frame"][3] - g["frame"][2]); u_t = 1.5 * 50.0 / (g["frame"][3] - g["frame"][2])
with open(sys.argv[2], "w") as f:
    f.write("r/R   c/R     beta\n"); [f.write(f"{r:.3f}  {cr:.4f}  {b:.3f}\n") for r, cr, b in rows]
json.dump(dict(stations=rows, u_c_over_R=u_c, u_twist_deg=u_t, r_first=r0), open(sys.argv[3], "w"), indent=1)
for r in rows: print("%.3f %.4f %.2f" % r)
print("u c/R %.5f  u twist %.3f deg" % (u_c, u_t))
