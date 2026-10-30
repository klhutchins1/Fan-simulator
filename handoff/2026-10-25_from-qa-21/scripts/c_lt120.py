"""QA r21 C: lt120 reference build cut check (no CFD). Run from repo-r21 root with its .venv."""
import dataclasses, json, sys, time, math
from pathlib import Path
import numpy as np, trimesh

T0 = time.monotonic()
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
import fansim.geometry.blade as B
from fansim.geometry.config import load_blade_params
from fansim.geometry.export import export_stl
from fansim.geometry.features import Features
from fansim.validation.section_compare import measure_sections, _measure_loop
from fansim.audit.direction import prove_direction

G = json.load(open("docs/qa/benchmarks/lt120/geometry.json"))
TAB = [dict(r=s["r_mm"]["value"], chord=s["chord_mm"]["value"], stagger=s["stagger_deg"]["value"],
            camber=s["max_camber"]["value"]) for s in G["stations"]]
base = load_blade_params("docs/qa/benchmarks/lt120/fansim_params.json")
TIP = float(base.tip_radius)
log = lambda *a: print(f"[{time.monotonic()-T0:7.1f}s]", *a, flush=True)

def ref_reading(p, st, r_mm, omega):
    kw = B._thick_scale_kw(p); kw["wrap"] = True
    pts = B._section_points_3d(r=r_mm, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg,
        thickness=st.thickness, max_camber=st.max_camber, camber_pos=st.camber_pos, sweep=0.0, skew=0.0,
        le_sweep=0.0, lean_deg=0.0, n_chord=60, features=Features(), **kw)
    return _measure_loop(np.array([[v.x, v.y, v.z] for v in pts]), r_mm, omega, 1)

def mesh_info(stl):
    m = trimesh.load(str(stl), force="mesh"); m.merge_vertices()
    pr = prove_direction(m)
    return dict(watertight=bool(m.is_watertight), bodies=len(m.split(only_watertight=False)),
                volume_mm3=float(m.volume), zmin=float(m.bounds[0][2]), zmax=float(m.bounds[1][2]),
                rmax=float(np.hypot(m.vertices[:, 0], m.vertices[:, 1]).max()),
                direction=str(getattr(pr, "verdict", pr)), omega_sign=getattr(pr, "omega_sign", None))

def cut(tag, stl, p):
    rows = measure_sections(stl, [t["r"] / TIP for t in TAB], tip_radius_mm=TIP)
    out = []
    for t, st, row in zip(TAB, p.stations, rows):
        rec = dict(build=tag, r_mm=t["r"], table_chord=t["chord"], table_stagger=t["stagger"],
                   table_camber=t["camber"], n_blades=row.get("n_blades", 0))
        if not row.get("n_blades"):
            rec.update(verdict="N/M"); out.append(rec); continue
        a = ref_reading(p, st, float(row["r_mm"]), int(row.get("omega_sign", 1)))
        rec.update(chord=row["chord_mm"], stagger=row["stagger_deg"], camber=row["camber_ratio"],
                   omega_sign=row.get("omega_sign"), ref_chord=a["chord_mm"], ref_stagger=a["stagger_deg"],
                   ref_camber=a["camber_ratio"])
        rec["chord_err_pct"] = 100 * (rec["chord"] / t["chord"] - 1)
        rec["camber_err"] = rec["camber"] - rec["ref_camber"]
        rec["stagger_err_deg"] = rec["stagger"] - rec["ref_stagger"]
        rec["raw_camber_minus_table"] = rec["camber"] - t["camber"]
        rec["raw_stagger_minus_table"] = rec["stagger"] - t["stagger"]
        rec["est_bias_camber"] = rec["ref_camber"] - t["camber"]
        rec["est_bias_stagger"] = rec["ref_stagger"] - t["stagger"]
        ok = (abs(rec["chord_err_pct"]) <= 3.0, abs(rec["camber_err"]) <= 0.005, abs(rec["stagger_err_deg"]) <= 1.5)
        rec["pass_chord"], rec["pass_camber"], rec["pass_stagger"] = ok
        rec["verdict"] = "PASS" if all(ok) else "FAIL"
        out.append(rec)
    return out

summary = {}
# ---- primary P: clip_below_hub=False, shipping build_impeller
P = dataclasses.replace(base, section_wrap="cylinder", clip_below_hub=False)
Pc = dataclasses.replace(base, section_wrap="cylinder")  # clip on, for hang numbers
summary["designed_hang_mm"] = B.blade_hang_below_hub_mm(Pc)
try:
    B.validate_blade_params(Pc); summary["validate_clip_on"] = "accepted"
except ValueError as e:
    summary["validate_clip_on"] = f"refused: {e}"
B.validate_blade_params(P); summary["validate_P"] = "accepted"
log("building P impeller")
imp = B.build_impeller(P)
export_stl(imp, OUT / "lt120_P_impeller.stl")
summary["P_solids"] = len(imp.val().Solids()); summary["P_mesh"] = mesh_info(OUT / "lt120_P_impeller.stl")
bladeP = B.build_blade_solid(P)
summary["P_built_hang_mm_vs_clip_on_hub_face"] = B.blade_hang_built_mm(Pc, bladeP)
summary["P_hub_axial_range"] = list(B._hub_axial_range(P, bladeP))
log("P built; cutting")
rows = cut("P", OUT / "lt120_P_impeller.stl", P)
# ---- secondary S: clip on, skip only the hang test
orig_validate = B.validate_blade_params
B.validate_blade_params = lambda p: orig_validate(dataclasses.replace(p, clip_below_hub=False))
B._refuse_if_built_hang_past_limit = lambda p, b: None
log("building S impeller")
try:
    impS = B.build_impeller(Pc)
    export_stl(impS, OUT / "lt120_S_impeller.stl")
    summary["S_solids"] = len(impS.val().Solids()); summary["S_mesh"] = mesh_info(OUT / "lt120_S_impeller.stl")
    bladeS = B.build_blade_solid(Pc)
    summary["S_built_hang_unclipped_mm"] = B.blade_hang_built_mm(Pc, bladeS)
    rows += cut("S", OUT / "lt120_S_impeller.stl", Pc)
except Exception as e:  # report, don't fix
    summary["S_error"] = repr(e)
summary["elapsed_s"] = time.monotonic() - T0
json.dump(dict(summary=summary, rows=rows), open(OUT / "c_lt120.json", "w"), indent=1, default=str)
log("done")
