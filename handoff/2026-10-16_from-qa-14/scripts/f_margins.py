"""QA r14 Task F (PREREG_R14 586bbe9): 27.3d two-run margins from the queue's m1-m5 table (v3 planes). Numbers only.
Usage: python f_margins.py <out.json>"""
import json, math, sys, itertools, statistics as S
T = {  # run: (mean push, bars hub->tip, dead, tip ratio, backflow, swirl, proudman)
 "m1": (12.540, [7.54, 10.13, 11.18, 13.22, 17.05], 0.0325, 0.954, 0.0388, 0.5645, -13.7),
 "m2": (12.770, [7.57, 10.17, 11.98, 13.38, 16.79], 0.0340, 0.846, 0.0267, 0.6016, 22.2),
 "m3": (12.977, [7.58, 10.08, 11.42, 14.19, 17.33], 0.0349, 0.946, 0.0377, 0.5783, -4.7),
 "m4": (12.711, [7.66, 10.17, 11.54, 13.37, 16.81], 0.0298, 0.891, 0.0319, 0.5768, 19.4),
 "m5": (12.947, [8.26, 10.42, 11.45, 13.85, 17.18], 0.0259, 0.983, 0.0199, 0.5886, 18.2)}
ceil2 = lambda x: math.ceil(x * 100 - 1e-12) / 100; ceil1 = lambda x: math.ceil(x * 10 - 1e-12) / 10
R = {}
mp = [v[0] for v in T.values()]; bars = [v[1] for v in T.values()]; noise = [v[6] for v in T.values()]
rel2s = lambda xs: 2 * S.stdev(xs) / abs(S.mean(xs))
r_mean = rel2s(mp); r_bars = [rel2s([b[k] for b in bars]) for k in range(5)]
R["F1"] = {"mean_push_2sigma_pct": 100 * r_mean, "bars_2sigma": r_bars, "bars_tol": max(0.02, ceil2(max(r_bars))),
           "band_tol_incl_mean": max(0.02, ceil2(max([r_mean] + r_bars))), "noise_2sigma_db": 2 * S.stdev(noise), "noise_tol": max(0.5, ceil1(2 * S.stdev(noise)))}
R["F1"]["PASS"] = R["F1"]["bars_tol"] == 0.08 and round(R["F1"]["mean_push_2sigma_pct"], 1) == 2.9 and R["F1"]["noise_tol"] == 32.8
pairs = list(itertools.permutations(T, 2))
def mx(f): return max(pairs, key=lambda ab: f(*ab)), max(f(*ab) for ab in pairs)
F2 = {}
F2["mean_push_rel"] = mx(lambda a, b: abs(T[a][0] / T[b][0] - 1))
for k in range(5): F2[f"bar{k+1}_rel"] = mx(lambda a, b, k=k: abs(T[a][1][k] / T[b][1][k] - 1))
F2["dead_abs"] = mx(lambda a, b: abs(T[a][2] - T[b][2]))
F2["backflow_abs"] = mx(lambda a, b: abs(T[a][4] - T[b][4]))
F2["swirl_rel"] = mx(lambda a, b: abs(T[a][5] / T[b][5] - 1))
mn = min(pairs, key=lambda ab: T[ab[0]][3] / T[ab[1]][3]); F2["tip_ratio_min_d_over_s"] = (mn, T[mn[0]][3] / T[mn[1]][3])
TODAY = {"mean_push_rel": 0.03, "bar_rel": 0.08, "dead_abs": 0.02, "tip_factor": 0.90, "backflow_abs": 0.02, "swirl_rel": 0.10}
MASTER = {"mean_push_rel": 0.06, "bar_rel": 0.12, "dead_abs": 0.02, "tip_factor": 0.90, "backflow_abs": 0.02, "swirl_rel": 0.10,
          "CLOSE_mean": 0.08, "CLOSE_backflow": 0.02, "CLOSE_swirl": 0.10, "CLOSE_dead": 0.02, "CLOSE_tip_rel": 0.15}
