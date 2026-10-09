"""Before/after table for every lead variant on the benchmark cases. Writes compare.json."""
import sys, os, json, math, time
sys.path.insert(0, "/workspace/fansim/research/proto"); sys.path.insert(0, os.getcwd())
import numpy as np
import bem_variants as V, cases as C

RPM = 2000.0
cs = C.cases()
stock = cs["stock7"]

# Carter normaliser: Stock's mass-avg turning fraction at its own peak-efficiency flow (keeps Stock calibrated)
def carter_mean(p, q):
    o = V.Opts(); hub, tip = p.hub_radius / 1000, p.tip_radius / 1000
    _, al = V.operating_point(p, RPM, q, o, detail=True)
    ch, sg, cb = V._interp_geometry(p); fr = []; w = []
    edges = np.linspace(hub, tip, 21)
    for i in range(20):
        r = 0.5 * (edges[i] + edges[i + 1]); rf = (r - hub) / (tip - hub)
        fr.append(V.carter_turning_fraction(sg(rf), cb(rf), ch(rf) / 1000, 2 * math.pi * r / p.n_blades, al[i]))
        w.append(r)
    return float(np.average(fr, weights=w))
base = V.pq_curve(stock, RPM, V.Opts())
q_pe = base.peak_eff_cfm / V.CFM_PER_M3S
CREF = carter_mean(stock, q_pe)
VARIANTS = {
    "base": V.Opts(),
    "9a_bv_plate": V.Opts(polar="bv"),
    "9b_bv_plate+poststall": V.Opts(polar="bv_ps"),
    "ps_only_viterna": V.Opts(polar="ps"),
    "8_koch_cap": V.Opts(koch=True),
    "6_carter": V.Opts(carter=True, carter_ref=CREF),
    "11_bracket": V.Opts(solver="bracket"),
    "combo_9b+8": V.Opts(polar="bv_ps", koch=True),
    "8_koch_x1.67": V.Opts(koch=True, koch_scale=1.67),
    "X_axialforce": V.Opts(axial_force=True),
    "X_axialforce+ps": V.Opts(axial_force=True, polar="ps"),
}
res = {"carter_ref": CREF}
for vn, o in VARIANTS.items():
    t0 = time.time(); res[vn] = {}
    for n, p in cs.items():
        c = V.pq_curve(p, RPM, o)
        pts = c.points
        # load point vs case hose (8 Pa @ 50 CFM): k Q^2 intersection on the BEM curve
        k = 8.0 / 50.0 ** 2; qop = None
        for a, b in zip(pts, pts[1:]):
            fa, fb = a.dp_static_pa - k * a.flow_cfm ** 2, b.dp_static_pa - k * b.flow_cfm ** 2
            if fa > 0 >= fb:
                qop = a.flow_cfm + fa / (fa - fb) * (b.flow_cfm - a.flow_cfm); break
        res[vn][n] = dict(free=c.free_delivery_cfm, shut=c.shutoff_dp_pa, peak_eff=c.peak_efficiency,
                          q8=round(qop, 1) if qop else None, conv=c.converged,
                          pmax_w=max(x.power_w for x in pts))
    res[vn]["_s"] = round(time.time() - t0, 2)
json.dump(res, open("/workspace/fansim/research/proto/compare.json", "w"), indent=1, default=float)
print("carter_ref", round(CREF, 3))
names = list(cs)
for vn in VARIANTS:
    print(f"\n== {vn} ({res[vn]['_s']}s)")
    for n in names:
        r = res[vn][n]
        print(f"  {n:12s} free {str(r['free']):>6} shut {str(r['shut']):>7} eff {r['peak_eff']:5} q@hose {str(r['q8']):>5} Pmax {r['pmax_w']:5} conv {r['conv']}")
