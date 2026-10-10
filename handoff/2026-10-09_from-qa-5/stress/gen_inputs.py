"""Generate every stress design's inputs (PREREG §1) into inputs.jsonl BEFORE any build.
Usage: python gen_inputs.py <out inputs.jsonl>"""
import json, sys, warnings
from dataclasses import asdict
from pathlib import Path

import numpy as np
import optuna

from fansim.optimize.search_space import (BOUNDS, EXTENDED, blade_to_flat, stock_blade_flat,
                                          suggest_params)

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.ERROR)
out = Path(sys.argv[1])
STRATA = [("S1", "open", {}, 6001, 600), ("S2", "guided", {}, 6002, 300),
          ("S3", "guided_lc", {}, 6003, 200), ("S4", "open", {"with_extended": True}, 6004, 400),
          ("S5", "open", {"with_extended": True, "with_features": True}, 6005, 300),
          ("S6", "open", {"with_winglet": True, "with_spacing": True}, 6006, 200),
          ("S7", "open", {"with_shroud": True}, 6007, 200)]
rows = []


def rec(stratum, idx, flat, feats, flags, extra=None, err=None):
    rows.append({"id": f"{stratum}_{idx:04d}", "stratum": stratum, "idx": idx, "flags": flags,
                 "flat": flat, "features": feats, "sample_error": err, **(extra or {})})


def to_rec(bp):
    return blade_to_flat(bp), asdict(bp.features)


for name, space, flags, seed, n in STRATA:
    st = optuna.create_study(sampler=optuna.samplers.QMCSampler(qmc_type="sobol", scramble=True, seed=seed))
    for i in range(n):
        t = st.ask()
        try:
            bp = suggest_params(t, space=space, **flags)
            flat, feats = to_rec(bp); err = None
        except ValueError as exc:
            flat, feats, err = dict(t.params), None, f"ValueError: {exc}"
        st.tell(t, 0.0)
        rec(name, i, flat, feats, {"space": space, **flags}, err=err)

# S8 edges
box = {**BOUNDS["open"], **EXTENDED}
centre = {k: (lo + hi) / 2 for k, (lo, hi) in box.items()}
centre["n_blades"] = 8
flags8 = {"space": "open", "with_extended": True}


def fixed(vals):
    v = dict(vals); v["n_blades"] = int(round(v["n_blades"]))
    return suggest_params(optuna.trial.FixedTrial(v), space="open", with_extended=True)


i = 0
def add8(vals, tag):
    global i
    try:
        flat, feats = to_rec(fixed(vals)); err = None
    except ValueError as exc:
        flat, feats, err = vals, None, f"ValueError: {exc}"
    rec("S8", i, flat, feats, flags8, {"s8_kind": tag}, err); i += 1


for k, (lo, hi) in box.items():
    for lab, val in (("min", lo), ("max", hi)):
        add8({**centre, k: val}, f"edge_{k}_{lab}")
rng = np.random.default_rng(6008)
top = lambda k: (box[k][1] - 0.1 * (box[k][1] - box[k][0]), box[k][1])
bot = lambda k: (box[k][0], box[k][0] + 0.1 * (box[k][1] - box[k][0]))
corners = {
    "c1_lowcamber_highlean": {"max_camber": (0.0, 0.02), "lean_tip": (20.0, 45.0)},
    "c2_thin_longtip": {"thickness_root": bot("thickness_root"), "thickness_mid": bot("thickness_mid"),
                        "thickness_tip": bot("thickness_tip"), "chord_tip": top("chord_tip")},
    "c3_manyblades_longchords": {"n_blades": (10, 11), "chord_root": top("chord_root"),
                                 "chord_mid": top("chord_mid"), "chord_tip": top("chord_tip")},
    "c4_sweep_lean": {"sweep_tip": top("sweep_tip"), "lean_tip": top("lean_tip")},
    "c5_smallhub_longroot": {"hub_radius": bot("hub_radius"), "chord_root": top("chord_root")},
}
for tag, sub in corners.items():
    for _ in range(20):
        v = {}
        for k, (lo, hi) in box.items():
            a, b = sub.get(k, (lo, hi))
            v[k] = int(rng.integers(a, b + 1)) if k == "n_blades" else float(rng.uniform(a, b))
        add8(v, tag)
# controls
src = Path("/workspace/fansim/repo-r3/handoff/2026-10-09_from-qa-2/screen_r3/cockpit_import/runs")
rec("CTL", 0, stock_blade_flat("a12x25"), None, {"control": "stock"}, {"s8_kind": "control_stock"})
for j, t in enumerate((9605, 9606, 9620, 9630), 1):
    f = next(src.glob(f"*/cockpit_assess/design_{t}/design.json"))
    rec("CTL", j, json.loads(f.read_text())["params"], None, {"control": f"screen_r3_{t}"},
        {"s8_kind": f"control_{t}"})
# order: pilot first (5 per S1-S7, 10 S8, 5 controls), then the rest round-robin by stratum
pilot = []
for s in ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
    pilot += [r for r in rows if r["stratum"] == s and r["idx"] < 5]
pilot += [r for r in rows if r["stratum"] == "S8" and r["idx"] < 10] + [r for r in rows if r["stratum"] == "CTL"]
pid = {r["id"] for r in pilot}
rest = [r for r in rows if r["id"] not in pid]
by = {}
for r in rest:
    by.setdefault(r["stratum"], []).append(r)
order = list(pilot)
while any(by.values()):
    for s in list(by):
        if by[s]:
            order.append(by[s].pop(0))
with out.open("w") as fh:
    for seq, r in enumerate(order):
        r["seq"] = seq; r["pilot"] = r["id"] in pid
        fh.write(json.dumps(r, default=float) + "\n")
print(len(order), "designs;", sum(r["sample_error"] is not None for r in order), "sampler errors")