trips = {}
trips["mean_push"] = sum(abs(T[a][0] / T[b][0] - 1) > 0.03 for a, b in pairs) / 2
trips["bars_any"] = sum(any(abs(T[a][1][k] / T[b][1][k] - 1) > 0.08 for k in range(5)) for a, b in pairs) / 2
trips["tip"] = sum(T[a][3] < 0.90 * T[b][3] for a, b in pairs)
trips["dead"] = sum(abs(T[a][2] - T[b][2]) > 0.02 for a, b in pairs) / 2
trips["backflow"] = sum(abs(T[a][4] - T[b][4]) > 0.02 for a, b in pairs) / 2
F2["pairs_tripping_today_of_10"] = trips
trips_m = {"mean_push>0.06": sum(abs(T[a][0] / T[b][0] - 1) > 0.06 for a, b in pairs) / 2,
           "bars_any>0.12": sum(any(abs(T[a][1][k] / T[b][1][k] - 1) > 0.12 for k in range(5)) for a, b in pairs) / 2,
           "tip_rel>0.15(CLOSE)": sum(T[a][3] / T[b][3] - 1 < -0.15 for a, b in pairs)}
F2["pairs_tripping_master_of_10"] = trips_m
R["F2"] = F2
mbars = max(F2[f"bar{k+1}_rel"][1] for k in range(5))
prop = {"mean_push_rel": max(0.03, ceil2(F2["mean_push_rel"][1])), "bar_rel": max(0.08, ceil2(mbars)), "dead_abs": max(0.02, ceil2(F2["dead_abs"][1])),
        "tip_factor": min(0.90, math.floor(F2["tip_ratio_min_d_over_s"][1] * 100 + 1e-12) / 100), "backflow_abs": max(0.02, ceil2(F2["backflow_abs"][1]))}
sq2 = {"mean_push_rel": ceil2(math.sqrt(2) * r_mean), "bar_rel": ceil2(math.sqrt(2) * max(r_bars)),
       "dead_abs": ceil2(math.sqrt(2) * 2 * S.stdev([v[2] for v in T.values()])), "backflow_abs": ceil2(math.sqrt(2) * 2 * S.stdev([v[4] for v in T.values()])),
       "tip_rel": ceil2(math.sqrt(2) * rel2s([v[3] for v in T.values()]))}
R["F3"] = {"proposal_maxpair": prop, "alt_sqrt2_2sigma": sq2}
# 9604 / 9610 same-mesh mean deltas (v3), 2026-10-16 audit Q1 table
D = {"9604": {"mean_push_rel": -0.328, "backflow_abs": 0.017, "dead_abs": -0.002, "tip_rel": 0.037, "swirl_abs": -0.256},
     "9610": {"mean_push_rel": 0.067, "backflow_abs": 0.060, "dead_abs": 0.048, "tip_rel": -0.75, "swirl_abs": 0.070}}
fl = []
for d, v in D.items():
    for row, today, new in (("mean_push_rel", 0.03, prop["mean_push_rel"]), ("backflow_abs", 0.02, prop["backflow_abs"]), ("dead_abs", 0.02, prop["dead_abs"])):
        out_today, out_new = abs(v[row]) > today, abs(v[row]) > new
        fl.append({"design": d, "row": row, "delta": v[row], "today_judged": out_today, "proposed_judged": out_new, "flips_to_same": out_today and not out_new})
    t_today = v["tip_rel"] < -(1 - 0.90); t_new = v["tip_rel"] < -(1 - prop["tip_factor"])
    fl.append({"design": d, "row": "tip", "delta": v["tip_rel"], "today_judged": t_today, "proposed_judged": t_new, "flips_to_same": t_today and not t_new})
R["F3"]["flip_rows"] = fl; R["F3"]["n_flip"] = sum(r["flips_to_same"] for r in fl)
json.dump(R, open(sys.argv[1], "w"), indent=1); print(json.dumps(R, indent=1))
