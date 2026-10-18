"""QA r14 Task C1, C2, C4 (PREREG_R14 586bbe9): optimizer space under wrap, no builds.
Usage: python c_space.py <out.json> <sample.jsonl>"""
import json, math, sys
import numpy as np, optuna
import fansim; assert fansim.__file__.startswith("/workspace/fansim/qa/run_r14"), fansim.__file__
optuna.logging.set_verbosity(optuna.logging.WARNING)
from fansim.optimize import search_space as SS
from fansim.optimize.search_space import suggest_params, blade_to_flat
from fansim.optimize.study import optimizer_max_tip_radius
from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
from fansim.geometry.blade import validate_blade_params, blade_hang_below_hub_mm
spec = get_fan_spec("a12x25"); lo = mount_min_hub_radius(spec); HUB = (lo, max(lo + 0.1, spec.hub_dia_mm[1] / 2)); MT = optimizer_max_tip_radius(spec)
STOCK = {"max_camber": (0.0235, 0.0478), "stagger_root": 23.5154, "stagger_mid": 31.1959, "stagger_tip": 22.4624}
KEYS = ["n_blades", "stagger_root", "stagger_mid", "stagger_tip", "chord_root", "chord_mid", "chord_tip", "sweep_mid", "sweep_tip", "lean_mid", "lean_tip", "max_camber", "hub_radius", "tip_radius"]
def sample(seed, n, space="guided", bounds=None):
    old = dict(SS.BOUNDS[space])
    if bounds: SS.BOUNDS[space] = dict(old, **bounds)
    try:
        st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=seed)); rows = []
        for i in range(n):
            tr = st.ask(); p = suggest_params(tr, space=space, hub_radius_range=HUB, max_tip_radius=MT)
            row = {"i": i, **{k: tr.params.get(k) for k in KEYS}, "section_wrap": p.section_wrap}
            row["hang"] = blade_hang_below_hub_mm(p)
            try: validate_blade_params(p); row["refused"] = False
            except ValueError as e: row["refused"] = True; row["why"] = str(e)[:160]; row["hang_refusal"] = "hang" in str(e)
            row["flat"] = blade_to_flat(p); rows.append(row)
        return rows
    finally:
        SS.BOUNDS[space] = old
def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))
def auc(a, b):  # P(refused value > allowed value)
    a, b = np.asarray(a, float), np.asarray(b, float)
    if not len(a) or not len(b): return None
    return float(((a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()) / (len(a) * len(b)))
def summarise(rows):
    n = len(rows); ref = [r for r in rows if r.get("hang_refusal")]; other = [r for r in rows if r["refused"] and not r.get("hang_refusal")]
    al = [r for r in rows if not r["refused"]]
    dist = {k: {q: float(np.percentile([r[k] for r in rows], qq)) for q, qq in (("min", 0), ("p5", 5), ("p50", 50), ("p95", 95), ("max", 100))} for k in KEYS}
    drv = {k: auc([r[k] for r in ref], [r[k] for r in al]) for k in KEYS}
    top = sorted([k for k in KEYS if drv[k] is not None], key=lambda k: -abs(drv[k] - 0.5))[:3]
    return {"n": n, "hang_refused": len(ref), "other_refused": len(other), "share": len(ref) / n, "wilson95": wilson(len(ref), n), "dist": dist,
            "auc": drv, "top3": top, "camber_in_stock_range": sum(0.024 <= r["max_camber"] <= 0.048 for r in rows) / n,
            "hang_pos": sum(r["hang"] > 0 for r in rows), "hang_median_of_pos": float(np.median([r["hang"] for r in rows if r["hang"] > 0] or [0])),
            "stagger_below_stock": {k: sum(r[k] < STOCK[k] for r in rows) / n for k in ("stagger_root", "stagger_mid", "stagger_tip")}}
OUT, SAMP = sys.argv[1], sys.argv[2]; R = {"stock": STOCK, "hub_range": HUB, "max_tip": MT, "guided_bounds": SS.GUIDED, "open_bounds": SS.OPEN}
g = sample(14003, 300); R["guided"] = summarise(g)
with open(SAMP, "w") as fh:
    for r in g: fh.write(json.dumps(r) + "\n")
R["open"] = summarise(sample(14003, 300, "open"))
# C4 ladder
G = SS.GUIDED; b = {"max_camber": (0.015, 0.06)}
for k in ("stagger_root", "stagger_mid", "stagger_tip"): b[k] = (min(G[k][0], round(STOCK[k] - 4.0, 1)), G[k][1])
ladder = []
for step in range(6):
    rows = sample(14004, 300, bounds=b); s = summarise(rows)
    ladder.append({"step": step, "bounds": {k: list(v) for k, v in b.items()}, "share": s["share"], "wilson95": s["wilson95"], "top3": s["top3"], "auc": {k: s["auc"][k] for k in ("stagger_root", "stagger_mid", "stagger_tip")}})
    if s["share"] <= 0.05: break
    drv = [k for k in s["top3"] if k.startswith("stagger_")] or sorted(("stagger_root", "stagger_mid", "stagger_tip"), key=lambda k: -abs((s["auc"][k] or .5) - .5))
    k = drv[0]; newhi = max(round(STOCK[k] + 4.0, 1), b[k][1] - 2.0)
    if newhi == b[k][1]:
        ladder[-1]["note"] = f"{k} upper already at Stock+4"; break
    b[k] = (b[k][0], newhi)
R["C4_ladder"] = ladder
json.dump(R, open(OUT, "w"), indent=1, default=float); print("DONE")
