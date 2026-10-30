"""QA r22 B (PREREG_R22 715891f): cut the COMMITTED lt120 freeze STL at the 10 table radii (no rebuild, no CFD).
Run from repo-r22 root with its .venv:  .venv/bin/python b_lt120_recut.py <out_dir> <r21_c_lt120.json>"""
import json, sys, time, hashlib
from pathlib import Path
import numpy as np, trimesh

T0 = time.monotonic()
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
R21 = json.load(open(sys.argv[2]))["rows"]
import fansim.geometry.blade as B
from fansim.geometry.config import load_blade_params
from fansim.geometry.features import Features
from fansim.validation.section_compare import measure_sections, _measure_loop
from fansim.audit.direction import prove_direction

STL = Path("validation/reference/lt120/lt120.stl")
assert STL.exists(), "freeze STL missing (prereg: rebuild only then)"
G = json.load(open("docs/qa/benchmarks/lt120/geometry.json"))
TAB = [dict(r=s["r_mm"]["value"], chord=s["chord_mm"]["value"], stagger=s["stagger_deg"]["value"],
            camber=s["max_camber"]["value"]) for s in G["stations"]]
p = load_blade_params("validation/reference/lt120/params.json")
TIP = float(p.tip_radius)
log = lambda *a: print(f"[{time.monotonic()-T0:7.1f}s]", *a, flush=True)

def ref_reading(st, r_mm, omega):  # identical to r21 c_lt120.py
    kw = B._thick_scale_kw(p); kw["wrap"] = True
    pts = B._section_points_3d(r=r_mm, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg,
        thickness=st.thickness, max_camber=st.max_camber, camber_pos=st.camber_pos, sweep=0.0, skew=0.0,
        le_sweep=0.0, lean_deg=0.0, n_chord=60, features=Features(), **kw)
    return _measure_loop(np.array([[v.x, v.y, v.z] for v in pts]), r_mm, omega, 1)

summ = dict(stl=str(STL), sha256=hashlib.sha256(STL.read_bytes()).hexdigest(), stl_bytes=STL.stat().st_size,
            params=dict(reference_build=p.reference_build, clip_below_hub=p.clip_below_hub,
                        section_wrap=p.section_wrap, n_blades=p.n_blades))
m = trimesh.load(str(STL), force="mesh"); m.merge_vertices()
summ["mesh"] = dict(watertight=bool(m.is_watertight), bodies=len(m.split(only_watertight=False)),
                    volume_mm3=float(m.volume), zmin=float(m.bounds[0][2]), zmax=float(m.bounds[1][2]),
                    rmax=float(np.hypot(m.vertices[:, 0], m.vertices[:, 1]).max()), faces=len(m.faces))
log("mesh", summ["mesh"])
t = time.monotonic(); pr = prove_direction(m)
summ["direction"] = dict(verdict=str(getattr(pr, "verdict", pr)), omega_sign=getattr(pr, "omega_sign", None),
                         secs=round(time.monotonic() - t, 1))
log("direction", summ["direction"])
rows_m = measure_sections(STL, [x["r"] / TIP for x in TAB], tip_radius_mm=TIP)
r21 = {(x["build"], x["r_mm"]): x for x in R21}
rows = []
for x, st, row in zip(TAB, p.stations, rows_m):
    rec = dict(r_mm=x["r"], table_chord=x["chord"], table_stagger=x["stagger"], table_camber=x["camber"],
               n_blades=row.get("n_blades", 0))
    if not row.get("n_blades"):
        rec["verdict"] = "N/M"; rows.append(rec); continue
    a = ref_reading(st, float(row["r_mm"]), int(row.get("omega_sign", 1)))
    rec.update(chord=row["chord_mm"], stagger=row["stagger_deg"], camber=row["camber_ratio"],
               omega_sign=row.get("omega_sign"), ref_stagger=a["stagger_deg"], ref_camber=a["camber_ratio"])
    rec["chord_err_pct"] = 100 * (rec["chord"] / x["chord"] - 1)
    rec["camber_err"] = rec["camber"] - rec["ref_camber"]
    rec["stagger_err_deg"] = rec["stagger"] - rec["ref_stagger"]
    ok = (abs(rec["chord_err_pct"]) <= 3.0, abs(rec["camber_err"]) <= 0.005, abs(rec["stagger_err_deg"]) <= 1.5)
    rec["verdict"] = "PASS" if all(ok) else "FAIL"
    for tag in ("S", "P"):
        o = r21.get((tag, x["r"]))
        if o and o.get("chord"):
            rec[f"d_chord_pct_vs_r21{tag}"] = 100 * (rec["chord"] / o["chord"] - 1)
            rec[f"d_stagger_vs_r21{tag}"] = rec["stagger"] - o["stagger"]
            rec[f"d_camber_vs_r21{tag}"] = rec["camber"] - o["camber"]
            rec[f"r21{tag}_chord"] = o["chord"]
    rows.append(rec)
cut = [r for r in rows if r["r_mm"] > 25]
summ["r23_NM"] = rows[0]["verdict"] == "N/M"
summ["pass_count"] = sum(r["verdict"] == "PASS" for r in cut)
summ["B_pass"] = summ["r23_NM"] and summ["pass_count"] == 9
summ["matches_r21S"] = all(abs(r["d_chord_pct_vs_r21S"]) <= 0.5 and abs(r["d_stagger_vs_r21S"]) <= 0.1
                           and abs(r["d_camber_vs_r21S"]) <= 0.001 for r in cut)
summ["elapsed_s"] = time.monotonic() - T0
json.dump(dict(summary=summ, rows=rows), open(OUT / "b_lt120_recut.json", "w"), indent=1, default=str)
log("done", summ["pass_count"], summ["B_pass"], summ["matches_r21S"])
