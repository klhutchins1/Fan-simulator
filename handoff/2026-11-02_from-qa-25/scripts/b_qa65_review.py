"""QA r25 B (PREREG_R25 b7e7574): review the QA-65 patch adopted on master 9d0118f.
Pure-function calls on a SCRATCH copy of master+patch (repo-r25 untouched). No CFD.
Usage: PYTHONPATH=<scratch> repo-r25/.venv/bin/python b_qa65_review.py <scratch> <out.json>"""
import json, sys, inspect
scratch = sys.argv[1]
import fansim; assert fansim.__file__.startswith(scratch), fansim.__file__
from fansim.cockpit.score_caption import stamp_score_extra, score_caption
from fansim.optimize import objectives as O
W = "did not settle"
R = {}
base = {"free": {"converged": True}, "load": {"flow_drift_pct": 6.0, "oscillation_pct": 16.0}}
cases = {"conv=True": True, "conv=False": False, "conv=None": None, "conv=missing": "MISSING"}
for name, c in cases.items():
    raw = dict(base)
    if c != "MISSING":
        raw["converged"] = c
    ex = stamp_score_extra({}, raw, load_pa=8.0, preset="case", refine_op=False)
    cap = score_caption(ex)
    R[name] = {"caption": cap, "warn": W in cap, "converged_in_extra": ex.get("converged", "absent")}
# old design.json extra with no key, and string "False" (json round trip keeps bool, but check robustness)
R["old_extra_no_key_warn"] = W in score_caption({"preset": "case", "load_pa": 8.0})
R["extra_converged_str_False_warn"] = W in score_caption({"converged": "False"})
# re-assess overwrite: stale False then converged True
ex = {"converged": False}; stamp_score_extra(ex, dict(base, converged=True), load_pa=8.0, preset="case", refine_op=False)
R["reassess_False_then_True_warn"] = W in score_caption(ex)
# reject message unchanged vs r24 for same inputs
sig = inspect.signature(O._operating_point_reason); first = list(sig.parameters)[0]
kw = dict(free_signed=60.0, probe_signed=-3.0, derate=1.0, p_free_pa=0.0, p_probe_pa=8.0,
          free_drift_pct=0.4, load_drift_pct=6.0, free_osc_pct=1.0, load_osc_pct=16.0)
R["reject_reason_conv=False"] = O._operating_point_reason(**{first: "probe CFM must be positive"}, **kw, converged=False)
# r24 output; in the repo it is handoff/2026-11-01_from-qa-24/data/c_k1.json
r24 = json.load(open("/workspace/fansim/qa_r24/data/c_k1.json"))
R["reject_reason_same_as_r24"] = R["reject_reason_conv=False"] == r24["reject_reason_conv=False"]
R["shows_only_when_False"] = R["conv=False"]["warn"] and not any(R[k]["warn"] for k in ("conv=True", "conv=None", "conv=missing")) \
    and not R["old_extra_no_key_warn"] and not R["extra_converged_str_False_warn"] and not R["reassess_False_then_True_warn"]
json.dump(R, open(sys.argv[2], "w"), indent=1, ensure_ascii=False); print(json.dumps(R, indent=1, ensure_ascii=False))
