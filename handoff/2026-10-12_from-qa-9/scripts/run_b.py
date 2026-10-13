"""QA r9 Task B (PREREG_R9 a0260c0): built vs sliders on wrapped (cylinder) builds. Round-8 run_d method
(2-blade build_impeller, measure_sections at station radii, analytic NACA camber bias) plus, per station,
whether the hub-face clip reaches it: lone chord-realised blade, untrimmed, unclipped vs clip_blade_below,
both cut at the same radii; reached iff chord_unclipped - chord_clipped > 0.1 mm (or clipped missing).
Usage: python run_b.py <out.jsonl>   (resumable by design name)"""
import csv, gzip, json, os, random, sys, time, dataclasses
import numpy as np, trimesh
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.config import blade_params_from_dict, load_blade_params
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.validation.section_compare import measure_sections, _measure_loop
from fansim.geometry.chord_realisation import prepare_loft_chords
from fansim.geometry.blade import build_blade_solid, clip_blade_below, _hub_axial_range
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"

def naca_bias(m, p, t, n=200):
    x = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1036 * x**4)
    yc = np.where(x < p, m / p**2 * (2 * p * x - x**2), m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2))
    dy = np.where(x < p, 2 * m / p**2 * (p - x), 2 * m / (1 - p)**2 * (p - x)); th = np.arctan(dy)
    xu, yu = x - yt * np.sin(th), yc + yt * np.cos(th); xl, yl = x + yt * np.sin(th), yc - yt * np.cos(th)
    X = np.concatenate([xu[::-1], xl[1:]]) * 30.0; Y = np.concatenate([yu[::-1], yl[1:]]) * 30.0
    R = 1e4; th3 = X / R
    r = _measure_loop(np.column_stack([R * np.cos(th3), R * np.sin(th3), Y]), R, 1, 1)
    return r["camber_ratio"] - m, r["thickness_ratio"] - t

def avail():
    for l in open("/proc/meminfo"):
        if l.startswith("MemAvailable"): return int(l.split()[1]) / 1048576

def designs():
    yield "stock_v3", load_blade_params("config/problems/a12x25_reference.yaml")
    d = json.load(open("docs/qa/benchmarks/lt120/fansim_params.json")); p = blade_params_from_dict(d)
    yield "lt120", dataclasses.replace(p, section_wrap="cylinder")
    rows = {r["design_id"]: r for r in csv.DictReader(open("handoff/2026-10-09_to-qa-2/cfd_designs.csv"))}
    for k in ("t9000", "t9002", "t9003", "t9005"):
        yield k, blade_from_flat(json.loads(rows[k]["flat"]), Features())
    D = [json.loads(l) for l in gzip.open(R7)]
    D = [x for x in D if not x.get("sample_error") and not float(x["flat"].get("shroud_thick_mm") or 0)]
    for x in random.Random(9010).sample(D, 20):
        yield x["id"], blade_from_flat(x["flat"], Features(**(x.get("features") or {})))

OUT = sys.argv[1]
done = {json.loads(l)["design"] for l in open(OUT)} if os.path.exists(OUT) else set()
for name, p in designs():
    if name in done: continue
    t0 = time.monotonic(); rec = {"design": name, "wrap": p.section_wrap, "chord_basis": p.chord_basis}
    try:
        g = time.monotonic()
        while avail() < 2.5 and time.monotonic() - g < 600: time.sleep(10)
        stl = "/tmp/qa9b_full.stl"
        export_stl(build_impeller(dataclasses.replace(p, n_blades=2, blade_angles_deg=None)), stl)
        r0 = p.hub_radius - p.root_embed; span = p.tip_radius - r0
        fr = [min((r0 + span * s.r_frac) / p.tip_radius, 0.99) for s in p.stations]
        meas = measure_sections(stl, tuple(fr), tip_radius_mm=p.tip_radius)
        pr = prepare_loft_chords(p); hub_face = float(_hub_axial_range(p)[0])
        bl = build_blade_solid(pr, _chord_realized=True, _trim_tip=False)
        export_stl(bl, "/tmp/qa9b_un.stl"); export_stl(clip_blade_below(p, bl, hub_face), "/tmp/qa9b_cl.stl")
        mu = measure_sections("/tmp/qa9b_un.stl", tuple(fr), tip_radius_mm=p.tip_radius)
        mc = measure_sections("/tmp/qa9b_cl.stl", tuple(fr), tip_radius_mm=p.tip_radius)
        zmin_un = float(trimesh.load("/tmp/qa9b_un.stl", force="mesh").bounds[0][2])
        rec.update(hub_face_z=hub_face, zmin_unclipped=zmin_un, hang_mm=hub_face - zmin_un, clip_below_hub=bool(p.clip_below_hub))
        st = []
        for i, (s, f, m, u, c) in enumerate(zip(p.stations, fr, meas, mu, mc)):
            cb, tb = naca_bias(s.max_camber, s.camber_pos, s.thickness); rmm = f * p.tip_radius
            x = {"i": i, "r_frac_station": s.r_frac, "r_mm": round(rmm, 2), "chord_p": s.chord, "stagger_p": s.stagger_deg,
                 "camber_p": s.max_camber, "tc_p": s.thickness, "chord_over_r": s.chord / rmm, "camber_bias": cb,
                 "n_read": m.get("n_blades", 0), "lean": s.lean_deg, "skew": getattr(s, "skew", None), "sweep": getattr(s, "sweep", None)}
            cu = u.get("chord_mm") if u.get("n_blades") else None; cc = c.get("chord_mm") if c.get("n_blades") else None
            x["chord_unclipped"], x["chord_clipped"] = cu, cc
            x["clip_reached"] = bool(cu is not None and (cc is None or cu - cc > 0.1))
            if m.get("n_blades"):
                x.update(chord_m=m["chord_mm"], stagger_m=m["stagger_deg"], camber_m=m["camber_ratio"], tc_m=m["thickness_ratio"])
                x["chord_err"] = m["chord_mm"] / s.chord - 1; x["camber_gap_net"] = m["camber_ratio"] - s.max_camber - cb
                x["stagger_err"] = m["stagger_deg"] - s.stagger_deg
                x["material"] = abs(x["chord_err"]) > 0.03 or abs(x["camber_gap_net"]) > 0.005
            st.append(x)
        rec["stations"] = st
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"[:400]
    rec["mono_s"] = round(time.monotonic() - t0, 1)
    with open(OUT, "a") as fh: fh.write(json.dumps(rec, default=float) + "\n")
    print(name, rec.get("error") or (round(rec["hang_mm"], 2), sum(x.get("material", False) for x in rec["stations"]), sum(x["clip_reached"] for x in rec["stations"])), rec["mono_s"], flush=True)
print("DONE", flush=True)
