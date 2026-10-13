"""QA r9 Task D step 2 (PREREG_R9 a0260c0): both readers on every prepared part and its y-mirror, scored with
the radial-led rule against the truth frozen in step 1. Readers: prove_direction (cylinder) and round-8
stacking_cut.prove_direction_stacking(mode="radial"), unchanged (copied here verbatim from round 8).
Usage: python run_readers.py <truth.json> <out.json>"""
import json, sys, time, os
import trimesh
sys.path.insert(0, os.path.dirname(__file__))
from fansim.audit.direction import prove_direction
from stacking_cut import prove_direction_stacking
T = json.load(open(sys.argv[1])); PREP = "/tmp/qa9_ext/prep"
def pr(p): return {"verdict": p.verdict, "omega": p.omega_sign, "pump": p.pump_sign, "chi": p.chirality, "n": p.n_sections, "note": (p.note or "")[:160]}
def rule(cy, ra):
    if ra["verdict"] != "CONCLUSIVE": return "ASK", None
    if cy["verdict"] == "CONCLUSIVE" and (cy["omega"], cy["pump"], cy["chi"]) != (ra["omega"], ra["pump"], ra["chi"]): return "ASK", None
    return "ACCEPT", [ra["omega"], ra["pump"], ra["chi"]]
out = {}
for name, t in T.items():
    t0 = time.monotonic(); m = trimesh.load(f"{PREP}/{name}.stl", force="mesh")
    mir = m.copy(); mir.vertices[:, 1] *= -1; mir.invert()
    truth = t["truth"]; rec = {"truth": truth}
    for tag, mesh, tr in (("orig", m, truth), ("mirror", mir, [-truth[0], truth[1], -truth[2]] if truth else None)):
        try:
            cy = pr(prove_direction(mesh)); ra = pr(prove_direction_stacking(mesh, mode="radial")[0])
        except Exception as exc:  # unreadable mesh counts as ASK
            cy = ra = {"verdict": "ERROR", "note": f"{type(exc).__name__}: {exc}"[:160], "omega": None, "pump": None, "chi": None}
        dec, val = rule(cy, ra)
        rec[tag] = {"cyl": cy, "radial": ra, "decision": dec, "value": val,
                    "score": None if tr is None else ("ASK" if dec == "ASK" else ("OK" if val == tr else "WRONG")),
                    "cyl_alone": None if tr is None or cy["verdict"] != "CONCLUSIVE" else ([cy["omega"], cy["pump"], cy["chi"]] == tr),
                    "radial_alone": None if tr is None or ra["verdict"] != "CONCLUSIVE" else ([ra["omega"], ra["pump"], ra["chi"]] == tr)}
    rec["mono_s"] = round(time.monotonic() - t0, 1); out[name] = rec
    print(name, truth, rec["orig"]["decision"], rec["orig"]["score"], rec["mirror"]["score"], rec["orig"]["cyl"]["verdict"][:4], rec["orig"]["radial"]["verdict"][:4], rec["mono_s"], flush=True)
json.dump(out, open(sys.argv[2], "w"), indent=1)
