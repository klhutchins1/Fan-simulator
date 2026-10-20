"""QA r17 Task B method 1 (vector): EPJ WoC 180:02023 Figs 6, 7, 8. Marker centres = bbox centres of the stroked marker
paths; axes from the vector grid lines (exact). Usage: python b_epj.py"""
import json, math
import numpy as np, pdfplumber
PDF = "/workspace/fansim/qa/r17_src/epj2018_02023.pdf"; OUT = "/workspace/fansim/qa/r17/b/epj_m1.json"
pdf = pdfplumber.open(PDF)
# axes: (page, x px list -> values, y px list -> values, log flags, plot box, legend box to exclude)
FIG = {
 "fig6": dict(page=3, X={347.97: 0, 378.17: 50, 408.29: 100, 438.49: 150, 468.69: 200, 498.89: 250, 529.01: 300},
              Y={233.05: 0, 219.23: 50, 205.48: 100, 191.66: 150, 177.92: 200, 164.18: 250, 150.35: 300, 136.61: 350, 122.79: 400, 109.04: 450, 95.3: 500},
              logx=False, logy=False, box=(345, 93, 531, 235), legend=(457.1, 200.2, 524.7, 228.3),
              series={"A_const_current_9000": ("rect", "(0.753, 0.0, 0.0)"), "B_const_rpm_9000": ("curve", "(0.0, 0.439, 0.753)")}),
 "fig7": dict(page=3, X={345.88: 10, 381.59: 20, 402.44: 30, 417.29: 40, 428.72: 50, 438.14: 60, 446.05: 70, 452.92: 80, 458.99: 90, 464.42: 100, 500.12: 200, 520.97: 300},
              Y={587.31: 10, 518.03: 100, 448.84: 1000, 452.04: 900, 455.55: 800, 459.55: 700, 464.18: 600, 469.69: 500, 476.41: 400, 485.04: 300, 497.26: 200,
                 521.23: 90, 524.75: 80, 528.82: 70, 533.46: 60, 538.89: 50, 545.6: 40, 554.23: 30, 566.45: 20},
              logx=True, logy=True, box=(343, 446, 531, 590), legend=(464.3, 548.4, 525.9, 582.6),
              series={"plastic_6000": ("curve", "(0.0, 0.69, 0.314)"), "plastic_9000": ("curve", "(0.0, 0.439, 0.753)"), "plastic_11000": ("rect", "(0.753, 0.0, 0.0)")}),
 "fig8": dict(page=4, X={94.25: 0, 124.68: 50, 155.04: 100, 185.47: 150, 215.82: 200, 246.26: 250, 276.61: 300},
              Y={232.42: 200, 204.62: 250, 176.81: 300, 148.93: 350, 121.13: 400, 93.33: 450},
              logx=False, logy=False, box=(92, 91, 279, 235), legend=(100, 135, 130, 225),
              series={"plastic_wheel0_9000": ("curve", "(0.0, 0.69, 0.314)")}),
}
res = {"pdf": PDF, "figs": {}}
for fid, F in FIG.items():
    p = pdf.pages[F["page"] - 1]
    def fit(D, log):
        px = np.array(list(D.keys())); v = np.array(list(D.values()), float); v = np.log10(v) if log else v
        A = np.polyfit(px, v, 1); r = v - np.polyval(A, px); return A, r
    ax, rx = fit(F["X"], F["logx"]); ay, ry = fit(F["Y"], F["logy"])
    xv = list(F["X"].values()); yv = list(F["Y"].values())
    fsx = (math.log10(max(xv)) - math.log10(min(xv))) if F["logx"] else max(xv) - min(xv)
    fsy = (math.log10(max(yv)) - math.log10(min(yv))) if F["logy"] else max(yv) - min(yv)
    cal = dict(x_fit=list(ax), y_fit=list(ay), x_res_max=float(abs(rx).max()), y_res_max=float(abs(ry).max()), x_fs=fsx, y_fs=fsy,
               logx=F["logx"], logy=F["logy"], units_x="L/min", units_y="Pa", res_units="log10 decades" if F["logx"] else "data units")
    cal["B_cal"] = "PASS" if cal["x_res_max"] <= 0.005 * fsx and cal["y_res_max"] <= 0.005 * fsy else "FAIL"
    x0, t0, x1, b0 = F["box"]; lx0, lt0, lx1, lb0 = F["legend"]; pts = []
    for name, (typ, col) in F["series"].items():
        objs = (p.rects if typ == "rect" else p.curves)
        for o in objs:
            if str(o.get("stroking_color")) != col or (o["x1"] - o["x0"]) > 8: continue
            cx, cy = (o["x0"] + o["x1"]) / 2, (o["top"] + o["bottom"]) / 2
            if not (x0 < cx < x1 and t0 < cy < b0) or (lx0 <= cx <= lx1 and lt0 <= cy <= lb0): continue
            q = np.polyval(ax, cx); y = np.polyval(ay, cy)
            pts.append(dict(curve=name, cx_pt=cx, cy_pt=cy, w_pt=o["x1"] - o["x0"], Q=float(10 ** q if F["logx"] else q), dP=float(10 ** y if F["logy"] else y)))
    pts.sort(key=lambda d: (d["curve"], d["Q"]))
    res["figs"][fid] = dict(page=F["page"], cal=cal, points=pts)
    print(fid, json.dumps({k: cal[k] for k in ("x_res_max", "y_res_max", "B_cal")}), {s: sum(p_["curve"] == s for p_ in pts) for s in F["series"]})
json.dump(res, open(OUT, "w"), indent=1)
