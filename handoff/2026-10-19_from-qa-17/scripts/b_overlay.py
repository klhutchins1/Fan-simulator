"""QA r17 Task B method 2 helper: zoomed crop with a data-unit grid (from the axis calibration only) for manual reading.
Usage: python b_overlay.py <m1.json> <out.png> q0 q1 p0 p1 dq dp [scale]"""
import json, sys
import numpy as np
from PIL import Image, ImageDraw
d = json.load(open(sys.argv[1])); im = Image.open(d["src"]).convert("RGB")
ax, ay = d["cal"]["x_fit"], d["cal"]["y_fit"]
q0, q1, p0, p1, dq, dp = map(float, sys.argv[3:9]); S = int(sys.argv[9]) if len(sys.argv) > 9 else 4
logx = d["cal"].get("logx", False); logy = d["cal"].get("logy", False)
fx = (lambda v: np.log10(v)) if logx else (lambda v: v); fy = (lambda v: np.log10(v)) if logy else (lambda v: v)
px = lambda q: (fx(q) - ax[1]) / ax[0]; py = lambda p: (fy(p) - ay[1]) / ay[0]
X0, X1 = sorted([px(q0), px(q1)]); Y0, Y1 = sorted([py(p0), py(p1)])
cr = im.crop((int(X0), int(Y0), int(X1) + 1, int(Y1) + 1)).resize(((int(X1) - int(X0) + 1) * S, (int(Y1) - int(Y0) + 1) * S), Image.LANCZOS)
dr = ImageDraw.Draw(cr)
for k, q in enumerate(np.arange(q0, q1 + 1e-9, dq)):
    x = (px(q) - int(X0)) * S; dr.line([(x, 0), (x, cr.size[1])], fill=(0, 120, 255) if k % 5 else (0, 0, 200), width=1)
    if k % 5 == 0: dr.text((x + 2, 2), f"{q:g}", fill=(0, 0, 200))
for k, p in enumerate(np.arange(p0, p1 + 1e-9, dp)):
    y = (py(p) - int(Y0)) * S; dr.line([(0, y), (cr.size[0], y)], fill=(0, 160, 0) if k % 5 else (0, 90, 0), width=1)
    if k % 5 == 0: dr.text((2, y + 2), f"{p:g}", fill=(0, 90, 0))
cr.save(sys.argv[2]); print(cr.size)
