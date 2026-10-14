"""QA r10b Task C.1 (PREREG_R10 26aa359): designed hang (blade_hang_below_hub_mm) on r9 B.3 200 (seed 9011) + 200 fresh
(seed 10012, remaining sample_error-free rows, shrouded allowed); validate agreement; r of the lowest point. Usage: c1_hang.py <out.jsonl>"""
import gzip, json, math, random, sys
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.geometry import blade as B
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
R9 = "/workspace/fansim/repo-r9/handoff/2026-10-12_from-qa-9/data/b_population.jsonl.gz"
D = [json.loads(l) for l in gzip.open(R7)]; ok = [x for x in D if not x.get("sample_error")]
uns = [x for x in ok if not float(x["flat"].get("shroud_thick_mm") or 0)]
S9 = random.Random(9011).sample(uns, 200); ids9 = {x["id"] for x in S9}
r9 = {}
for l in gzip.open(R9):
    r = json.loads(l); r9[r["id"]] = r
assert ids9 <= set(r9), len(ids9 - set(r9))
rest = [x for x in ok if x["id"] not in ids9]; S10 = random.Random(10012).sample(rest, 200)
def lowest_r(p):
    z_face = B._hub_axial_range(p)[0]; it = B._interp_stations(p, p.n_span); r0 = p.hub_radius - p.root_embed; kw = B._thick_scale_kw(p); best = (math.inf, None, None)
    for i in range(p.n_span):
        rf = float(it["r_frac"][i]); r = r0 + (p.tip_radius - r0) * rf
        pts = B._section_points_3d(r=r, r_frac=rf, chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]), thickness=float(it["thickness"][i]),
              max_camber=float(it["max_camber"][i]), camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]), skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]),
              lean_deg=float(it["lean_deg"][i]), n_chord=p.n_chord, features=p.features, le_skew=float(it["le_skew"][i]), tip_notch_count=p.tip_notch_count, tip_notch_depth_mm=p.tip_notch_depth_mm, **kw)
        for v in pts:
            if v.z < best[0]: best = (v.z, math.hypot(v.x, v.y), rf)
    return best
with open(sys.argv[1], "w") as fh:
    for src, S in (("r9", S9), ("fresh", S10)):
        for x in S:
            rec = {"id": x["id"], "src": src, "stratum": x["stratum"], "shrouded": bool(float(x["flat"].get("shroud_thick_mm") or 0))}
            try:
                p = blade_from_flat(dict(x["flat"], section_wrap="cylinder"), Features(**(x.get("features") or {})))
                rec["wrap"] = p.section_wrap; rec["clip"] = bool(p.clip_below_hub); h = B.blade_hang_below_hub_mm(p); rec["hang"] = h
                zl, rl, rf = lowest_r(p); rec.update(low_r=rl, low_rf=rf, hub_r=p.hub_radius)
                try: B.validate_blade_params(p); rec["valid"] = True
                except ValueError as e: rec["valid"] = False; rec["refusal"] = str(e)[:300]
                if src == "r9": rec["r9_realised_hang"] = r9[x["id"]].get("hang_mm")
            except Exception as e: rec["error"] = f"{type(e).__name__}: {e}"[:300]
            fh.write(json.dumps(rec) + "\n")
print("DONE")
