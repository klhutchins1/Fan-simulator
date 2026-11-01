"""R23 A: is 13.71 Pa / 60 CFM on lt120's knee? Applies PREREG_R23 (0006f9b) A rules. No CFD run; numbers from repo files."""
import json, sys, time
import numpy as np
t0 = time.monotonic()
CFM = 2118.88
# docs/qa/benchmarks/lt120/curve.csv (Q m3/s, dP Pa), sorted by Q
MEAS = [(0.003785, 34.01), (0.015107, 17.14), (0.018878, 14.69), (0.028317, 13.71), (0.039644, 6.85)]
# CFD loaded points (CFM, dP) from 2026-10-18-lt120-validation-prereg.md and 2026-10-30-lt120-tip-gap-prereg.md
CFD = {
    "baseline_0.5mm_mesh5.8": [(65.0, 17.14), (72.4, 14.69), (74.7, 13.71), (89.6, 6.85)],
    "baseline_0.5mm_mesh6.2": [(65.5, 17.14, "INCONCLUSIVE"), (73.7, 14.69), (76.2, 13.71), (92.0, 6.85)],
    "gap_1.0mm_mesh5.8": [(77.3, 13.71), (94.9, 6.85)],
    "gap_1.5mm_mesh5.8": [(54.2, 13.71, "INCONCLUSIVE"), (89.3, 6.85)],
}

def slopes(q, p):
    return [(p[i + 1] - p[i]) / (q[i + 1] - q[i]) for i in range(len(q) - 1)]

def classes(s):
    st = min(s)
    out = []
    for x in s:
        if x >= 0: out.append("rising")
        elif abs(x) >= 0.5 * abs(st): out.append("steep")
        else: out.append("flat")
    return out

def verdict(q, p, idx):
    """idx = index of test point (a measured point) -> its two adjacent segments idx-1 (low-Q side), idx (high-Q side)."""
    s = slopes(q, p); c = classes(s)
    lo = c[idx - 1] if idx - 1 >= 0 else None
    hi = c[idx] if idx < len(c) else None
    rising = [i for i, x in enumerate(c) if x == "rising"]
    past = (hi in ("flat", "rising") and lo == "rising") or (bool(rising) and q[idx] < q[rising[0]])
    if past: v = "past the knee"
    elif lo == "steep" and hi == "steep": v = "on the steep branch"
    elif lo in ("flat", "rising") or hi in ("flat", "rising") or lo != hi: v = "at the knee"
    else: v = "unclassified"
    return v, s, c

def knee_q(q, p):
    s = slopes(q, p); st = min(s); thr = 0.5 * st
    mids = [(q[i] + q[i + 1]) / 2 for i in range(len(s))]
    i0 = s.index(st)  # walk to higher Q from the steepest segment: first crossing of 0.5*s_steep (|s| falls below)
    for i in range(i0, len(s) - 1):
        a, b = s[i], s[i + 1]
        if (a - thr) * (b - thr) <= 0 and a != b:
            return mids[i] + (thr - a) / (b - a) * (mids[i + 1] - mids[i])
    return None

q = [x[0] for x in MEAS]; p = [x[1] for x in MEAS]
IDX = 3  # 13.71 Pa point
v, s, c = verdict(q, p, IDX)
res = {"measured": {"Q_cfm": [round(x * CFM, 2) for x in q], "dP": p,
                    "slopes_Pa_per_m3s": [round(x, 1) for x in s], "slopes_Pa_per_cfm": [round(x / CFM, 4) for x in s],
                    "ratio_to_steep": [round(x / min(s), 3) for x in s], "classes": c, "verdict_13.71": v,
                    "verdict_6.85": "end point (only low-Q segment): class " + c[-1]}}
