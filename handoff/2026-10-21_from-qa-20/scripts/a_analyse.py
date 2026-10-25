"""QA r20 A analysis (PREREG_R20 2c4380d): gates A1-A4 against docs/qa/r18/r18-A-built-hang-reference.csv."""
import csv, json, sys
R = {}
for l in open(sys.argv[1]):
    r = json.loads(l); R[(r["id"], r["mode"])] = r
ref = {r["id"]: r for r in csv.DictReader(l for l in open(sys.argv[2]) if not l.startswith('"#'))}
rows, g = [], {"errors": [k for k, v in R.items() if "error" in v]}
F = 1.75 / 2.0
for did, rr in ref.items():
    m, e = R[(did, "mine")], R[(did, "e2e")]
    href = float(rr["built_hang_ref_mm"]); feat = rr["features"] == "1"
    alt = R.get((did, "json" if feat else "r16"))
    s1_exp = 1.75 * m["h_designed"] > 2.0; s2_exp = m["h_built"] > 2.0
    top_ok = abs(m["z_mount"][1] - m["z_auto"][1]) < 1e-6
    row = dict(id=did, features=int(feat), r18_built_hang_mm=href, r20_built_hang_mm=round(m["h_built"], 4),
               diff_mm=round(m["h_built"] - href, 6), reuse_equal=abs(m["h_built"] - m["h_built_reuse"]) < 1e-12,
               alt_recipe=("json" if feat else "r16"), alt_built_hang_mm=round(alt["h_built"], 4) if alt and "h_built" in alt else None,
               alt_minus_r18_mm=round(alt["h_built"] - href, 6) if alt and "h_built" in alt else None,
               json_fields_differ=(alt or {}).get("fields_differ_from_r18_build") if feat else "",
               hub_height_mm=round(m["z_mount"][1] - m["z_mount"][0], 6), top_face_fixed=top_ok,
               z_face_mm=round(m["z_mount"][0], 4), z_face_r18_mm=float(rr["z_hub_face_mm"]),
               designed_hang_mm=round(m["h_designed"], 4), printed_est_stage1_mm=round(1.75 * m["h_designed"], 4),
               stage1=("refuse" if m["stage1"].startswith("refused") else "pass"), stage1_expected=("refuse" if s1_exp else "pass"),
               stage2=("refuse" if m["stage2"].startswith("refused") else "pass"), stage2_expected=("refuse" if s2_exp else "pass"),
               e2e_build_impeller_parts=("refused" if e["e2e"].startswith("refused") else "built"), e2e_msg=e["e2e"][:90],
               export_z_face_mm=round(m["z_export"][0], 6), export_z_top_mm=round(m["z_export"][1], 6),
               export_dz_face=round(m["z_export"][0] - m["z_mount"][0], 9), export_dz_top=round(m["z_export"][1] - m["z_mount"][1], 9),
               export_built_hang_mm=round(m["h_built_export"], 4), export_minus_eval_hang_mm=round(m["h_built_export"] - m["h_built"], 6),
               export_section_wrap=m["section_wrap_export"], export_hub_radius_change=m["hub_radius"][0] != m["hub_radius"][1],
               export_changes=";".join(f"{c[0]} {c[1]:.4f}->{c[2]:.4f}" for c in m["export_changes"]))
    rows.append(row)
R18 = {json.loads(l)["id"]: json.loads(l)["h"] for l in open("/workspace/fansim/qa/r18/data/a_built.jsonl") if json.loads(l)["mode"] == "x"}
g["A1_json_reproduces_1e-6"] = all(abs(R[(r["id"], "json")]["h_built"] - R18[r["id"]]) <= 1e-6 and not r["json_fields_differ"] for r in rows if r["features"])
g["A2_max_abs_vs_r18_unrounded"] = max(abs(R[(r["id"], m)]["h_built"] - R18[r["id"]]) for r in rows for m in ("mine", "json" if r["features"] else "r16"))
g["A1_json_max_abs_vs_r20_mine"] = max(abs(R[(r["id"], "json")]["h_built"] - R[(r["id"], "mine")]["h_built"]) for r in rows if r["features"])
g["A2_all_within_0.05"] = all(abs(r["diff_mm"]) <= 0.05 for r in rows)
g["A2_max_abs_diff_mm"] = max(abs(r["diff_mm"]) for r in rows)
g["A2_r16_max_abs_vs_r18"] = max(abs(r["alt_minus_r18_mm"]) for r in rows if not r["features"])
g["A2_hub_ge15mm_top_fixed"] = all(r["hub_height_mm"] >= 15 - 1e-6 and r["top_face_fixed"] for r in rows)  # hubs already >= 15 mm are not grown
g["A2_z_face_vs_r18_max"] = max(abs(r["z_face_mm"] - r["z_face_r18_mm"]) for r in rows)
g["A3_stage1_as_expected"] = all(r["stage1"] == r["stage1_expected"] for r in rows)
g["A3_stage2_as_expected"] = all(r["stage2"] == r["stage2_expected"] for r in rows)
g["A3_no_overhang_built"] = all(not (r["r20_built_hang_mm"] > 2 and r["e2e_build_impeller_parts"] == "built") for r in rows)
g["A3_counts"] = {"stage1_refuse": sum(r["stage1"] == "refuse" for r in rows), "stage2_refuse": sum(r["stage2"] == "refuse" for r in rows),
                  "e2e_refused": sum(r["e2e_build_impeller_parts"] == "refused" for r in rows)}
g["A4_z_agree_1e-6"] = all(abs(r["export_dz_face"]) < 1e-6 and abs(r["export_dz_top"]) < 1e-6 for r in rows)
g["A4_hang_agree_0.01"] = all(abs(r["export_minus_eval_hang_mm"]) <= 0.01 for r in rows)
g["A4_any_hub_radius_change"] = [r["id"] for r in rows if r["export_hub_radius_change"]]
json.dump({"gates": g, "rows": rows}, open(sys.argv[3], "w"), indent=1)
with open(sys.argv[4], "w", newline="") as f:
    f.write('"# grok QA r20 A (prereg 2c4380d), master 027ebcb: blade_hang_built_mm at the mount_hub_params hub (R1.7) vs grok r18 A reference; two-stage refusal (QA-43); Export-flat hub vs evaluate hub (QA-44). mm."\n')
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(json.dumps(g, indent=1))
for r in rows:
    print(r["id"], r["r20_built_hang_mm"], r["diff_mm"], r["alt_minus_r18_mm"], r["stage1"], r["stage2"], r["e2e_build_impeller_parts"], r["export_dz_face"], r["export_minus_eval_hang_mm"], r["export_changes"][:80])
