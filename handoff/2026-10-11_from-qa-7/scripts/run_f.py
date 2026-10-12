"""Task F runner: rebuild parts (2 blades, the validator minimum, to keep fuse memory low), then read the direction
with the current cylinder proof, the stacking-cut prototype and the radial-plane variant, on each part and its y-mirror.
Appends one JSON line per part to the output; parts already present are skipped (resumable)."""
import csv, json, sys, os, time, dataclasses, glob
import numpy as np, trimesh
from fansim.geometry.config import load_blade_params, blade_params_from_dict
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat
from fansim.geometry import build_impeller, export_stl
from fansim.audit.direction import prove_direction, tip_lead_sign
from stacking_cut import prove_direction_stacking
WT = "/workspace/fansim/research/r7_wt"; OUT = sys.argv[1]; TMP = "/tmp/f_part.stl"

def population():
    P = [("builder46", "stock", lambda: load_blade_params(f"{WT}/config/problems/a12x25_reference.yaml"))]
    for row in csv.DictReader(open("/workspace/fansim/repo-r3/handoff/2026-10-09_to-qa-2/cfd_designs.csv")):
        if row["design_id"] == "stock": continue
        P.append(("builder46", row["design_id"], (lambda fl: lambda: blade_from_flat(json.loads(fl), Features()))(row["flat"])))
    src = "/workspace/fansim/repo-r3/handoff/2026-10-09_from-qa-2/screen_r3/cockpit_import/runs"
    for t in range(9601, 9631):
        f = glob.glob(f"{src}/*/cockpit_assess/design_{t}/design.json")[0]
        P.append(("builder46", str(t), (lambda f: lambda: blade_from_flat(json.load(open(f))["params"], Features()))(f)))
    rows = [json.loads(l) for l in open("/workspace/fansim/qa/r6_stress/inputs.jsonl")]
    for s in [f"S{i}" for i in range(1, 9)]:
        cand = sorted([r for r in rows if r["stratum"] == s and not r.get("sample_error")], key=lambda r: int(r["idx"]))[:2]
        for r in cand:
            P.append(("stress_sample", r["id"], (lambda r: lambda: blade_from_flat(r["flat"], Features(**(r.get("features") or {}))))(r)))
    for i in ("S3_0002", "S4_0005", "S4_0012"):
        r = next(x for x in rows if x["id"] == i)
        P.append(("targeted_k5fail", i, (lambda r: lambda: blade_from_flat(r["flat"], Features(**(r.get("features") or {}))))(r)))
    P.append(("reference", "a12x25_ref_stl", f"{WT}/validation/reference/a12x25_impeller.stl"))
    P.append(("reference", "fan01_rotor", f"{WT}/validation/reference/fan01/fan01_rotor.stl"))
    return P

def pr(p):
    return {"verdict": p.verdict, "omega": p.omega_sign, "pump": p.pump_sign, "chi": p.chirality, "n": p.n_sections, "note": p.note}

def mem_ok():
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable"): return int(line.split()[1]) / 1e6 > 3.0
    return True

done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
for group, pid, src in population():
    if pid in done: continue
    rec = {"group": group, "id": pid}
    try:
        t0 = time.time()
        if isinstance(src, str):
            mesh = trimesh.load(src, force="mesh")
        else:
            p = src(); rec["design_camber"] = max((s.max_camber for s in p.stations), key=abs)
            rec["n_blades_design"] = p.n_blades; rec["max_lean_deg"] = max(abs(s.lean_deg) for s in p.stations)
            for _ in range(60):
                if mem_ok(): break
                time.sleep(30)
            export_stl(build_impeller(dataclasses.replace(p, n_blades=2, blade_angles_deg=None)), TMP)
            mesh = trimesh.load(TMP, force="mesh")
        rec["build_s"] = round(time.time() - t0, 1)
        mir = mesh.copy(); mir.vertices[:, 1] *= -1; mir.invert()
        rec["cyl"] = pr(prove_direction(mesh)); rec["cyl_mirror"] = pr(prove_direction(mir))
        s, e = prove_direction_stacking(mesh); rec["stack"] = pr(s); rec["stack_extra"] = e
        s, _ = prove_direction_stacking(mir); rec["stack_mirror"] = pr(s)
        s, _ = prove_direction_stacking(mesh, mode="radial"); rec["radial"] = pr(s)
        s, _ = prove_direction_stacking(mir, mode="radial"); rec["radial_mirror"] = pr(s)
        if group == "reference": rec["tip_lead"] = tip_lead_sign(mesh)
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"[:300]
    with open(OUT, "a") as fh: fh.write(json.dumps(rec, default=float) + "\n")
    print(pid, rec.get("error") or (rec["cyl"]["verdict"], rec["stack"]["verdict"]), flush=True)
print("DONE")
