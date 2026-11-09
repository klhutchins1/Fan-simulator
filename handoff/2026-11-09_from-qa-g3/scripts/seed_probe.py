"""ui-hunt-1: what Seed-from-duty does with the values the UI accepts (pure meanline call, as fan_editor.seed_from_duty does).
Usage: python seed_probe.py <out.json>"""
import json, math, sys
from fansim.optimize.meanline import DutyPoint, seed_from_duty, station_magnitudes
R = {}
for tag, (cfm, dp, rpm) in {"default": (60, 15, 2000), "neg_cfm": (-5, 15, 2000), "neg_pa": (60, -5, 2000), "neg_rpm": (60, 15, -5),
                            "zero_rpm": (60, 15, 0), "huge_cfm": (1e9, 15, 2000), "huge_rpm": (60, 15, 1e9)}.items():
    try:
        s = seed_from_duty(DutyPoint(cfm=float(cfm), dp_pa=float(dp), rpm=float(rpm)), hub_radius_mm=21.5, tip_radius_mm=54.5, n_blades=9,
                           chord_root_mm=18.7, chord_mid_mm=25.4, chord_tip_mm=33.7, vortex="free")
        m = station_magnitudes(s)
        R[tag] = {"ok": True, "mags": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()},
                  "nonfinite": [k for k, v in m.items() if isinstance(v, float) and not math.isfinite(v)]}
    except Exception as e:
        R[tag] = {"ok": False, "err": f"{type(e).__name__}: {e}"[:200]}
for v in ("", "-5", "1e9", "100"):
    try: R[f"sweep_steps_expr[{v!r}]"] = max(2, int(v))
    except Exception as e: R[f"sweep_steps_expr[{v!r}]"] = f"{type(e).__name__}: {e}"
    try: t = int(float(v))
    except (TypeError, ValueError): t = 8
    R[f"opt_trials_expr[{v!r}]"] = max(2, min(40, t))
json.dump(R, open(sys.argv[1], "w"), indent=1); print(json.dumps(R, indent=1)[:4000])