kq = knee_q(q, p)
res["measured"]["knee_Q_cfm_0.5steep"] = None if kq is None else round(kq * CFM, 1)
# Monte Carlo
rng = np.random.default_rng(23)
N = 5000; tally = {}; kqs = []
for _ in range(N):
    qq = [x * (1 + rng.uniform(-0.03, 0.03)) for x in q]; pp = [x + rng.uniform(-0.5, 0.5) for x in p]
    order = np.argsort(qq); qq = [qq[i] for i in order]; pp = [pp[i] for i in order]
    idx = list(order).index(IDX)
    vv, _, _ = verdict(qq, pp, idx); tally[vv] = tally.get(vv, 0) + 1
    k = knee_q(qq, pp); kqs.append(np.nan if k is None else k * CFM)
frac = {k: round(n / N, 4) for k, n in sorted(tally.items(), key=lambda t: -t[1])}
top = max(frac, key=frac.get)
res["mc"] = {"draws": N, "seed": 23, "dQ": "+-3% uniform", "dP": "+-0.5 Pa uniform (source.md: rig uncertainty unknown)",
             "fractions": frac, "robust": frac[top] >= 0.80, "top": top,
             "knee_Q_cfm_p5_p50_p95": [round(float(np.nanpercentile(kqs, x)), 1) for x in (5, 50, 95)],
             "knee_none_frac": round(float(np.mean(np.isnan(kqs))), 4)}
# exploratory: s_steep restricted to segments 2..4 (drop the near-shutoff segment)
c_ex = classes(s[1:])
res["exploratory_steep_from_s2"] = {"classes_s2_s4": c_ex, "verdict": "at the knee" if "flat" in c_ex[1:3] else "?"}
# PCHIP (report only)
try:
    from scipy.interpolate import PchipInterpolator
    f = PchipInterpolator(np.array(q) * CFM, np.array(p)); d = f.derivative()
    res["pchip_dPdQ_Pa_per_cfm"] = {"at_60cfm_13.71Pa": round(float(d(q[3] * CFM)), 4), "at_84cfm_6.85Pa": round(float(d(q[4] * CFM)), 4),
                                     "min_on_32_84": round(float(min(d(np.linspace(32, 84, 521)))), 4),
                                     "max_on_32_84": round(float(max(d(np.linspace(32, 84, 521)))), 4)}
except Exception as e:
    res["pchip_dPdQ_Pa_per_cfm"] = f"n/a ({e})"
# CFD shape
meas_s4_cfm = s[3] / CFM
res["cfd"] = {}
for name, pts in CFD.items():
    pts = sorted(pts, key=lambda t: t[0]); qc = [t[0] for t in pts]; pc = [t[1] for t in pts]
    flags = [t[2] if len(t) > 2 else "" for t in pts]
    sc = slopes(qc, pc); row = {"Q_cfm": qc, "dP": pc, "flags": flags, "slopes_Pa_per_cfm": [round(x, 4) for x in sc]}
    i = pc.index(13.71); j = pc.index(6.85)
    s_int = (pc[j] - pc[i]) / (qc[j] - qc[i])
    row["slope_6.85_13.71_Pa_per_cfm"] = round(s_int, 4)
    row["ratio_cfd_to_meas_on_6.85_13.71"] = round(s_int / meas_s4_cfm, 3)
    if len(sc) >= 2:
        cc = classes(sc); row["classes"] = cc
        vc, _, _ = verdict(qc, pc, i); row["class_at_13.71"] = vc
        row["shape_agrees"] = vc == v
    else:
        row["class_at_13.71"] = "n/a (one segment)"
    row["err_13.71_vs_60cfm_pct"] = round((qc[i] / 60.0 - 1) * 100, 1)
    row["err_6.85_vs_84cfm_pct"] = round((qc[j] / 84.0 - 1) * 100, 1)
    res["cfd"][name] = row
res["elapsed_s"] = round(time.monotonic() - t0, 2)
json.dump(res, open(sys.argv[1], "w"), indent=1)
print(json.dumps(res, indent=1))
