"""QA r19 B (PREREG_R19 cab2825): digitise TUD benchmark Fig 4 (raster image embedded in the CC BY 4.0 PDF) chord and twist.
Usage: python b_tud_geom.py <fig4.png> <out.json>"""
import json, sys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(int); H, W, _ = a.shape
R, G, B = a[..., 0], a[..., 1], a[..., 2]
dark = (R < 90) & (G < 90) & (B < 90)
# frame: longest dark vertical / horizontal runs
col = dark.sum(0); row = dark.sum(1)
vx = [x for x in range(W) if col[x] > 0.6 * H * 0.8]
hy = [y for y in range(H) if row[y] > 0.6 * W * 0.8]
xl, xr = min(vx), max(vx); yt, yb = min(hy), max(hy)
# ticks on the bottom frame: dark pixels just above the bottom line, 3..9 px up
band = dark[yb - 9:yb - 3, :].sum(0)
tx = []; x = xl + 3
while x < xr - 2:
    if band[x] >= 4:
        s = x
        while x < xr and band[x] >= 4: x += 1
        tx.append((s + x - 1) / 2.0)
    x += 1
tx = [xl] + tx + [xr]
lband = dark[:, xl + 3:xl + 9].sum(1)
ty = []; y = yt + 3
while y < yb - 2:
    if lband[y] >= 4:
        s = y
        while y < yb and lband[y] >= 4: y += 1
        ty.append((s + y - 1) / 2.0)
    y += 1
ty = [yt] + ty + [yb]
xv = np.linspace(0, 1, len(tx)); fx = np.polyfit(tx, xv, 1); rx = float(np.max(np.abs(np.polyval(fx, tx) - xv)))
yv = np.linspace(0.30, 0.05, len(ty)); fy = np.polyfit(ty, yv, 1); ry = float(np.max(np.abs(np.polyval(fy, ty) - yv)) / 0.25)
red = (R > 170) & (G < 110) & (B < 110); blue = (B > 150) & (R < 130) & (G < 150) & (B - R > 60)
legend = np.zeros_like(red); legend[: int(yt + 0.22 * (yb - yt)), int(xl + 0.6 * (xr - xl)):] = True
out = dict(frame=[xl, xr, yt, yb], xticks=tx, yticks=ty, resid_x=rx, resid_y_frac=ry, px_per_rR=1 / fx[0])
for name, m, conv in (("chord_c_over_R", red & ~legend, lambda v: v), ("twist_deg", blue & ~legend, lambda v: (v - 0.05) / 0.25 * 50.0)):
    xs, ys, th = [], [], []
    for x in range(xl + 2, xr - 1):
        yy = np.nonzero(m[yt + 2:yb - 2, x])[0]
        if len(yy) >= 2 and yy.max() - yy.min() < 12:
            xs.append(x); ys.append(yt + 2 + yy.mean()); th.append(yy.max() - yy.min() + 1)
    rr = np.polyval(fx, xs); vv = conv(np.polyval(fy, ys))
    out[name] = dict(r_over_R=rr.tolist(), val=vv.tolist(), thick_px=float(np.median(th)), n=len(xs))
    print(name, "n", len(xs), "r/R %.3f..%.3f" % (rr.min(), rr.max()), "line px", np.median(th))
out["B_cal"] = rx <= 0.005 and ry <= 0.005
print("frame", out["frame"], "ticks", len(tx), len(ty), "resid", rx, ry, "B_cal", out["B_cal"])
json.dump(out, open(sys.argv[2], "w"))
