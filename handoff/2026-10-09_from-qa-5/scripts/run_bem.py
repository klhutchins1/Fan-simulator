"""Run both fansim BEM pressure models (no tuning) on benchmark fans with full geometry."""
import json, csv, sys, os
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.geometry.config import load_blade_params
from fansim.fan_bem import pq_curve, PRESSURE_MODELS
B = sys.argv[1]; R6 = sys.argv[2]
def val(d): return d["value"]
def params_for(fid):
    g = json.load(open(os.path.join(B, fid, "geometry.json")))
    if fid == "nf-a12x25":
        p = load_blade_params(os.path.join(R6, "config/problems/a12x25_reference.yaml"))
        return p, g
    hub, tip = val(g["hub_radius_mm"]), val(g["tip_radius_mm"])
    sts = []
    for s in g["stations"]:
        rf = min(1.0, max(0.0, (val(s["r_mm"]) - hub) / (tip - hub)))
        sts.append(RadialStation(r_frac=rf, chord=val(s["chord_mm"]), stagger_deg=val(s["stagger_deg"]),
                                 thickness=val(s["thickness"]), max_camber=val(s["max_camber"]), camber_pos=val(s["camber_pos"])))
    if sts[-1].r_frac < 1.0:
        l = sts[-1]; sts.append(RadialStation(r_frac=1.0, chord=l.chord, stagger_deg=l.stagger_deg, thickness=l.thickness,
                                             max_camber=l.max_camber, camber_pos=l.camber_pos))
    p = BladeParams(n_blades=val(g["n_blades"]), hub_radius=hub, tip_radius=tip, rpm=val(g["rpm"]),
                    section_family=val(g["section_family"]))
    p.stations = sts
    return p, g
def interp(xs, ys, x):
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i]); return ys[i] + t * (ys[i + 1] - ys[i])
    return None
res = {"pressure_models": list(PRESSURE_MODELS)}
for fid in ("nf-a12x25", "lt120", "nv150"):
    p, g = params_for(fid)
    rows = list(csv.DictReader(open(os.path.join(B, fid, "curve.csv"))))
    q = [float(r["q_m3s"]) for r in rows]; dp = [float(r["dp_pa"]) for r in rows]; ptype = rows[0]["pressure_type"]
    rpm = float(rows[0]["rpm"]); gap = val(g["tip_gap_mm"])
    out = {}
    for m in PRESSURE_MODELS:
        c = pq_curve(p, rpm, n_points=40, pressure_model=m, tip_gap_mm=gap)
        bq = [pt.flow_m3s for pt in c.points]
        bdp = [(pt.dp_static_pa if ptype == "static" else pt.dp_total_pa) for pt in c.points]
        pts = []
        for qq, dd in zip(q, dp):
            b = interp(bq, bdp, qq) if qq > 0 else (c.shutoff_dp_pa if ptype == "static" else bdp[0])
            pts.append({"q": qq, "meas": dd, "bem": None if b is None else round(b, 2),
                        "err_pct": None if (b is None or dd == 0) else round(100 * (b - dd) / dd, 1)})
        free_meas = max(q) if dp[q.index(max(q))] == 0 else None
        out[m] = {"free_delivery_m3s": round(c.free_delivery_cfm / 2118.88, 5), "free_status": c.free_status,
                  "free_err_pct": None if not free_meas else round(100 * (c.free_delivery_cfm / 2118.88 - free_meas) / free_meas, 1),
                  "shutoff_bem_pa": round(c.shutoff_dp_pa, 2), "converged": c.converged,
                  "peak_eff": round(c.peak_efficiency, 3), "points": pts}
    res[fid] = {"pressure_type": ptype, "rpm": rpm, "tip_gap_mm": gap, **out}
json.dump(res, open(sys.argv[3], "w"), indent=1)
for fid in ("nf-a12x25", "lt120", "nv150"):
    for m in PRESSURE_MODELS:
        r = res[fid][m]; print(fid, m, "free", r["free_delivery_m3s"], r["free_err_pct"], r["free_status"], [(round(x["q"],4), x["meas"], x["bem"], x["err_pct"]) for x in r["points"]])
