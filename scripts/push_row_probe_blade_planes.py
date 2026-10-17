"""Roadmap 27.3e probe 2: push with planes outside each design's own blade row (LE - g, TE + g), g = 0.1 / 0.3 r_tip.

    python scripts/push_row_probe_blade_planes.py runs/push_row_probe_blade_planes.json
"""
import json, sys
from pathlib import Path
import numpy as np, trimesh
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
    mesh = load_case_mesh(case); hub, tip, zf = case_geometry(case, mesh); s = samples_from_mesh(mesh)
    v = trimesh.load(case/"impeller_cfd.stl").vertices; rv = np.hypot(v[:,0], v[:,1])/1000
    bl = v[rv > hub*1000/1000 + 0.001, 2]/1000
    le, te = float(bl.min()), float(bl.max())
    r, uz, uth = cylindrical_velocity(s.pts, s.u); z = s.pts[:,2]; hdz = max(0.04*tip, 0.002)
    res = {"le_mm": le*1000, "te_mm": te*1000}
    for g in (0.1, 0.3):
        planes = {"in": le - g*tip - hdz, "ex": te + g*tip + hdz}
        vals = {}
        for lab, z0 in planes.items():
            sel = (np.abs(z - z0) <= hdz) & (r >= hub) & (r <= tip); w = s.w[sel]
            f = lambda a: float(np.sum(a[sel]*w)/np.sum(w))
            vals[lab] = {"p": RHO*f(s.p), "q_uz": RHO*f(0.5*uz**2), "q_uth": RHO*f(0.5*uth**2), "n": int(sel.sum())}
        push = vals["ex"]["p"] + vals["ex"]["q_uz"] - vals["in"]["p"] - vals["in"]["q_uz"]
        res[f"g{g}"] = {"push": push, "dp_static": vals["ex"]["p"] - vals["in"]["p"], "q_uth_ex": vals["ex"]["q_uth"],
                        "p_in": vals["in"]["p"], "n": [vals["in"]["n"], vals["ex"]["n"]]}
    raw = json.loads((case/"_eval_result.json").read_text(encoding="utf-8")); res["cfm_load"] = raw["cfm_load"]
    out[name] = res
    print(name, "cfm %.1f LE %.1f TE %.1f mm" % (res["cfm_load"], res["le_mm"], res["te_mm"]),
          " | ".join("g%.1f push %.2f dps %.2f quth %.2f n%s" % (g, res[f"g{g}"]["push"], res[f"g{g}"]["dp_static"], res[f"g{g}"]["q_uth_ex"], res[f"g{g}"]["n"]) for g in (0.1, 0.3)), flush=True)
    del mesh, s
Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
