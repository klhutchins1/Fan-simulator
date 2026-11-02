"""QA r24 C (PREREG_R24 88c4e79): is K1 (loaded probe unconverged) visible? Pure-function calls only, no CFD.
Usage: repo-r24/.venv/bin/python c_k1_visibility.py <out.json>"""
import inspect, json, sys
import fansim; assert fansim.__file__.startswith("/workspace/fansim/repo-r24"), fansim.__file__
from fansim.cockpit.score_caption import stamp_score_extra, score_caption
from fansim.optimize import objectives as O
R = {}
for conv in (True, False):
    raw = {"converged": conv, "free": {"converged": True},
           "load": {"converged": conv, "flow_drift_pct": 6.0, "oscillation_pct": 16.0}}
    ex = stamp_score_extra({}, raw, load_pa=8.0, preset="case", refine_op=False)
    R[f"conv={conv}"] = {"score_caption": score_caption(ex), "stamped_keys": sorted(ex),
                         "converged_in_extra": "converged" in ex}
R["score_caption_identical"] = R["conv=True"]["score_caption"] == R["conv=False"]["score_caption"]
sig = inspect.signature(O._operating_point_reason)
kw = dict(free_signed=60.0, probe_signed=-3.0, derate=1.0, p_free_pa=0.0, p_probe_pa=8.0,
          free_drift_pct=0.4, load_drift_pct=6.0, free_osc_pct=1.0, load_osc_pct=16.0)
first = list(sig.parameters)[0]
for conv in (True, False):
    R[f"reject_reason_conv={conv}"] = O._operating_point_reason(**{first: "probe CFM must be positive"}, **kw, converged=conv)
R["reject_reason_mentions_unconverged"] = "UNCONVERGED" in R["reject_reason_conv=False"]
json.dump(R, open(sys.argv[1], "w"), indent=1, ensure_ascii=False); print(json.dumps(R, indent=1, ensure_ascii=False))
