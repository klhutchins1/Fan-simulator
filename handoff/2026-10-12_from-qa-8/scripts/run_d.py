"""QA r8 Task D (prereg 6b0aedf): param vs cylinder-cut section at each station radius, for chord_basis
measured and loft. 2-blade builds (disclosed). Camber estimator bias from an analytic NACA 4-digit
section with the station's own (m, p, t/c), read by the same _measure_loop (near-planar, r = 1e4 mm)."""
import csv, json, sys, dataclasses
import numpy as np
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.config import blade_params_from_dict
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.validation.blade_golden import stock_a12x25_params
from fansim.validation.section_compare import measure_sections, _measure_loop
from fansim.geometry.chord_realisation import _station_measure_fracs, prepare_loft_chords

def naca_bias(m, p, t, n=200):
    x = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1036 * x**4)
    yc = np.where(x < p, m / p**2 * (2 * p * x - x**2), m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2))
    dy = np.where(x < p, 2 * m / p**2 * (p - x), 2 * m / (1 - p)**2 * (p - x)); th = np.arctan(dy)
    xu, yu = x - yt * np.sin(th), yc + yt * np.cos(th); xl, yl = x + yt * np.sin(th), yc - yt * np.cos(th)
    X = np.concatenate([xu[::-1], xl[1:]]) * 30.0; Y = np.concatenate([yu[::-1], yl[1:]]) * 30.0
    R = 1e4; th3 = X / R
    pts = np.column_stack([R * np.cos(th3), R * np.sin(th3), Y])
    r = _measure_loop(pts, R, 1, 1)
    return r["camber_ratio"] - m, r["thickness_ratio"] - t

def designs():
    yield "stock", stock_a12x25_params()
    d = json.load(open("docs/qa/benchmarks/lt120/fansim_params.json")); yield "lt120", blade_params_from_dict(d)
    rows = [r for r in csv.DictReader(open("handoff/2026-10-09_to-qa-2/cfd_designs.csv")) if r["design_id"] != "stock"][:5]
    for r in rows: yield r["design_id"], blade_from_flat(json.loads(r["flat"]), Features())

out = []
for name, p0 in designs():
    for basis in ("measured", "loft"):
        p = dataclasses.replace(p0, chord_basis=basis)
        loft = [s.chord for s in prepare_loft_chords(p).stations]
        stl = f"/tmp/qa8d_{name}_{basis}.stl"
        export_stl(build_impeller(dataclasses.replace(p, n_blades=2, blade_angles_deg=None)), stl)
        r0 = p.hub_radius - p.root_embed; span = p.tip_radius - r0
        fr = [(r0 + span * s.r_frac) / p.tip_radius for s in p.stations]
        fr_m = [min(f, 0.99) for f in fr]
        meas = measure_sections(stl, tuple(fr_m), tip_radius_mm=p.tip_radius)
        rc = _station_measure_fracs(p)
        for i, (s, f, m) in enumerate(zip(p.stations, fr_m, meas)):
            rmm = f * p.tip_radius
            cb, tb = naca_bias(s.max_camber, s.camber_pos, s.thickness)
            rec = {"design": name, "basis": basis, "i": i, "r_frac_station": s.r_frac, "r_mm": round(rmm, 2),
                   "realisation_measures_here": rc[i] is not None, "loft_chord": round(loft[i], 2),
                   "chord_p": s.chord, "stagger_p": s.stagger_deg, "camber_p": s.max_camber, "tc_p": s.thickness,
                   "chord_over_r": s.chord / rmm, "camber_bias": cb, "tc_bias": tb, "n_read": m.get("n_blades", 0)}
            if m.get("n_blades"):
                rec.update(chord_m=m["chord_mm"], stagger_m=m["stagger_deg"], camber_m=m["camber_ratio"], tc_m=m["thickness_ratio"])
                rec["chord_err"] = m["chord_mm"] / s.chord - 1
                rec["camber_gap_net"] = m["camber_ratio"] - s.max_camber - cb
            out.append(rec); print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()}), flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
print("DONE")
