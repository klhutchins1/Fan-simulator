"""QA r26 G2 follow-up (PREREG_R26_G2 414177a): behavioural probe of the noise row, design-list label and print sheet
on master 83681c2. Pure functions only; no CFD, no UI. Usage: python g2_probe.py <repo> <out.json>"""
import dataclasses, json, re, sys
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
import fansim; assert fansim.__file__.startswith(str(repo)), fansim.__file__
from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd import flow_verdicts as fv
from fansim.cockpit.data import design_dropdown_items
G2 = "Scales with tip speed and airflow only; this is not a comparison of how quiet the design is."
STOCK = FlowMetrics(0.06, False, [2.0, 4.0, 6.0, 8.0, 6.0], 0.20, 0.05, 0.80, 60.0, 2.5, mean_dp0_pa=6.0)
m = lambda **k: dataclasses.replace(STOCK, **k)
R = {"NOISE_JUDGED": fv.NOISE_JUDGED, "noise_rows": {}}
cases = {"hint_more_cfm_+5dB": (m(noise_hint_db=80.4), m(noise_hint_db=75.4)),
         "hint_less_cfm_-5dB": (m(noise_hint_db=70.4), m(noise_hint_db=75.4)),
         "hint_equal": (m(noise_hint_db=75.4), m(noise_hint_db=75.4)),
         "hint_+30dB": (m(noise_hint_db=105.4), m(noise_hint_db=75.4)),
         "hint_no_stock": (m(noise_hint_db=80.4), None),
         "swl_only_+10dB": (m(noise_swl_db=50.0), m(noise_swl_db=40.0)),
         "swl_only_-10dB": (m(noise_swl_db=30.0), m(noise_swl_db=40.0))}
ok1 = ok2 = True
for k, (d, s) in cases.items():
    rows = fv.judge(d, s); r = rows[4]
    judged = r.status in ("ok", "warn", "bad") or bool(r.better) or "⚠" in r.text or "✓" in r.text
    louder = bool(re.search(r"\b(louder|quieter)\b", r.text))
    ov = fv.overall_line(rows, compared=s is not None)
    R["noise_rows"][k] = {"status": r.status, "better": r.better, "expert_only": r.expert_only, "judged": judged,
                          "louder_quieter_word": louder, "has_G2_text": G2 in r.text, "text": r.text,
                          "noise_in_overall_line": "noise" in ov.lower()}
    ok1 &= not judged and "noise" not in ov.lower()
    if k.startswith("hint"): ok2 &= G2 in r.text and not louder and r.expert_only
R["K1_never_judged_all_cases"] = ok1; R["K2_hint_text_and_expert_only_flag"] = ok2
it = design_dropdown_items([{"trial": 3, "objectives": {"cfm_free": 50.0, "swl_dba": 44.2}}])[0]["title"]
R["K4_design_list_title"] = it; R["K4_design_list_ok"] = "SWL est. 44.2" in it and "dBA" not in it and "dB(A)" not in it
from fansim.geometry.blade import BladeParams
from fansim.geometry.export import WatertightReport
from fansim.manufacturability.print_export import print_readme, recommend_print_settings
rep = WatertightReport(watertight=True, n_vertices=8, n_faces=12, volume_mm3=1000.0, n_bodies=1, bounds_mm=((-50, -50, 0), (50, 50, 20)))
md = print_readme("t", BladeParams(), "PETG", rep, {"balanced": True, "even_spacing": True, "normalized_unbalance": 0.0},
                  recommend_print_settings("PETG"), None, {"cfm_free": 50.0, "cfm_load": 30.0, "efficiency": 25.0, "noise_swl": 44.2})
line = [l for l in md.splitlines() if "Predicted performance" in l]
R["K4_print_sheet_line"] = line; bare = [l for l in md.splitlines() if re.search(r"dB\(A\)|dBA", l) and not re.search(r"not dB\(A\)|published|measured|estimate|not validated", l, re.I)]
R["K4_print_sheet_bare_dBA_lines"] = bare
R["K4_print_sheet_ok"] = bool(line) and "noise estimate 44.2 (not dB(A); not validated)" in line[0] and "noise_swl 44.2" not in md and not bare
json.dump(R, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in R.items() if k != "noise_rows"}, indent=1, ensure_ascii=False))
print({k: (v["status"], v["better"], v["expert_only"]) for k, v in R["noise_rows"].items()})
