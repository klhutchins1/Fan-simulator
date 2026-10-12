"""QA r8 Task B runner (prereg 6b0aedf). 2-blade rebuilds; cylinder (prove_direction) and radial
(stacking_cut mode="radial", unchanged from r7) readings on each part and its y-mirror. Resumable."""
import gzip, json, os, sys, time, dataclasses
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(__file__))
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.geometry import build_impeller, export_stl
import fansim.geometry.blade as B
from fansim.audit.direction import prove_direction, tip_lead_sign
from stacking_cut import prove_direction_stacking
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7"; REPO = "/workspace/fansim/repo-r8"
I = {json.loads(l)["id"]: json.loads(l) for l in gzip.open(f"{R7}/stress/inputs.jsonl.gz")}
SAMPLE, OUT = sys.argv[1], sys.argv[2]; TMP = "/tmp/qa8b_part.stl"
items = [json.loads(l) for l in open(SAMPLE)]
if "--no-refs" not in sys.argv: items += [{"cell_sel": "reference", "id": "a12x25_ref_stl", "path": f"{REPO}/validation/reference/a12x25_impeller.stl"},
          {"cell_sel": "reference", "id": "fan01_rotor", "path": f"{REPO}/validation/reference/fan01/fan01_rotor.stl"}]
def pr(p): return {"verdict": p.verdict, "omega": p.omega_sign, "pump": p.pump_sign, "chi": p.chirality, "n": p.n_sections, "note": p.note}
def avail():
    for l in open("/proc/meminfo"):
        if l.startswith("MemAvailable"): return int(l.split()[1]) / 1048576
done = {(json.loads(l)["cell_sel"], json.loads(l)["id"]) for l in open(OUT)} if os.path.exists(OUT) else set()
_val = B.validate_blade_params
for it in items:
    if (it["cell_sel"], it["id"]) in done: continue
    rec = dict(it); t0 = time.monotonic()
    try:
        if "path" in it:
            mesh = trimesh.load(it["path"], force="mesh")
        else:
            r = I[it["id"]]; p = blade_from_flat(r["flat"], Features(**(r.get("features") or {})))
            if it["cell_sel"] == "flipped":
                p = dataclasses.replace(p, stations=[dataclasses.replace(s, max_camber=-0.03) for s in p.stations])
                B.validate_blade_params = lambda _p: None   # QA-side bypass, flipped parts only
            rec["design_camber"] = max((s.max_camber for s in p.stations), key=abs)
            rec["lean_tip"] = max(abs(s.lean_deg) for s in p.stations); rec["n_blades_design"] = p.n_blades
            g0 = time.monotonic()
            while avail() < 3.0 and time.monotonic() - g0 < 600: time.sleep(10)
            try:
                export_stl(build_impeller(dataclasses.replace(p, n_blades=2, blade_angles_deg=None)), TMP)
            finally:
                B.validate_blade_params = _val
            mesh = trimesh.load(TMP, force="mesh")
        mir = mesh.copy(); mir.vertices[:, 1] *= -1; mir.invert()
        rec["cyl"] = pr(prove_direction(mesh)); rec["cyl_mirror"] = pr(prove_direction(mir))
        rec["radial"] = pr(prove_direction_stacking(mesh, mode="radial")[0])
        rec["radial_mirror"] = pr(prove_direction_stacking(mir, mode="radial")[0])
        if "path" in it: rec["tip_lead"] = tip_lead_sign(mesh)
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"[:300]
    rec["mono_s"] = round(time.monotonic() - t0, 1)
    with open(OUT, "a") as fh: fh.write(json.dumps(rec, default=float) + "\n")
    print(it["id"], it["cell_sel"], rec.get("error") or (rec["cyl"]["verdict"], rec["radial"]["verdict"]), rec["mono_s"], flush=True)
print("DONE", flush=True)
