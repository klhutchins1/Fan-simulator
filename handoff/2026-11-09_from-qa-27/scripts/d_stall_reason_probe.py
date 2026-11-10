"""r27 D: behavioural — the Assess 'rejected' text for a stalled hose (pure function; no CFD)."""
import json, sys
from fansim.optimize.objectives import _operating_point_reason
from fansim.optimize.system_curve import SystemCurveError  # noqa
msg = _operating_point_reason(SystemCurveError("probe CFM must be positive"), free_signed=35.0, probe_signed=-22.0,
                              derate=0.88, p_free_pa=1.4, p_probe_pa=7.3, converged=True,
                              free_drift_pct=0.0, load_drift_pct=0.0)
out = {"assess_msg_as_shown": f"Design: rejected — {msg}", "has_stale_2x": "~2×" in msg or "~2x" in msg}
json.dump(out, open(sys.argv[1], "w"), indent=1, ensure_ascii=False); print(json.dumps(out, ensure_ascii=False))
