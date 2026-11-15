"""r28 E3/E7: recess floor depth by sectioning marked vs sibling STL (QA venv). Usage: e_depth.py <sibling.stl> <marked.stl> <out.json>"""
import json, sys
import numpy as np, trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union
a, b = (trimesh.load(p, force="mesh") for p in sys.argv[1:3]); zt = float(a.bounds[1][2])
def sec(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    p2, _ = s.to_2D(to_2D=np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -z], [0, 0, 0, 1.0]]))
    return unary_union([Polygon(pg.exterior, pg.interiors) for pg in p2.polygons_full]).buffer(0)
def rem(d): return sec(a, zt - d).difference(sec(b, zt - d)).area
lo, hi = 0.3, 1.0
for _ in range(14):
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if rem(mid) > 1.0 else (lo, mid)
R = {"z_top": zt, "floor_depth_mm": round((lo + hi) / 2, 4), "area_at": {d: round(rem(d), 3) for d in (0.3, 0.49, 0.51, 0.6, 0.64, 0.66)}}
json.dump(R, open(sys.argv[3], "w"), indent=1); print(R)
