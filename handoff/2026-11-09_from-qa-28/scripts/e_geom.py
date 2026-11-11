"""r28 E2-E5, E7, E9a/c (PREREG f208f30): measure marked vs sibling print-ready STLs (and STEP solid count). No CFD.
Usage: <repo .venv python> e_geom.py <geo dir> <out.json> <screens dir>   (QA venv: trimesh, shapely, PIL; REPO env = clone path; mount.json from the repo venv)"""
import ast, json, math, sys
from pathlib import Path
import numpy as np, trimesh
from shapely.geometry import Polygon, MultiPolygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
from PIL import Image, ImageDraw
G = Path(sys.argv[1]); OUT = sys.argv[2]; SH = Path(sys.argv[3])
import importlib.util, os, types
_sp = importlib.util.spec_from_file_location('print_id', os.path.join(os.environ['REPO'], 'fansim/manufacturability/print_id.py'))
P = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(P)
mount = types.SimpleNamespace(**json.load(open(G / "mount.json")))
src = Path("/workspace/fansim/repo-r9/handoff/2026-10-12_from-qa-9/scripts/job_a.py").read_text()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "cup_measure")
ns = {"np": np, "math": math}; exec(ast.get_source_segment(src, fn), ns); cup_measure = ns["cup_measure"]
R = {}
code = json.load(open(G / "export.json"))["code"]; R["code"] = code
import re
M = {}
for tag in ("sibling", "marked"):
    m = trimesh.load(G / f"{tag}.stl", force="mesh"); M[tag] = m
    stxt = open(G / f"{tag}.step", errors="ignore").read()
    R[tag] = {"step_manifold_solid_brep": len(re.findall(r"MANIFOLD_SOLID_BREP", stxt)), "step_bytes": len(stxt), "watertight": bool(m.is_watertight), "winding_consistent": bool(m.is_winding_consistent),
              "bodies": len(m.split(only_watertight=False)), "volume_mm3": float(m.volume), "euler": int(m.euler_number),
              "faces": len(m.faces), "zmin": float(m.bounds[0][2]), "zmax": float(m.bounds[1][2])}
zt = R["sibling"]["zmax"]; R["z_top"] = zt
R["dV_mm3"] = R["sibling"]["volume_mm3"] - R["marked"]["volume_mm3"]
def sec(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return Polygon()
    p2, _ = s.to_planar(to_2D=np.eye(4) @ np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -z], [0, 0, 0, 1]]))
    return unary_union([Polygon(pg.exterior, pg.interiors) for pg in p2.polygons_full]).buffer(0)
def removed(z):
    return sec(M["sibling"], z).difference(sec(M["marked"], z)).buffer(-0.002).buffer(0.002)
# depth profile
prof = {}
for dz in (0.05, 0.25, 0.45, 0.48, 0.52, 0.55, 0.6, 1.0, 3.0):
    prof[dz] = round(removed(zt - dz).area, 4)
R["removed_area_by_depth_mm2"] = prof
mid = removed(zt - 0.25); R["mid_removed_area_mm2"] = round(mid.area, 3)
# z profile slab check (E5): sections below z_top-0.6 equal
R["slab_diff_area_below_0p6"] = {z: round(sec(M["sibling"], z).symmetric_difference(sec(M["marked"], z)).area, 4)
                                 for z in (zt - 0.6, zt - 1.0, zt - 3.0, zt - 8.0, R["sibling"]["zmin"] + 0.5)}
# E4 location
pts = np.vstack([np.asarray(p.exterior.coords) for p in getattr(mid, "geoms", [mid])])
rr = np.hypot(pts[:, 0], pts[:, 1]); th = np.degrees(np.arctan2(pts[:, 1], pts[:, 0]))
R["removed_r_range"] = [float(rr.min()), float(rr.max())]; R["removed_theta_range_deg"] = [float(th.min()), float(th.max())]
R["E4_in_band"] = bool(rr.min() >= P.MARK_R_INNER - 0.05 and rr.max() <= P.MARK_R_OUTER + 0.05)
# E9c keep-out: hub-top face polygon (sibling section just below top) contains footprint dilated 1 mm
top = sec(M["sibling"], zt - 0.01)
R["E9c_footprint_plus1mm_on_top_face"] = bool(top.buffer(1e-3).contains(mid.buffer(1.0)))
R["E9c_dist_to_bore_mm"] = float(rr.min() - 10.0); R["E9c_dist_to_rim_mm"] = float(P_hub - rr.max()) if (P_hub := 21.5) else None
# E5 K7
for tag in ("sibling", "marked"):
    hub_face = None
    R[tag]["K7"] = cup_measure(M[tag], R["sibling"]["zmin"], mount)
# E7 widths: groove width via opening; lands (counters) via holes; per glyph components
comps = list(getattr(mid, "geoms", [mid]))
R["groove_components"] = len(comps)
R["groove_survives_open_0p25"] = round(mid.buffer(-0.25).buffer(0.25).area / mid.area, 3)
R["groove_survives_open_0p29"] = round(mid.buffer(-0.29).buffer(0.29).area / mid.area, 3)
def inscribed_w(poly):
    lo, hi = 0.0, 2.0
    for _ in range(25):
        d = (lo + hi) / 2
        (lo, hi) = (d, hi) if not poly.buffer(-d).is_empty else (lo, d)
    return 2 * lo
holes = []
for c in comps:
    for h in c.interiors:
        hp = Polygon(h); holes.append({"area": round(hp.area, 3), "max_inscribed_w_mm": round(inscribed_w(hp), 3),
                                       "centroid_r": round(math.hypot(hp.centroid.x, hp.centroid.y), 2)})
