"""QA r17 C-r14 (PREREG_R17 a212b29): four refusal shares on the r14 P0 sample (seed 14004) and guided (14003),
then the pre-registered bounds ladder if (i+ii) > 5 %. Usage: python c_r14.py <out.json>"""
import json, math, sys
import numpy as np, optuna
sys.path.insert(0, __file__.rsplit("/", 1)[0])
optuna.logging.set_verbosity(optuna.logging.WARNING)
from fansim.optimize import search_space as SS
from fansim.optimize.search_space import suggest_params
from fansim.optimize.study import optimizer_max_tip_radius
from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
from c_common import rules
spec = get_fan_spec("a12x25"); lo = mount_min_hub_radius(spec); HUB = (lo, max(lo + 0.1, spec.hub_dia_mm[1] / 2)); MT = optimizer_max_tip_radius(spec)
HANG = ["sweep_mid", "sweep_tip", "chord_root", "chord_mid", "chord_tip", "stagger_root", "stagger_mid", "stagger_tip"]
P0 = {"max_camber": (0.015, 0.06), "stagger_root": (19.5, 48.0), "stagger_mid": (27.2, 48.0), "stagger_tip": (18.0, 38.0)}


def sample(seed, n, bounds=None, space="guided"):
    old = dict(SS.BOUNDS[space])
    if bounds: SS.BOUNDS[space] = dict(old, **bounds)
    try:
        st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=seed)); rows = []
        for i in range(n):
            tr = st.ask(); p = suggest_params(tr, space=space, hub_radius_range=HUB, max_tip_radius=MT)
            rows.append({"i": i, **{k: tr.params.get(k) for k in HANG}, **rules(p)})
        return rows
    finally:
        SS.BOUNDS[space] = old


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0, c - h), min(1, c + h)]


def auc(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if not len(a) or not len(b): return 0.5
    return float(((a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()) / (len(a) * len(b)))


def summ(rows):
    n = len(rows); s = {"n": n, "other_refused": sum(r["validator"].startswith("other") for r in rows),
                        "grown": sum(r["dh"] > 0 for r in rows)}
    for k in ("base", "i", "ii", "both"):
        c = sum(r[k] for r in rows); s[k] = {"k": c, "share": c / n, "wilson95": wilson(c, n)}
    ref = [r for r in rows if r["both"]]; al = [r for r in rows if not r["both"]]
    s["auc_both"] = {k: auc([r[k] for r in ref], [r[k] for r in al]) for k in HANG}
    return s


out = {"hub": HUB, "max_tip": MT, "guided_bounds": {k: list(v) for k, v in SS.GUIDED.items()}}
g = sample(14003, 300); out["guided_14003"] = summ(g)
b = dict(P0); r0 = sample(14004, 300, b); out["P0_14004"] = summ(r0)
json.dump({"P0": r0, "guided": g}, open(sys.argv[1].replace(".json", "_rows.json"), "w"), default=float)
ladder = []; s = out["P0_14004"]; step = 0
while s["both"]["share"] > 0.05 and step < 6:
    step += 1
    k = max(HANG, key=lambda x: abs(s["auc_both"][x] - 0.5)); a = s["auc_both"][k]
    lo_, hi_ = b.get(k, SS.GUIDED[k]); span = hi_ - lo_
    b[k] = (lo_ + 0.1 * span, hi_) if a < 0.5 else (lo_, hi_ - 0.1 * span)
    s = summ(sample(17000 + step, 300, b))
    ladder.append({"step": step, "moved": k, "auc": a, "bounds": {x: list(v) for x, v in b.items()},
                   "share_both": s["both"]["share"], "wilson95": s["both"]["wilson95"], "summary": s})
    print(step, k, round(a, 3), b[k], round(s["both"]["share"], 4), flush=True)
out["ladder"] = ladder
if ladder:
    out["holdout_17100"] = summ(sample(17100, 300, b)); out["final_bounds"] = {x: list(v) for x, v in b.items()}
json.dump(out, open(sys.argv[1], "w"), indent=1, default=float)
print({k: {q: out[k][q]["share"] for q in ("base", "i", "ii", "both")} for k in ("guided_14003", "P0_14004")}, flush=True)
print("DONE", flush=True)
