"""QA r18 A: gates + reference CSV. Usage: python a_finalise.py <a_built.jsonl> <a_selection.json> <a_diag.json> <out.csv> <summary.json>"""
import csv, json, sys
R = [json.loads(l) for l in open(sys.argv[1])]; S = json.load(open(sys.argv[2])); Dg = {d["id"]: d for d in json.load(open(sys.argv[3]))}
by = {(r["id"], r["mode"]): r for r in R}
g = dict(A_run=all((s["id"], "x") in by and "error" not in by[(s["id"], "x")] for s in S))
g["A_self_vert_max"] = max(abs(by[(s["id"], "x")]["z_min"] - by[(s["id"], "x")]["z_vert"]) for s in S)
g["A_self_mesh_max"] = max(abs(by[(s["id"], "x")]["z_min"] - by[(s["id"], "x")]["z_mesh"]) for s in S)
g["A_self"] = g["A_self_vert_max"] <= 0.005 and g["A_self_mesh_max"] <= 0.02
g["A_rep_max"] = max(abs(by[(i, "x")]["s"] - by[(i, "x_rep")]["s"]) for i in ("S2_0269", "S5_0207", "G_0502"))
g["A_rep"] = g["A_rep_max"] <= 1e-4
g["A_repro_S2_0269_auto"] = by[("S2_0269", "auto")]["h"]; g["A_repro"] = abs(g["A_repro_S2_0269_auto"] - 2.2524) <= 0.05
g["clip_ok_all"] = all(r.get("clip_ok") for r in R if "error" not in r)
rows = []
for s in S:
    x = by[(s["id"], "x")]; a = by.get((s["id"], "auto"), {}); m = by.get((s["id"], "mount"), {})
    m1 = s["r17_h_bx"]  # None: r17 did not build it (designed hang 0 at the export hub)
    rows.append(dict(id=s["id"], features=int(s["features"]), hub_growth_below_mm=round(x["dh"], 4), z_hub_face_mm=round(x["z_face"], 4),
                     z_blade_min_mm=round(x["z_min"], 4), signed_hang_mm=round(x["s"], 4), built_hang_ref_mm=round(x["h"], 4),
                     m3_vertex_hang_mm=round(x["h_vert"], 4), m3_mesh_hang_mm=round(x["h_mesh"], 4),
                     m1_section_points_r17_mm="" if m1 is None else round(m1, 4), m1_minus_m2_mm="" if m1 is None else round(m1 - x["h"], 4),
                     designed_hang_export_hub_mm=round(x["h_designed"], 4), refuse_stage2=int(x["h"] > 2.0),
                     supp_auto_hub_hang_mm=round(a["h"], 4) if a else "", supp_mount_hub_params_hang_mm=round(m["h"], 4) if m else "",
                     supp_mount_growth_top_mm=round(m.get("dh_top", 0.0), 4) if m else "",
                     note=("lowest point at tip; r17 section method includes the untrimmed over-radius wire" if s["id"] in Dg and Dg[s["id"]]["M1_rf"] == 1.0
                           else "features raise loft span sections; lowest section missed at n_span" if s["features"] and m1 is not None and abs(m1 - x["h"]) > 0.05 else "")))
w = csv.DictWriter(open(sys.argv[4], "w", newline=""), fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
g["m1_m2_max_abs"] = max(abs(r["m1_minus_m2_mm"]) for r in rows if r["m1_minus_m2_mm"] != "")
json.dump(dict(gates=g, rows=rows), open(sys.argv[5], "w"), indent=1)
print(json.dumps(g, indent=0))
for r in rows: print(r["id"], r["features"], r["built_hang_ref_mm"], r["m1_minus_m2_mm"], r["refuse_stage2"], r["supp_auto_hub_hang_mm"], r["supp_mount_hub_params_hang_mm"], r["supp_mount_growth_top_mm"])
