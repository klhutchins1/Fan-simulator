"""QA r9 Task B.3 (PREREG_R9 a0260c0): hub-face hang over the stress population. 200 random unshrouded,
sample_error-free stress designs (seed 9011), cylinder wrap. Lone chord-realised blade, untrimmed (as
chord_realisation.measure_station_chords builds it): hang = hub_face_z - zmin (mm). For the first 60 also
the clip-reached station count (unclipped vs clip_blade_below chord at each station radius, > 0.1 mm).
Resumable. Usage: python pop_b.py <out.jsonl>"""
import gzip, json, os, random, sys, time, dataclasses
import trimesh
from fansim.geometry import export_stl
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.geometry.chord_realisation import prepare_loft_chords
from fansim.geometry.blade import build_blade_solid, clip_blade_below, _hub_axial_range
from fansim.validation.section_compare import measure_sections
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
D = [json.loads(l) for l in gzip.open(R7)]
D = [x for x in D if not x.get("sample_error") and not float(x["flat"].get("shroud_thick_mm") or 0)]
S = random.Random(9011).sample(D, 200)
OUT = sys.argv[1]; done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
for k, x in enumerate(S):
    if x["id"] in done: continue
    t0 = time.monotonic(); rec = {"id": x["id"], "stratum": x["stratum"], "k": k}
    try:
        p = blade_from_flat(x["flat"], Features(**(x.get("features") or {})))
        hub_face = float(_hub_axial_range(p)[0]); pr = prepare_loft_chords(p)
        bl = build_blade_solid(pr, _chord_realized=True, _trim_tip=False); export_stl(bl, "/tmp/qa9p_un.stl")
        zmin = float(trimesh.load("/tmp/qa9p_un.stl", force="mesh").bounds[0][2])
        rec.update(hub_face_z=hub_face, zmin=zmin, hang_mm=hub_face - zmin, clip_below_hub=bool(p.clip_below_hub),
                   lean_tip=max(abs(s.lean_deg) for s in p.stations), n_stations=len(p.stations))
        if k < 60:
            export_stl(clip_blade_below(p, bl, hub_face), "/tmp/qa9p_cl.stl")
            r0 = p.hub_radius - p.root_embed; span = p.tip_radius - r0
            fr = tuple(min((r0 + span * s.r_frac) / p.tip_radius, 0.99) for s in p.stations)
            mu = measure_sections("/tmp/qa9p_un.stl", fr, tip_radius_mm=p.tip_radius); mc = measure_sections("/tmp/qa9p_cl.stl", fr, tip_radius_mm=p.tip_radius)
            reached = []
            for u, c in zip(mu, mc):
                cu = u.get("chord_mm") if u.get("n_blades") else None; cc = c.get("chord_mm") if c.get("n_blades") else None
                reached.append(bool(cu is not None and (cc is None or cu - cc > 0.1)))
            rec["clip_reached"] = reached; rec["chord_loss_mm"] = [None if not u.get("n_blades") else (u["chord_mm"] - (c["chord_mm"] if c.get("n_blades") else 0)) for u, c in zip(mu, mc)]
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"[:300]
    rec["mono_s"] = round(time.monotonic() - t0, 1)
    with open(OUT, "a") as fh: fh.write(json.dumps(rec) + "\n")
    print(k, x["id"], rec.get("error") or round(rec["hang_mm"], 2), rec["mono_s"], flush=True)
print("DONE", flush=True)