R["counter_lands"] = holes
# land slivers across the whole band (material between grooves within the glyph hull area)
hull = mid.convex_hull; land = hull.difference(mid)
for w in (0.2, 0.4):
    sl = land.difference(land.buffer(-w / 2).buffer(w / 2))
    R[f"land_area_narrower_than_{w}mm"] = round(sum(p.area for p in getattr(sl, "geoms", [sl]) if p.area > 0.002), 3)
# per-glyph assignment + neighbour gaps
r_mid = 0.5 * (P.MARK_R_INNER + P.MARK_R_OUTER); dth = P.GLYPH_ADVANCE_MM / r_mid; th0 = math.radians(P.MARK_THETA0_DEG)
centres = [th0 + (i - 2) * dth for i in range(5)]
def ang(p): return math.atan2(p.centroid.y, p.centroid.x)
per = {i: [] for i in range(5)}
for c in comps: per[int(np.argmin([abs(ang(c) - t) for t in centres]))].append(c)
gl = {i: unary_union(v) for i, v in per.items()}
R["neighbour_glyph_gap_mm"] = [round(gl[i].distance(gl[i + 1]), 3) for i in range(4)]
# E9a chirality: map to view from outside +Z (looking -Z), glyph up = radially outward => "right" = decreasing theta
def to_view(poly, tc):
    def f(x, y, z=None):
        r = math.hypot(x, y); t = math.atan2(y, x)
        return ((tc - t) * r_mid, r - P.MARK_R_INNER)
    from shapely.ops import transform
    return transform(lambda xs, ys, zs=None: tuple(zip(*[f(x, y) for x, y in zip(xs, ys)])) if False else (
        [f(x, y)[0] for x, y in zip(xs, ys)], [f(x, y)[1] for x, y in zip(xs, ys)]), poly)
W, H, SW = P._GLYPH_WIDTH_MM, P.MARK_R_OUTER - P.MARK_R_INNER, P.MARK_STROKE_MM
def font_poly(ch, mirror=False):
    ps = []
    for x0, y0, x1, y1 in P.glyph_strokes(ch):
        if mirror: x0, x1 = 1 - x0, 1 - x1
        a, b = ((x0 - 0.5) * W, y0 * H), ((x1 - 0.5) * W, y1 * H); L = math.dist(a, b); span = L + SW
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ps.append(affinity.rotate(box(mx - span / 2, my - SW / 2, mx + span / 2, my + SW / 2), math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), origin=(mx, my)))
    return unary_union(ps)
def iou(a, b): return a.intersection(b).area / max(a.union(b).area, 1e-9)
code_n = P.normalize_read(code)
# Independent read: order glyph blobs left-to-right as seen from +Z (x right at theta0 = 90 deg), then match each blob
# against every font glyph, normal and mirrored, in its own local frame (no assumption about the code's layout).
blobs = sorted(gl.values(), key=lambda g: g.centroid.x)
read, mirrored_hits, chir = "", 0, []
for g in blobs:
    tc = math.atan2(g.centroid.y, g.centroid.x)
    v = to_view(g, tc)
    v = affinity.translate(v, -(v.bounds[0] + v.bounds[2]) / 2 + 0.0, 0)
    best = max(((iou(v, font_poly(c, m)), c, m) for c in P.CHECK_ALPHABET for m in (False, True)), key=lambda t: t[0])
    normal = max((iou(v, font_poly(c)), c) for c in P.CHECK_ALPHABET)
    is_mirr = bool(best[2] and best[0] > normal[0] + 1e-3)  # symmetric glyphs (W, X, ...) tie: not mirrored
    read += best[1] if is_mirr else normal[1]; mirrored_hits += is_mirr
    chir.append({"best": best[1], "best_is_mirrored": is_mirr, "best_iou": round(best[0], 3), "best_unmirrored": normal[1], "best_unmirrored_iou": round(normal[0], 3)})
R["E9a_per_glyph"] = chir
R["E9a_read_left_to_right_from_plus_Z"] = read
R["E9a_glyphs_unmirrored"] = mirrored_hits == 0
R["E9a_order_matches_code"] = read == code_n
# render view from +Z (looking -Z), mark up = +Y (theta0 = 90 deg so this is a literal top view, x right)
sc = 60; xs = np.vstack([np.asarray(p.exterior.coords) for p in comps])
x0, x1, y0, y1 = xs[:, 0].min() - 1, xs[:, 0].max() + 1, xs[:, 1].min() - 1, xs[:, 1].max() + 1
img = Image.new("L", (int((x1 - x0) * sc), int((y1 - y0) * sc)), 235); d = ImageDraw.Draw(img)
for p in comps:
    d.polygon([((x - x0) * sc, (y1 - y) * sc) for x, y in p.exterior.coords], fill=20)
    for h in p.interiors: d.polygon([((x - x0) * sc, (y1 - y) * sc) for x, y in h.coords], fill=235)
img.save(SH / "e9a_marked_top_view_from_plusZ.png")
img.transpose(Image.FLIP_LEFT_RIGHT).save(SH / "e9a_same_mirrored_for_comparison.png")
# aero area ratio (report only)
R["recess_area_ratio_of_hub_disk_pct"] = round(100 * mid.area / (math.pi * 21.5 ** 2), 3)
k0, k1 = R["sibling"]["K7"], R["marked"]["K7"]
R["E5_K7_identical"] = all(abs((k0.get(k) or 0) - (k1.get(k) or 0)) < 1e-6 for k in ("floor_above_hub_face", "grip_count", "grip_protrude_mm", "cup_dia_mm"))
json.dump(R, open(OUT, "w"), indent=1, default=float); print(json.dumps(R, indent=1, default=float))
