"""R23 B exploratory (post-hoc, NOT the prereg rule): BEM local flattening at the loaded pressure.
K4x: |dP/dQ| of BEM pq_curve (euler, default) at the flow where BEM dP = P, divided by the mean |dP/dQ| of the
BEM curve between 0.5*Q_free and Q_free; flag if < 0.5. No CFD."""
import json, sys
import numpy as np
from pathlib import Path
from fansim.fan_bem import pq_curve
from fansim.geometry.config import load_blade_params
from fansim.optimize.search_space import stock_blade_flat, blade_from_flat
P = {"a12x25": (blade_from_flat(stock_blade_flat("a12x25")), [5, 10, 15, 20]),
     "lt120": (load_blade_params(Path("validation/reference/lt120/params.json")), [6.85, 13.71])}
out = {}
for fan, (p, loads) in P.items():
    c = pq_curve(p, 2000.0, n_points=60)
    pts = sorted([(float(x.flow_cfm), float(x.dp_static_pa)) for x in c.points])
    out[fan] = {"attrs": [a for a in dir(c.points[0]) if not a.startswith("_")][:20]} if pts is None else {}
    if pts is None: continue
    q = np.array([a for a, b in pts]); d = np.array([b for a, b in pts])
    qf = float(c.free_delivery_cfm); g = np.gradient(d, q)
    ref = float(np.mean(np.abs(g[(q >= 0.5 * qf) & (q <= qf)])))
    for L in loads:
        i = [k for k in range(len(q) - 1) if (d[k] - L) * (d[k + 1] - L) <= 0]
        if not i: out[fan][L] = "no crossing"; continue
        k = i[-1]; qL = q[k] + (d[k] - L) / (d[k] - d[k + 1]) * (q[k + 1] - q[k])
        gL = abs(float(np.interp(qL, q, g)))
        out[fan][L] = {"q_bem_cfm": round(qL, 1), "abs_slope": round(gL, 3), "ref": round(ref, 3), "ratio": round(gL / ref, 2), "K4x": gL / ref < 0.5}
json.dump(out, open(sys.argv[1], "w"), indent=1); print(json.dumps(out))
