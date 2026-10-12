"""Score Task B against PREREG_R8 (6b0aedf) R1-R6 (+R6b)."""
import json, sys
from collections import Counter
R = [json.loads(l) for l in open(sys.argv[1])]
def exp(r):
    if r["id"] == "fan01_rotor": return (1, 1, 1)
    if r["id"] == "a12x25_ref_stl": tl = r.get("tip_lead"); return (tl, -tl, -1) if tl else None
    return (1, -1, -1) if r["design_camber"] >= 0 else (-1, 1, -1)
def mexp(e): return (-e[0], e[1], -e[2])
def cls(p, e):
    if p["verdict"] != "CONCLUSIVE": return "INC"
    return "OK" if (p["omega"], p["pump"], p["chi"]) == tuple(e) else "WRONG"
def comb(a, b):
    if a["verdict"] == b["verdict"] == "CONCLUSIVE" and (a["omega"], a["pump"], a["chi"]) == (b["omega"], b["pump"], b["chi"]): return a
    return {"verdict": "ASK"}
def cell(r):
    if r["cell_sel"] in ("reference", "flipped", "extra"): return r["cell_sel"]
    c = abs(r["design_camber"]); lt = r["lean_tip"]
    return "S3cell" if 0.02 <= c < 0.04 and lt >= 30 else "flatlean" if c < 0.02 and lt >= 20 else "ordinary" if c >= 0.04 else "other"
def refuse(cy, ra, camber, gate=False):
    for p in (cy, ra):
        if p["verdict"] == "CONCLUSIVE" and p["chi"] != -1: return True
    if camber is None or (gate and abs(camber) < 0.02): return False
    ex = (1, -1) if camber > 0 else (-1, 1)
    return all(p["verdict"] == "CONCLUSIVE" and (p["omega"], p["pump"]) != ex for p in (cy, ra))
rows = []
for r in R:
    if "error" in r: rows.append({"id": r["id"], "error": r["error"]}); continue
    e = exp(r); x = {"id": r["id"], "sel": r["cell_sel"], "cell": cell(r), "camber": r.get("design_camber"), "lean": r.get("lean_tip"),
                     "featured": r.get("featured")}
    for k in ("cyl", "radial"):
        x[k] = cls(r[k], e); x[k + "_m"] = cls(r[k + "_mirror"], mexp(e))
        x[k + "_raw"] = (r[k]["verdict"][:4], r[k]["omega"], r[k]["pump"], r[k]["chi"])
    c, cm = comb(r["cyl"], r["radial"]), comb(r["cyl_mirror"], r["radial_mirror"])
    x["comb"] = "ASK" if c["verdict"] == "ASK" else cls(c, e); x["comb_m"] = "ASK" if cm["verdict"] == "ASK" else cls(cm, mexp(e))
    x["r3_ok"] = (r["radial"]["verdict"] != "CONCLUSIVE") or (r["radial_mirror"]["verdict"] == "CONCLUSIVE" and r["radial_mirror"]["chi"] == -r["radial"]["chi"])
    dc = r.get("design_camber")
    if r["cell_sel"] != "reference":
        x["ref"] = refuse(r["cyl"], r["radial"], dc); x["ref_m"] = refuse(r["cyl_mirror"], r["radial_mirror"], dc)
        x["refb"] = refuse(r["cyl"], r["radial"], dc, True); x["refb_m"] = refuse(r["cyl_mirror"], r["radial_mirror"], dc, True)
    rows.append(x)
ok = [x for x in rows if "error" not in x]
O = {"n": len(R), "errors": [x for x in rows if "error" in x], "cells": dict(Counter(x["cell"] for x in ok)),
     "cell_moves": [(x["id"], x["sel"], x["cell"]) for x in ok if x["sel"] not in ("reference", "flipped", "extra") and x["sel"] != x["cell"]]}
for k in ("cyl", "radial", "comb"):
    O[k] = dict(Counter(x[k] for x in ok)); O[k + "_mirror"] = dict(Counter(x[k + "_m"] for x in ok))
    O[k + "_by_cell"] = {c: dict(Counter(x[k] for x in ok if x["cell"] == c)) for c in O["cells"]}
cam = [x for x in ok if x["cell"] != "reference" and abs(x["camber"]) >= 0.02]
O["R1_wrong"] = [x["id"] for x in ok if x["radial"] == "WRONG" or x["radial_m"] == "WRONG"]
O["R2"] = f'{sum(x["radial"] == "OK" for x in cam)}/{len(cam)}'
O["R3_fail"] = [x["id"] for x in ok if not x["r3_ok"]]
O["R4"] = {x["id"]: x["radial"] for x in ok if x["cell"] == "reference"}
O["R5_wrong"] = [x["id"] for x in ok if x["comb"] == "WRONG" or x["comb_m"] == "WRONG"]
O["R5_read"] = f'{sum(x["comb"] == "OK" for x in cam)}/{len(cam)}'
b = [x for x in ok if x["cell"] != "reference"]
for tag, kk in (("R6", "ref"), ("R6b", "refb")):
    O[tag + "_refused_S3cell_or_extra"] = [x["id"] for x in b if x["cell"] in ("S3cell", "extra") and x[kk]]
    O[tag + "_mirror_not_refused"] = [x["id"] for x in b if not x[kk + "_m"]]
    O[tag + "_flipped_not_refused"] = [x["id"] for x in b if x["cell"] == "flipped" and not x[kk]]
    O[tag + "_other_refused"] = [(x["id"], x["cell"]) for x in b if x[kk] and x["cell"] not in ("S3cell", "extra", "flipped")]
O["not_ok_rows"] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items()} for x in ok
                    if x["cyl"] != "OK" or x["radial"] != "OK" or x["comb"] != "OK"]
print(json.dumps(O, indent=1, default=str))
