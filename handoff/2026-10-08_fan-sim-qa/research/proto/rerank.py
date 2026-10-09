"""Would the variant change the screen ranking? Re-score the 517 guarded-feasible screen designs
with the screen's own score (free, hose-point, eta_op, derate) recomputed from each variant's curve."""
import sys, os, json, math
sys.path.insert(0, "/workspace/fansim/research/proto"); sys.path.insert(0, "/workspace/fansim/screen"); sys.path.insert(0, os.getcwd())
import numpy as np
import bem_variants as V
from fansim.optimize.search_space import blade_from_flat
from fansim.geometry.config import load_blade_params
from fansim.fan_spec import A12X25
from fansim.optimize.system_curve import probe_flow_cfm, intersect_fan_line, k_from_pa, SystemCurveError
from scipy.stats import spearmanr

rows = [json.loads(l) for l in open("/workspace/fansim/screen/all_designs.jsonl")]
feas = [r for r in rows if r["feasible"] or (all(r["flags"].get(g, False) for g in r["flags"]) and r.get("aoa_stalled_frac", 1) <= 0.5)]
feas = [r for r in rows if all(r["flags"].values()) and r.get("aoa_stalled_frac", 1) <= 0.5]
print("designs", len(feas))
CREF = json.load(open("/workspace/fansim/research/proto/compare.json"))["carter_ref"]
VARS = {"base": V.Opts(), "6_carter": V.Opts(carter=True, carter_ref=CREF), "8_koch_x1.67": V.Opts(koch=True, koch_scale=1.67),
        "9b_ps": V.Opts(polar="bv_ps"), "X_axialforce+ps": V.Opts(axial_force=True, polar="ps")}
BUDGET = A12X25.max_shaft_power_w_leeway

def score(p, gap, o):
    c = V.pq_curve(p, 2000.0, o, tip_gap_mm=gap)
    if c.free_delivery_cfm is None: return None
    q0 = c.free_delivery_cfm
    try:
        q1 = probe_flow_cfm(c, 8.0); q1 = min(q1, 0.999 * q0)
        qop, _ = intersect_fan_line(q0, q1, 8.0, k_from_pa(8.0))
    except (SystemCurveError, Exception):
        return None
    op = V.operating_point(p, 2000.0, qop / V.CFM_PER_M3S, o, tip_gap_mm=gap)
    pw = max(V.operating_point(p, 2000.0, q / V.CFM_PER_M3S, o, tip_gap_mm=gap).power_w for q in (q0, q1))
    d = min(1.0, (BUDGET / max(pw, 1e-9)) ** (1 / 3))
    return (q0 * d, qop * d, op.efficiency * 100)

stock = load_blade_params("config/problems/a12x25_reference.yaml")
out = {}
for vn, o in VARS.items():
    s0 = score(stock, 0.5, o)
    sc = []
    for r in feas:
        v = score(blade_from_flat(r["flat"]), max(r["tip_gap_mm"], 0), o)
        sc.append(np.nan if v is None or s0 is None else (v[0] / s0[0] + v[1] / s0[1] + v[2] / s0[2]) / 3)
    out[vn] = (s0, np.array(sc))
b = out["base"][1]; top_b = set(np.argsort(-b)[:30])
for vn, (s0, sc) in out.items():
    ok = ~np.isnan(sc)
    rho = spearmanr(b[ok], sc[ok]).correlation
    top = set(np.argsort(-np.nan_to_num(sc, nan=-9))[:30]); top5 = [feas[i]["id"] for i in np.argsort(-np.nan_to_num(sc, nan=-9))[:5]]
    print(f"{vn:16s} stock(free,load,eta)={tuple(round(x,1) for x in s0) if s0 else None} rho_vs_base={rho:.3f} "
          f"top30_overlap={len(top & top_b)}/30 n_beat_stock={(sc>1).sum()} best={np.nanmax(sc):.3f} top5={top5}")
