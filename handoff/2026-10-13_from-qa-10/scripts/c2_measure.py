"""QA r10b Task C.2 (PREREG_R10 26aa359): built vs sliders on every allowed design with designed hang > 0 (from c1 jsonl).
2-blade build_impeller (shipped path incl. clip correction), measure_sections at _station_measure_fracs; analytic ref =
slider chord / stagger / camber + family-aware estimator bias. Plus clip-reached (r9 criterion) and stations the correction
touched. Resumable. Usage: c2_measure.py <c1.jsonl> <out.jsonl>"""
import gzip, json, os, sys, time, dataclasses
import numpy as np, trimesh
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.features import Features
from fansim.geometry.airfoil import section_loop_2d, SECTION_PLATE
from fansim.optimize.search_space import blade_from_flat
from fansim.validation.section_compare import measure_sections, _measure_loop
from fansim.geometry import chord_realisation as CR
from fansim.geometry.blade import build_blade_solid, clip_blade_below, _hub_axial_range, _thick_scale_kw
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
X = {json.loads(l)["id"]: json.loads(l) for l in gzip.open(R7)}
C1 = [json.loads(l) for l in open(sys.argv[1])]; todo = [r for r in C1 if r.get("valid") and r.get("hang", 0) > 0]
OUT = sys.argv[2]; done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
def bias(p, s, n=200):
    kw = _thick_scale_kw(p); fam = kw["section_family"]
    le, te = (kw["le_thick_scale"], kw["te_thick_scale"]) if fam == SECTION_PLATE else (1.0, 1.0)
    loop = np.asarray(section_loop_2d(fam, max_camber=s.max_camber, camber_pos=s.camber_pos, thickness=s.thickness, n_points=n, te_radius_frac=te, le_radius_frac=le), float)
    X2, Y2 = loop[:, 0] * 30.0, loop[:, 1] * 30.0; Rb = 1e4; th = X2 / Rb
    r = _measure_loop(np.column_stack([Rb * np.cos(th), Rb * np.sin(th), Y2]), Rb, 1, 1)
    return r["camber_ratio"] - s.max_camber, fam
def avail():
    for l in open("/proc/meminfo"):
        if l.startswith("MemAvailable"): return int(l.split()[1]) / 1048576
print("todo", len(todo), flush=True)
for c in todo:
    if c["id"] in done: continue
    x = X[c["id"]]; t0 = time.monotonic(); rec = {"id": c["id"], "designed_hang": c["hang"]}
    try:
        g = time.monotonic()
        while avail() < 2.5 and time.monotonic() - g < 600: time.sleep(10)
        p = blade_from_flat(dict(x["flat"], section_wrap="cylinder"), Features(**(x.get("features") or {})))
        rec["family"] = _thick_scale_kw(p)["section_family"]
        loft0 = CR.with_loft_chords(p, CR.loft_chords_for_measured_targets(p)); loft1 = CR.prepare_loft_chords(p)
        touched = [abs(a.max_camber - b.max_camber) > 1e-9 or abs(a.stagger_deg - b.stagger_deg) > 1e-9 for a, b in zip(loft0.stations, loft1.stations)]
        stl = "/tmp/qa10c_full.stl"; export_stl(build_impeller(dataclasses.replace(p, n_blades=2, blade_angles_deg=None)), stl)
        fr = CR._station_measure_fracs(p); idx = [i for i, f in enumerate(fr) if f is not None]
        meas = measure_sections(stl, tuple(fr[i] for i in idx), tip_radius_mm=p.tip_radius)
        hub_face = float(_hub_axial_range(p)[0]); bl = build_blade_solid(loft1, _chord_realized=True, _trim_tip=False)
        export_stl(bl, "/tmp/qa10c_un.stl"); export_stl(clip_blade_below(p, bl, hub_face), "/tmp/qa10c_cl.stl")
        mu = measure_sections("/tmp/qa10c_un.stl", tuple(fr[i] for i in idx), tip_radius_mm=p.tip_radius)
        mc = measure_sections("/tmp/qa10c_cl.stl", tuple(fr[i] for i in idx), tip_radius_mm=p.tip_radius)
        st = []
        for i, m, u, cl in zip(idx, meas, mu, mc):
            s = p.stations[i]; cb, fam = bias(p, s)
            y = {"i": i, "r_mm": round(fr[i] * p.tip_radius, 2), "chord_p": s.chord, "stagger_p": s.stagger_deg, "camber_p": s.max_camber, "bias": cb, "touched": touched[i], "n_read": m.get("n_blades", 0)}
            cu = u.get("chord_mm") if u.get("n_blades") else None; cc = cl.get("chord_mm") if cl.get("n_blades") else None
            y["clip_reached"] = bool(cu is not None and (cc is None or cu - cc > 0.1))
            if m.get("n_blades"):
                y.update(chord_m=m["chord_mm"], stagger_m=m["stagger_deg"], camber_m=m["camber_ratio"])
                y["chord_err"] = m["chord_mm"] / s.chord - 1; y["camber_gap_net"] = m["camber_ratio"] - s.max_camber - cb; y["stagger_err"] = m["stagger_deg"] - s.stagger_deg
                y["fail"] = abs(y["chord_err"]) > 0.03 or abs(y["camber_gap_net"]) > 0.005 or abs(y["stagger_err"]) > 1.5
            st.append(y)
        rec["stations"] = st; rec["n_unreadable_frac_none"] = sum(f is None for f in fr)
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"[:400]
    rec["mono_s"] = round(time.monotonic() - t0, 1)
    with open(OUT, "a") as fh: fh.write(json.dumps(rec, default=float) + "\n")
    print(c["id"], rec.get("error") or sum(y.get("fail", False) for y in rec["stations"]), rec["mono_s"], flush=True)
print("DONE", flush=True)
