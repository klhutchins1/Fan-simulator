"""QA r16 hang: summarise optB.jsonl against the registered worth-it rule, plus report-only attribution of each failed
gate (pre-existing in the base design vs caused by the skirt). Usage: python optB_summary.py <optB.jsonl> <out.json>"""
import json, statistics as st, sys
from fansim.fan_spec import get_fan_spec, mount_min_hub_radius

spec = get_fan_spec("a12x25"); need_r = mount_min_hub_radius(spec)
R = [json.loads(l) for l in open(sys.argv[1])]; ok = [r for r in R if "error" not in r]
G = ["G1_mesh_ok", "G2_bed_ok", "G3_cup_ok", "G4_depth_ok", "G5_mass_ok", "G6_aero_ok"]
res = dict(n=len(R), n_errors=len(R) - len(ok), errors=[(r["id"], r["error"]) for r in R if "error" in r],
           rescued=sum(bool(r.get("rescued")) for r in ok), gate_pass={g: sum(bool(r.get(g)) for r in ok) for g in G},
           e_median=st.median(r["e"] for r in ok), e_max=max(r["e"] for r in ok),
           second_pass_needed=sum(len(r["passes"]) > 1 for r in ok),
           dm_auto_g20_median=st.median(r["dm_vs_auto_g20"] for r in ok), dm_auto_g20_max=max(r["dm_vs_auto_g20"] for r in ok),
           dm_auto_gsolid_median=st.median(r["dm_vs_auto_gsolid"] for r in ok), dm_auto_gsolid_max=max(r["dm_vs_auto_gsolid"] for r in ok),
           dm_base15_g20_median=st.median(r["dm_vs_base15_g20"] for r in ok), dm_base15_gsolid_median=st.median(r["dm_vs_base15_gsolid"] for r in ok),
           blade_vol_change_pct_median=st.median(100 * (r["blade_vol_ext"] - r["blade_vol_base"]) / r["blade_vol_base"] for r in ok),
           bem_change_max_abs_pct=max(abs(r["bem_free_change_pct"]) for r in ok),
           watertight=sum(bool(r.get("watertight")) for r in ok), one_body=sum(r.get("n_bodies") == 1 for r in ok),
           build_s_median=st.median(r["build_s"] for r in ok if "build_s" in r),
           mount_grew_after_skirt=sum(bool(r["mount_note"]) for r in ok))
# report-only attribution of failures
cause = {"G3_cup_ok": lambda r: r["hub_r"] < need_r - 1e-6, "G4_depth_ok": lambda r: r["depth_base15"] > spec.depth_mm[1] + 1e-9}
att = {}
for g, pre in cause.items():
    f = [r for r in ok if not r.get(g)]
    att[g] = dict(failed=len(f), pre_existing=sum(pre(r) for r in f), caused_by_skirt=sum(not pre(r) for r in f),
                  ids_caused=[r["id"] for r in f if not pre(r)])
res["failure_attribution"] = att
base_ok = [r for r in ok if r["hub_r"] >= need_r - 1e-6 and r["depth_base15"] <= spec.depth_mm[1] + 1e-9]
res["among_base_designs_that_fit_a12x25"] = dict(n=len(base_ok), rescued=sum(bool(r.get("rescued")) for r in base_ok))
worth = (res["rescued"] / len(R) >= 0.70) and (len(R) - sum(bool(r.get("G1_mesh_ok")) for r in ok) == 0) and res["dm_auto_g20_median"] <= 1.0
res["registered_verdict"] = "WORTH IT" if worth else "NOT WORTH IT (as registered)"
res["mount_min_hub_radius"] = need_r
json.dump(res, open(sys.argv[2], "w"), indent=1); print(json.dumps(res, indent=1))
