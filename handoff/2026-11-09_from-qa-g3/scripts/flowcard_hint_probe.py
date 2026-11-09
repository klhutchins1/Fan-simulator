"""ui-hunt-1: is the Expert noise-hint row emitted by build_report when the run has a hint but no turbulence SWL? I/O seams faked (r22 a_flowcard pattern)."""
import json, sys
import fansim.cockpit.fan_flow_report as F
from fansim.cfd.flow_report import FlowMetrics
def fm(swl=None, hint=None):
    return FlowMetrics(backflow_frac=0.03, net_reversed=False, band_dp0_pa=[8, 10, 11, 13, 17], swirl_frac=0.58, dead_frac=0.03,
                       tip_band_uz_ratio=0.93, noise_swl_db=swl, mean_uz_exit=5.0, mean_dp0_pa=12.0, noise_hint_db=hint)
R = {}
for name, (d, s) in {"hint_and_swl": (fm(10.0, 30.0), fm(5.0, 28.0)), "hint_only_no_swl": (fm(None, 30.0), fm(None, 28.0))}.items():
    F.load_or_compute_metrics = lambda case, d=d: d; F._attach_noise_hint = lambda m, case: m; F.test_settings = lambda case: {}
    F.first_mismatch = lambda a, b: None; F._stock_pack = lambda ref, s=s: (s, None, {}); F._pictures_cached = lambda *a, **k: {}
    out = F.build_report("/tmp/qa_fake_case", "/tmp/qa_fake_ref")
    R[name] = {"row_keys": [r["key"] for r in out["flow_rows"]], "noise_row": [r["text"][:90] for r in out["flow_rows"] if r["key"] == "noise"], "msg": out["flow_msg"]}
json.dump(R, open(sys.argv[1], "w"), indent=1); print(json.dumps(R, indent=1))
