"""Hedge view: Euler-mode re-score of the 400 best axial-mode feasible designs; best by min(axial, euler) score."""
import json, sys, os, functools
sys.path.insert(0, os.getcwd()); sys.path.insert(0, "/workspace/fansim/screen")
import fansim.fan_bem as FB
from fansim.optimize import search_space as SS
import bem_screen as S
from fansim.geometry.config import load_blade_params
SS.BOUNDS[S.SPACE]["max_camber"] = (0.0, 0.10)
D = "/workspace/fansim/research/screen_r3"
feas = sorted([r for r in map(json.loads, open(f"{D}/all_designs.jsonl")) if r["feasible"] and r.get("aoa_stalled_frac", 1) <= 0.5],
              key=lambda r: -r["score"])[:400]
S.pq_curve = functools.partial(FB.pq_curve, pressure_model="euler"); S.operating_point = functools.partial(FB.operating_point, pressure_model="euler")
st = S.evaluate(load_blade_params("config/problems/a12x25_reference.yaml"), {})
res = []
for r in feas:
    e = S.evaluate(S.blade_from_flat(dict(r["flat"])), dict(r["flat"]))
    res.append(dict(id=r["id"], axial=r["score"], euler=S.scalar_score(e, st) if "cfm_free" in e else float("nan"), euler_ff=e["first_fail"],
                    ax_free=r["cfm_free"], eu_free=e.get("cfm_free"), ax_eff=r["efficiency"], eu_eff=e.get("efficiency"), nb=r["flat"]["n_blades"], cam=r["flat"]["max_camber"]))
res.sort(key=lambda x: -min(x["axial"], x["euler"]))
json.dump(res, open(f"{D}/hedge_top400.json", "w"), indent=0)
print("n euler>1:", sum(x["euler"] > 1 for x in res), "of", len(res))
for x in res[:8]: print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()})
