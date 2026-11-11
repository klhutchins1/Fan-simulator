"""r28 E9b/E7 (PREREG f208f30): rasterise each glyph as cut (0.6 mm square-capped boxes, cell 1.8 x 3.2 mm at r_mid), CAD-free.
Pairwise IoU of rendered glyphs; narrow counters inside a glyph. Usage: python e9_font_raster.py <out.json> <png>"""
import itertools, json, math, sys
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import affinity
import importlib.util, os
_sp = importlib.util.spec_from_file_location('print_id', os.path.join(os.environ.get('REPO', '.'), 'fansim/manufacturability/print_id.py'))
P = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(P)
W, H, SW = P._GLYPH_WIDTH_MM, P.MARK_R_OUTER - P.MARK_R_INNER, P.MARK_STROKE_MM
def glyph_poly(ch):
    polys = []
    for x0, y0, x1, y1 in P.glyph_strokes(ch):
        a, b = (x0 * W, y0 * H), (x1 * W, y1 * H); L = math.dist(a, b); span = L + SW
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        r = box(mx - span / 2, my - SW / 2, mx + span / 2, my + SW / 2)
        polys.append(affinity.rotate(r, math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), origin=(mx, my)))
    return unary_union(polys)
G = {c: glyph_poly(c) for c in P.CHECK_ALPHABET}
R = {"cell_mm": [W, H], "stroke_mm": SW}
iou = []
for a, b in itertools.combinations(P.CHECK_ALPHABET, 2):
    i = G[a].intersection(G[b]).area / G[a].union(G[b]).area; iou.append((round(i, 3), a + b))
iou.sort(reverse=True); R["top_pair_iou"] = iou[:12]
R["identical_when_cut"] = [p for v, p in iou if v >= 0.98]
# glyph extent beyond the cell (caps), and narrow counters (holes or notches < 0.4 mm)
cell = box(0, 0, W, H)
R["extent_outside_cell_mm"] = {c: [round(v, 3) for v in G[c].bounds] for c in P.CHECK_ALPHABET if not cell.buffer(1e-6).contains(G[c])}
narrow = {}
for c, g in G.items():
    land = g.envelope.buffer(0.3).difference(g)  # material around/inside the glyph
    opened = land.buffer(-0.2).buffer(0.2)
    sliver = land.difference(opened)
    parts = [p for p in getattr(sliver, "geoms", [sliver]) if p.area > 0.005]
    if parts: narrow[c] = round(sum(p.area for p in parts), 3)
R["glyphs_with_lands_under_0p4mm_area_mm2"] = narrow
# min land between adjacent glyphs at the inner radius (worst case), all ordered pairs
adv_in = P.GLYPH_ADVANCE_MM * P.MARK_R_INNER / (0.5 * (P.MARK_R_INNER + P.MARK_R_OUTER))
k = P.MARK_R_INNER / (0.5 * (P.MARK_R_INNER + P.MARK_R_OUTER))
gaps = []
for a, b in itertools.product(P.CHECK_ALPHABET, repeat=2):
    ga = affinity.scale(G[a], k, 1, origin=(0, 0)); gb = affinity.translate(affinity.scale(G[b], k, 1, origin=(0, 0)), adv_in)
    gaps.append((round(ga.distance(gb), 3), a + b))
gaps.sort(); R["min_gap_adjacent_glyphs_inner_r_mm"] = gaps[:6]
# render sheet
sc = 40; img = Image.new("L", (int(len(P.CHECK_ALPHABET) * (W + 0.8) * sc) + 20, int((H + 1.2) * sc)), 255); d = ImageDraw.Draw(img)
for n, c in enumerate(P.CHECK_ALPHABET):
    ox = 10 + n * (W + 0.8) * sc
    for p in getattr(G[c], "geoms", [G[c]]):
        d.polygon([(ox + x * sc, (H + 0.6 - y) * sc) for x, y in p.exterior.coords], fill=0)
        for h in p.interiors: d.polygon([(ox + x * sc, (H + 0.6 - y) * sc) for x, y in h.coords], fill=255)
img.save(sys.argv[2])
json.dump(R, open(sys.argv[1], "w"), indent=1); print(json.dumps(R, indent=1))
