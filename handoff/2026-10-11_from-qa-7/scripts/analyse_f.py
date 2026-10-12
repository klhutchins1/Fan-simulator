"""Score Task F results against the pre-registered F1-F6 (PREREG_R7.md)."""
import json, sys
R = [json.loads(l) for l in open(sys.argv[1])]
def expected(r):
    if r["id"] == "fan01_rotor": return (1, 1, 1)
    if r["id"] == "a12x25_ref_stl": tl = r.get("tip_lead"); return (tl, -tl, -1) if tl else None
    return (1, -1, -1)
def cls(p, exp):
    if p["verdict"] != "CONCLUSIVE": return "INC"
    return "OK" if (p["omega"], p["pump"], p["chi"]) == tuple(exp) else "WRONG"
def mexp(e): return (-e[0], e[1], -e[2])
out = {"n": len(R), "errors": [r["id"] for r in R if "error" in r]}
rows = []
for r in R:
    if "error" in r: continue
    e = expected(r)
    row = {"id": r["id"], "group": r["group"], "camber": r.get("design_camber"), "lean": r.get("max_lean_deg"), "exp": e}
    for k in ("cyl", "stack", "radial"):
        row[k] = cls(r[k], e) if e else "noexp"; row[k + "_m"] = cls(r[k + "_mirror"], mexp(e)) if e else "noexp"
    row["stack_raw"] = (r["stack"]["verdict"][:4], r["stack"]["omega"], r["stack"]["pump"], r["stack"]["chi"])
    row["cyl_raw"] = (r["cyl"]["verdict"][:4], r["cyl"]["omega"], r["cyl"]["pump"], r["cyl"]["chi"])
    row["tilt"] = r["stack_extra"].get("max_tilt_deg"); row["med_cam_stack"] = r["stack_extra"].get("median_camber")
    rows.append(row)
def count(key, sel=lambda x: True):
    from collections import Counter
    return dict(Counter(x[key] for x in rows if sel(x)))
for k in ("cyl", "stack", "radial"):
    out[k] = count(k); out[k + "_mirror"] = count(k + "_m")
hic = lambda x: x["camber"] is not None and abs(x["camber"]) >= 0.02
out["F1_wrong_stack"] = [x["id"] for x in rows if x["stack"] == "WRONG"]
n_hi = sum(hic(x) for x in rows); ok_hi = sum(hic(x) and x["stack"] == "OK" for x in rows)
out["F2"] = f"{ok_hi}/{n_hi} = {ok_hi / max(n_hi, 1):.3f}"
ctl = [x for x in rows if x["id"] in ("9605", "9606", "9620", "9630")]
out["F3"] = {x["id"]: x["stack"] for x in ctl}
out["F4_fail"] = [x["id"] for x in rows if x["stack"] == "OK" and x["stack_m"] != "OK"] + \
                 [x["id"] for x in rows if x["stack"] == "WRONG"]
out["F5"] = {x["id"]: (x["stack"], x["stack_raw"], "cyl", x["cyl_raw"]) for x in rows if x["group"] == "reference"}
cw = [x for x in rows if x["cyl"] == "WRONG"]
out["F6_population"] = [x["id"] for x in cw]; out["F6_stack_wrong"] = [x["id"] for x in cw if x["stack"] == "WRONG"]
out["F6_stack_result"] = {x["id"]: x["stack"] for x in cw}
out["rows_not_ok"] = [(x["id"], x["group"], round(x["camber"], 4) if x["camber"] is not None else None, x["lean"] and round(x["lean"], 1),
                       "cyl", x["cyl"], x["cyl_raw"], "stack", x["stack"], x["stack_raw"], "m", x["stack_m"], "rad", x["radial"], "tilt", x["tilt"])
                      for x in rows if x["stack"] != "OK" or x["cyl"] != "OK" or x["stack_m"] != "OK"]
print(json.dumps(out, indent=1, default=str))
