"""QA r17 Task B method 1: Shigemitsu 2018 Fig. 8 (static-pressure efficiency, CFD only), black markers."""
import json
import numpy as np, cv2
SRC = "/workspace/fansim/qa/r17_src/img/shig-001.jpg"; OUT = "/workspace/fansim/qa/r17/b/shig_fig8_m1.json"
im = cv2.imread(SRC); H, W, _ = im.shape; b, g, r = [im[:, :, i].astype(int) for i in range(3)]; gr = (r + g + b) / 3


def lines(mask, axis, thr):
    s = mask.sum(axis); idx = [i for i, c in enumerate(s) if c > thr]; groups = []
    for i in idx:
        if groups and i - groups[-1][-1] <= 2: groups[-1].append(i)
        else: groups.append([i])
    return [float(np.mean(gp)) for gp in groups]


def assign(px, v0, p0, pitch, step):
    out = {}
    for p in px:
        k = round((p - p0) / pitch)
        if abs((p - p0) - k * pitch) < 6: out.setdefault(round(v0 + k * step, 6), []).append(p)
    return {v: float(np.mean(ps)) for v, ps in out.items()}


gray = (gr > 90) & (gr < 200) & (np.abs(r - b) < 30); dark = gr < 100
X = assign(lines(gray, 0, 200) + lines(dark[200:1100], 0, 700), 0.0, 195.0, 158.0, 0.2)
Y = assign(lines(gray, 1, 200) + lines(dark[:, 250:1150], 1, 700), 100.0, 147.0, 135.3, -20.0)
X = {k: v for k, v in X.items() if 0 <= k <= 1.2}; Y = {k: v for k, v in Y.items() if -40 <= k <= 100}
def fit(d):
    v = np.array(list(d.keys())); p = np.array(list(d.values())); A = np.polyfit(p, v, 1); return A, v - np.polyval(A, p)
ax, rx = fit(X); ay, ry = fit(Y)
cal = dict(x_ticks=X, y_ticks=Y, x_fit=list(ax), y_fit=list(ay), x_res_max=float(np.abs(rx).max()), y_res_max=float(np.abs(ry).max()), x_fs=1.2, y_fs=140.0)
cal["B_cal"] = "PASS" if cal["x_res_max"] <= 0.006 and cal["y_res_max"] <= 0.7 else "FAIL"
blk = (gr < 80).astype(np.uint8) * 255; y0 = int(Y[100.0]) + 3; blk[:y0] = 0; blk[:, :int(X[0.0]) + 3] = 0
blk[:240, :600] = 0  # legend box (y 13-221, x < 593)
op = cv2.morphologyEx(blk, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
n, lab, st, cen = cv2.connectedComponentsWithStats(op); pts = []
for i in range(1, n):
    x, y, w, h, a = st[i]
    if a < 80 or w > 45 or h > 45: continue
    fill = a / (w * h); rel = (cen[i][1] - (y + h / 2)) / h
    kind = "cal_total" if fill > 0.70 else ("cal_front" if rel > 0.03 else ("cal_rear" if rel < -0.03 else "unclassified"))
    px, py = (cen[i][0], cen[i][1]) if kind == "cal_total" else (x + w / 2.0, y + h / 2.0)
    pts.append(dict(curve=kind, px=float(px), py=float(py), Q=float(np.polyval(ax, px)), eta=float(np.polyval(ay, py)), marker_w_px=int(w)))
pts.sort(key=lambda p: (p["curve"], p["Q"]))
json.dump(dict(src=SRC, size=[W, H], cal=cal, q_per_px=abs(ax[0]), pct_per_px=abs(ay[0]), points=pts), open(OUT, "w"), indent=1)
print(json.dumps(cal))
for p in pts: print(p["curve"], round(p["Q"], 4), round(p["eta"], 2), p["marker_w_px"])
