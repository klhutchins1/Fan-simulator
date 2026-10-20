"""QA r17 Task B (PREREG_R17 a212b29): method 1 (automated) digitising of Shigemitsu 2018 Fig. 7 (raster, 1223x1304).
Calibration from detected grid lines; red open circles by Hough on the red mask; black markers by opening + shape."""
import json, sys
import numpy as np, cv2
SRC = "/workspace/fansim/qa/r17_src/img/shig-000.jpg"; OUT = "/workspace/fansim/qa/r17/b/shig_fig7_m1.json"
im = cv2.imread(SRC); H, W, _ = im.shape; b, g, r = [im[:, :, i].astype(int) for i in range(3)]; gr = (r + g + b) / 3


def lines(mask, axis, thr):
    s = mask.sum(axis); idx = [i for i, c in enumerate(s) if c > thr]; groups = []
    for i in idx:
        if groups and i - groups[-1][-1] <= 2: groups[-1].append(i)
        else: groups.append([i])
    return [float(np.mean(gp)) for gp in groups]


gray = (gr > 90) & (gr < 200) & (np.abs(r - b) < 30)
xc = lines(gray, 0, 200); yc = lines(gray, 1, 200)
dark = gr < 100
xf = lines(dark[200:1100], 0, 700); yf = lines(dark[:, 250:1150], 1, 700)
# assign: x grid lines + frame; Q ticks 0..1.2 step 0.2, pitch ~157.6 px
def assign(px, v0, p0, pitch, step):
    out = {}
    for p in px:
        k = round((p - p0) / pitch)
        if abs((p - p0) - k * pitch) < 6: out.setdefault(round(v0 + k * step, 6), []).append(p)
    return {v: float(np.mean(ps)) for v, ps in out.items()}
X = assign(xc + xf, 0.0, 224.5, 157.6, 0.2); Y = assign(yc + yf, 600.0, 190.0, 118.06, -100.0)
def fit(d):
    v = np.array(list(d.keys())); p = np.array(list(d.values())); A = np.polyfit(p, v, 1); res = v - np.polyval(A, p)
    return A, res
ax, rx = fit(X); ay, ry = fit(Y)
cal = dict(x_ticks=X, y_ticks=Y, x_fit=list(ax), y_fit=list(ay), x_res_max=float(np.abs(rx).max()), y_res_max=float(np.abs(ry).max()),
           x_fs=1.2, y_fs=800.0)
cal["B_cal"] = "PASS" if cal["x_res_max"] <= 0.005 * 1.2 and cal["y_res_max"] <= 0.005 * 800 else "FAIL"
to_q = lambda px: float(np.polyval(ax, px)); to_p = lambda py: float(np.polyval(ay, py))
x0, x1, y0, y1 = int(X[0.0]) - 15, int(X[1.2]) + 15, int(Y[600.0]) + 3, int(Y[-200.0]) + 15
# red open circles
red = ((r - g > 40) & (r - b > 25) & (r > 170)).astype(np.uint8) * 255
red[:y0] = 0; red[:, :x0] = 0
circ = cv2.HoughCircles(cv2.GaussianBlur(red, (5, 5), 1.5), cv2.HOUGH_GRADIENT, dp=1, minDist=18, param1=80, param2=10, minRadius=9, maxRadius=16)
exp = []
for cx, cy, rr in (circ[0] if circ is not None else []):
    # require a ring: red pixels on the circle and not in the centre
    ang = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    dil = cv2.dilate(red, np.ones((3, 3), np.uint8))
    best = max((np.mean([dil[int(round(cy + R_ * np.sin(t))), int(round(cx + R_ * np.cos(t)))] > 0 for t in ang]), R_) for R_ in np.arange(12.0, 16.1, 0.5))
    if best[0] > 0.45: exp.append((float(cx), float(cy), float(best[1]), float(best[0])))
# refine centres: least-squares circle fit to red pixels in an annulus, then drop duplicates
ys_, xs_ = np.nonzero(red); ref = []
for cx, cy, rr, sc in exp:
    d = np.hypot(xs_ - cx, ys_ - cy); m = (d > rr - 4) & (d < rr + 4)
    if m.sum() > 20:
        A = np.c_[2 * xs_[m], 2 * ys_[m], np.ones(m.sum())]; bb = xs_[m] ** 2 + ys_[m] ** 2
        (ccx, ccy, c0), *_ = np.linalg.lstsq(A, bb, rcond=None); rad = np.sqrt(c0 + ccx ** 2 + ccy ** 2)
        if abs(rad - 14) < 3 and np.hypot(ccx - cx, ccy - cy) < 5: cx, cy, rr = ccx, ccy, rad
    if all(np.hypot(cx - q[0], cy - q[1]) > 15 for q in ref): ref.append((float(cx), float(cy), float(rr), float(sc)))
exp = [e for e in ref if e[3] > 0.51 and abs(e[2] - 13.0) <= 0.35]  # marker-size consistency filter (true markers r = 12.7-13.1 px)
exp.sort()
# black markers
blk = (gr < 80).astype(np.uint8) * 255; blk[:y0] = 0; blk[:, :x0] = 0; blk[y1:] = 0; blk[:, x1:] = 0
op = cv2.morphologyEx(blk, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
n, lab, st, cen = cv2.connectedComponentsWithStats(op)
black = []
for i in range(1, n):
    x, y, w, h, a = st[i]
    if a < 80 or w > 40 or h > 40: continue
    fill = a / (w * h); cyy = cen[i][1]; rel = (cyy - (y + h / 2)) / h
    kind = "circle" if fill > 0.70 else ("up" if rel > 0.03 else ("down" if rel < -0.03 else "?"))
    # triangle marker reference point = bbox centre (plotting symbols are centred on the bbox)
    px, py = (x + w / 2.0, y + h / 2.0) if kind != "circle" else (cen[i][0], cen[i][1])
    black.append(dict(kind=kind, px=float(px), py=float(py), w=int(w), h=int(h), fill=float(fill)))
pix_q = abs(ax[0]); pix_p = abs(ay[0])
pts = [dict(curve="exp_total", px=cx, py=cy, Q=to_q(cx), dP=to_p(cy), marker_r_px=rr, ring=sc) for cx, cy, rr, sc in exp]
name = {"circle": "cal_total", "up": "cal_front", "down": "cal_rear", "?": "unclassified"}
pts += [dict(curve=name[m["kind"]], px=m["px"], py=m["py"], Q=to_q(m["px"]), dP=to_p(m["py"]), marker_w_px=m["w"]) for m in sorted(black, key=lambda m: m["px"])]
json.dump(dict(src=SRC, size=[W, H], cal=cal, q_per_px=pix_q, pa_per_px=pix_p, points=pts), open(OUT, "w"), indent=1)
print(json.dumps(cal)); print("q/px", pix_q, "Pa/px", pix_p)
for p in pts: print(p["curve"], round(p["Q"], 4), round(p["dP"], 1), round(p["px"]), round(p["py"]), round(p.get("marker_r_px", 0), 1), round(p.get("ring", 0), 2))
