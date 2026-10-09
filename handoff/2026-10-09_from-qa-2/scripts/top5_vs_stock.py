"""Pre-registered (docs/qa/notes/axial-force-top5-vs-stock-criteria.md, sha256 66db0018...): screen score of
bem_9501..9505 vs Stock under axial_force (verdict) and euler (reported). Run from repo root, axial patch applied."""
import sys, os, csv, json, functools
sys.path.insert(0, os.getcwd()); sys.path.insert(0, "/workspace/fansim/screen")
import fansim.fan_bem as FB
import bem_screen as S
from fansim.optimize.search_space import blade_from_flat
from fansim.geometry.config import load_blade_params
CSV = "/workspace/fansim/handoff_in/2026-10-09_to-qa-2/cfd_designs.csv"
rows = {r["design_id"]: r for r in csv.DictReader(open(CSV))}   # only geometry columns are used here
ids = ["bem_9501", "bem_9502", "bem_9503", "bem_9504", "bem_9505"]
out = {}
for model in ("axial_force", "euler"):
    S.pq_curve = functools.partial(FB.pq_curve, pressure_model=model)
    S.operating_point = functools.partial(FB.operating_point, pressure_model=model)
    stock = S.evaluate(load_blade_params("config/problems/a12x25_reference.yaml"), {})
    res = {"stock": dict(score=1.0, free=stock.get("cfm_free"), load=stock.get("cfm_load"), eff=stock.get("efficiency"), feasible=stock["feasible"], first_fail=stock["first_fail"])}
    for i in ids:
        flat = json.loads(rows[i]["flat"]); rec = S.evaluate(blade_from_flat(flat), flat)
        sc = S.scalar_score(rec, stock) if "cfm_free" in rec and "cfm_free" in stock else None
        res[i] = dict(score=sc, free=rec.get("cfm_free"), load=rec.get("cfm_load"), eff=rec.get("efficiency"), feasible=rec["feasible"], first_fail=rec["first_fail"])
    out[model] = res
    print(f"== {model}")
    for k, v in res.items():
        print(f"  {k:9s} score {v['score'] if v['score'] is None else round(v['score'], 4)}  free {v['free'] and round(v['free'], 2)}  load {v['load'] and round(v['load'], 2)}  eff% {v['eff'] and round(v['eff'], 2)}  feasible {v['feasible']} ({v['first_fail']})")
    sc = [res[i]["score"] for i in ids]
    print("  ALL FIVE > 1.000:", all(s is not None and s > 1.0 for s in sc), "| order:", sorted(ids, key=lambda i: -(res[i]["score"] or -9)))
json.dump(out, open("/workspace/fansim/research/proto/r3/top5_vs_stock.json", "w"), indent=1, default=float)
