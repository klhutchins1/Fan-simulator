"""QA r14 Task B5 (PREREG_R14 586bbe9): designed hang vs realised (unclipped, chord-realised, untrimmed lone blade) on
10 hanging designs; explanation test via section points of the realised loft stations. Resumable.
Usage: python b5_hang.py <out.jsonl>"""
import gzip, json, math, os, random, sys, time, dataclasses
import trimesh
import fansim; assert fansim.__file__.startswith("/workspace/fansim/qa/run_r14"), fansim.__file__
from fansim.geometry import export_stl
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.geometry.chord_realisation import prepare_loft_chords
from fansim.geometry import blade as B
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
D = [json.loads(l) for l in gzip.open(R7)]
D = [x for x in D if not x.get("sample_error") and not float(x["flat"].get("shroud_thick_mm") or 0)]
random.Random(14005).shuffle(D)
def sec_zmin(p, n_span=None):
    ns = int(n_span or p.n_span); it = B._interp_stations(p, ns); r0 = p.hub_radius - p.root_embed; kw = B._thick_scale_kw(p); zmin = (math.inf, None)
    for i in range(ns):
        rf = float(it["r_frac"][i])
        pts = B._section_points_3d(r=r0 + (p.tip_radius - r0) * rf, r_frac=rf, chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]),
            thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]), camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]), lean_deg=float(it["lean_deg"][i]), n_chord=p.n_chord, features=p.features,
            le_skew=float(it["le_skew"][i]), tip_notch_count=p.tip_notch_count, tip_notch_depth_mm=p.tip_notch_depth_mm, **kw)
        z = min(v.z for v in pts)
        if z < zmin[0]: zmin = (z, rf)
    return zmin
OUT = sys.argv[1]; done = [json.loads(l) for l in open(OUT)] if os.path.exists(OUT) else []
seen = {r["id"] for r in done}; n_hang = sum(1 for r in done if r.get("designed_hang", 0) > 0)
for x in D:
    if n_hang >= 10: break
    if x["id"] in seen: continue
    t0 = time.monotonic(); rec = {"id": x["id"], "stratum": x["stratum"]}
    p = blade_from_flat(dict(x["flat"], section_wrap="cylinder"), Features(**(x.get("features") or {})))
    h = B.blade_hang_below_hub_mm(p); rec["designed_hang"] = h
    if h <= 0:
        continue  # not a hanging design; not recorded (selection = first 10 with hang > 0)
    try:
        face = float(B._hub_axial_range(p)[0]); pr = prepare_loft_chords(p)
        bl = B.build_blade_solid(pr, _chord_realized=True, _trim_tip=False); export_stl(bl, "/tmp/qa14b5_un.stl")
        zmin = float(trimesh.load("/tmp/qa14b5_un.stl", force="mesh").bounds[0][2]); rec["realised_hang"] = face - zmin
        blt = B.build_blade_solid(pr, _chord_realized=True); export_stl(blt, "/tmp/qa14b5_tr.stl")
        rec["realised_hang_trimmed"] = face - float(trimesh.load("/tmp/qa14b5_tr.stl", force="mesh").bounds[0][2])
        zd, rfd = sec_zmin(p); zr, rfr = sec_zmin(pr); zr4, _ = sec_zmin(pr, 4 * int(pr.n_span))
        rec.update(face=face, n_span=int(p.n_span), designed_sec_hang=face - zd, designed_low_rf=rfd, loftsec_hang=face - zr, loftsec_low_rf=rfr,
                   loftsec_hang_dense=face - zr4, ratio=rec["realised_hang"] / h,
                   chord_design=[s.chord for s in p.stations], chord_loft=[s.chord for s in pr.stations],
                   stagger_design=[s.stagger_deg for s in p.stations], stagger_loft=[s.stagger_deg for s in pr.stations],
                   camber_design=[s.max_camber for s in p.stations], camber_loft=[s.max_camber for s in pr.stations],
                   thick_design=[s.thickness for s in p.stations], thick_loft=[s.thickness for s in pr.stations],
                   r_frac=[s.r_frac for s in p.stations], valid_designed=h <= B.MAX_HANG_BELOW_HUB_MM)
        tol = max(0.1, 0.05 * rec["realised_hang"]); rec["explained_by_loft_stations"] = abs(rec["loftsec_hang"] - rec["realised_hang"]) <= tol
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"[:300]
    rec["mono_s"] = round(time.monotonic() - t0, 1); n_hang += 1
    with open(OUT, "a") as fh: fh.write(json.dumps(rec) + "\n")
    print(x["id"], rec.get("error") or (round(h, 2), round(rec["realised_hang"], 2), round(rec["loftsec_hang"], 2)), rec["mono_s"], flush=True)
print("DONE", flush=True)
