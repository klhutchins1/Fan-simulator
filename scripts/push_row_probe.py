"""Roadmap 27.3e: what does the flow card's mean push track? Read-only on the 27.3b/27.3d mesh-repeat cases.

    python scripts/push_row_probe.py runs/push_row_probe.json
"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(r"T:/Projects/Fan Simulator"); sys.path.insert(0, str(ROOT))
from fansim.cfd.cockpit_viz import load_case_mesh
from fansim.cfd.flow_report_case import samples_from_mesh, case_geometry
from fansim.cfd.spanwise import cylindrical_velocity
from fansim.physics.air import RHO_AMCA as RHO

cases = {f"stock/{m}": ROOT/"runs/stock_flow_mesh_repeats"/m for m in ("m1","m2","m3","m4","m5")}
for d in ("9604", "9610"):
    for m in ("m1","m2","m3","m4","m5"):
        cases[f"{d}/{m}"] = ROOT/"runs/design_flow_mesh_repeats"/d/m
out = {}
for name, case in cases.items():
    mesh = load_case_mesh(case)
    hub, tip, zf = case_geometry(case, mesh)
    s = samples_from_mesh(mesh)
    r, uz, uth = cylindrical_velocity(s.pts, s.u)
    ur2 = np.maximum(np.sum(s.u**2, axis=1) - uz**2 - uth**2, 0)
    z = s.pts[:, 2]; hdz = max(0.04*tip, 0.002)
    row = {"hub": hub, "tip": tip, "zmin": float(z.min()), "zmax": float(z.max()), "rmax": float(r.max())}
    for lab, zf_frac in [("in", -0.18), ("ex", 0.18), ("ex05", 0.5), ("ex10", 1.0), ("ex20", 2.0), ("in10", -1.0)]:
        z0 = zf + zf_frac*tip
        sel = (np.abs(z - z0) <= hdz) & (r >= hub) & (r <= tip)
        selall = (np.abs(z - z0) <= hdz) & (r <= tip*1.2)
        if not sel.any():
            row[lab] = None; continue
        w = s.w[sel]
        f = lambda a: float(np.sum(a[sel]*w)/np.sum(w))
        fm = lambda a: float(np.sum(a[sel]*w*np.maximum(uz[sel],0))/max(np.sum(w*np.maximum(uz[sel],0)),1e-12))
        wa = s.w[selall]
        row[lab] = {"p": RHO*f(s.p), "q_uz": RHO*f(0.5*uz**2), "q_uth": RHO*f(0.5*uth**2), "q_ur": RHO*f(0.5*ur2),
                    "p_massw": RHO*fm(s.p + 0.5*uz**2), "ptot_massw": RHO*fm(s.p + 0.5*np.sum(s.u**2, axis=1)),
                    "uz": f(uz), "p_wide": RHO*float(np.sum(s.p[selall]*wa)/np.sum(wa)), "n": int(sel.sum())}
    raw = json.loads((case/"_eval_result.json").read_text(encoding="utf-8"))
    row["cfm_load"] = raw.get("cfm_load"); row["eff"] = raw.get("efficiency")
    out[name] = row
    e, i = row["ex"], row["in"]
    print(name, "cfm", round(row["cfm_load"],2), "push", round(e["p"]+e["q_uz"]-i["p"]-i["q_uz"],2),
          "dp_static", round(e["p"]-i["p"],2), "q_uth_ex", round(e["q_uth"],2),
          "ex10 p", row["ex10"] and round(row["ex10"]["p"],2), "ex20 p", row["ex20"] and round(row["ex20"]["p"],2),
          "in10 p", row["in10"] and round(row["in10"]["p"],2), flush=True)
    del mesh, s
Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
