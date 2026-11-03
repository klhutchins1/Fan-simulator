"""QA r24 (reused r22) A QA-40 re-test (PREREG_R22 715891f; r14 a4_flowcard.py, path assert changed): flow card in Simple mode. build_report with only its I/O seams faked, 4 scenarios.
Visible in Simple = in flow_rows and expert_only False (fan_tab_ui v_show). Usage: python a4_flowcard.py <out.json>"""
import json, sys
import fansim; assert fansim.__file__.startswith(__import__("os").environ["QA_REPO"]), fansim.__file__
import fansim.cockpit.fan_flow_report as F
from fansim.cfd.flow_report import FlowMetrics
def fm(swl=None, hint=None, push=12.0, back=0.03):
    return FlowMetrics(backflow_frac=back, net_reversed=False, band_dp0_pa=[8, 10, 11, 13, 17], swirl_frac=0.58, dead_frac=0.03,
                       tip_band_uz_ratio=0.93, noise_swl_db=swl, mean_uz_exit=5.0, mean_dp0_pa=push, noise_hint_db=hint)
SC = {"s1_compared_hint": (fm(10.0, 30.0, 14.0), fm(5.0, 28.0), True),
      "s2_compared_swl_only": (fm(10.0, None, 14.0), fm(5.0, None), True),
      "s3_design_swl_no_stock": (fm(10.0, None, 14.0), None, False),
      "s4_no_swl": (fm(None, None, 14.0), fm(None, None), True)}
R = {}
for name, (d, s, has_ref) in SC.items():
    F.load_or_compute_metrics = lambda case, d=d: d
    F._attach_noise_hint = lambda m, case: m
    F.test_settings = lambda case: {}
    F.first_mismatch = lambda a, b: None
    F._stock_pack = lambda ref, s=s: (s, None, {})
    F._pictures_cached = lambda *a, **k: {}
    out = F.build_report("/tmp/qa22_fake_case", "/tmp/qa22_fake_ref" if has_ref else None)
    rows = out["flow_rows"]; simple = [r for r in rows if not r["expert_only"]]
    noise_vis = [r for r in simple if r["key"] == "noise"]
    ov = out["flow_overall"].lower(); words = [w for w in ("noise", "loud", "quiet") if w in ov]
    R[name] = {"rows": [(r["key"], r["status"], r["expert_only"], r["text"][:120]) for r in rows], "overall": out["flow_overall"],
               "msg": out["flow_msg"], "noise_visible_in_simple": [r["text"] for r in noise_vis], "overall_noise_words": words,
               "PASS": not noise_vis and not words}
R["A4_PASS"] = all(v["PASS"] for v in R.values() if isinstance(v, dict))
json.dump(R, open(sys.argv[1], "w"), indent=1); print(json.dumps(R, indent=1))
