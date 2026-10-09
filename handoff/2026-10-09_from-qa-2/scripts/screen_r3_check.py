"""Cross-checks on the r3 shortlist: euler-vs-axial objectives for the top 5 + refs; camber>0.06 fail reasons."""
import csv, json, sys, os, functools, collections
sys.path.insert(0, os.getcwd()); sys.path.insert(0, "/workspace/fansim/screen")
import numpy as np
import fansim.fan_bem as FB
from fansim.optimize import search_space as SS
import bem_screen as S
from fansim.geometry.config import load_blade_params
SS.BOUNDS[S.SPACE]["max_camber"] = (0.0, 0.10)
D = "/workspace/fansim/research/screen_r3"
rows = [json.loads(l) for l in open(f"{D}/all_designs.jsonl")]
hc = [r for r in rows if r["flat"]["max_camber"] > 0.06]
print("camber>0.06 trials", len(hc), "first_fail", collections.Counter(str(r["first_fail"]) for r in hc).most_common(5))
feas = [r for r in rows if r["feasible"]]
eff = np.array([r["efficiency"] for r in feas]); print("feasible eff pct p50/p90/max", np.percentile(eff, [50, 90, 100]).round(1))
top_free = sorted(feas, key=lambda r: -r["cfm_free"])[:5]
print("top5 by free CFM:", [(r["id"], round(r["cfm_free"], 1), round(r["efficiency"], 1)) for r in top_free])
sl = list(csv.DictReader(open(f"{D}/shortlist.csv")))
out = {}
for model in ("euler", "axial_force"):
    S.pq_curve = functools.partial(FB.pq_curve, pressure_model=model)
    S.operating_point = functools.partial(FB.operating_point, pressure_model=model)
    st = S.evaluate(load_blade_params("config/problems/a12x25_reference.yaml"), {})
    for r in sl[2:7] + [{"id": "REF_9504"}]:
        name = r["id"]
        fl = json.load(open(f"/workspace/fansim/screen/designs/04_T06559.flat.json")) if name == "REF_9504" else \
            json.load(open(f"{D}/designs/{r['rank'].zfill(2)}_{name}.flat.json"))
        e = S.evaluate(S.blade_from_flat(dict(fl)), dict(fl))
        out.setdefault(name, {})[model] = dict(free=round(e["cfm_free"], 1), load=round(e["cfm_load"], 1), eff=round(e["efficiency"], 1),
                                               score=round(S.scalar_score(e, st), 3), ff=e["first_fail"])
    out.setdefault("STOCK", {})[model] = dict(free=round(st["cfm_free"], 1), load=round(st["cfm_load"], 1), eff=round(st["efficiency"], 1))
for k, v in out.items(): print(k, v)
json.dump(out, open(f"{D}/top5_euler_vs_axial.json", "w"), indent=1)
