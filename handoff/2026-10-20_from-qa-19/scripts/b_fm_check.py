"""QA r19 B diagnostic (post-hoc, report only): figure of merit of the TUD static case, BEMT vs measured (propeller convention).
This check exposed the first-reading normalisation error (measured FM 0.38 / torque over the 0.18 N m cell). Usage: python b_fm_check.py <tud_geom.txt> <tud_forces.json> <out.json>"""
import json, math, sys
sys.path.insert(0, "/workspace/fansim/qa/r19/scripts")
import b_bemt as BB
from fansim.propeller import bemt
rows = BB.geom_rows(sys.argv[1]); out = {}
for be in ("table", "neuralfoil"):
    bemt.set_polar_backend(be)
    for sec, t in (("known", 0.12), ("generic", 0.06)):
        p = BB.blade(rows, 150.0, thickness=t, camber=0.04)
        perf = bemt.analyze(p, rpm=5000.0)
        T = perf.thrust_n; P = perf.power_w; A = math.pi * 0.15 ** 2
        out[f"{be}|{sec}"] = dict(T=T, P=P, FM=perf.figure_of_merit, FM_raw=perf.figure_of_merit_raw, P_ideal=T ** 1.5 / math.sqrt(2 * bemt.RHO_AIR * A), conv=perf.converged)
        print(be, sec, out[f"{be}|{sec}"])
Fm = json.load(open(sys.argv[2])); ct = Fm["CT"]["points"][0]["val"]; cq = Fm["CQ"]["points"][0]["val"]
T = ct * bemt.RHO_AIR * (5000 / 60) ** 2 * 0.3 ** 4; P = 2 * math.pi * cq * bemt.RHO_AIR * (5000 / 60) ** 3 * 0.3 ** 5
out["measured"] = dict(T=T, P=P, FM=T ** 1.5 / math.sqrt(2 * bemt.RHO_AIR * math.pi * 0.15 ** 2) / P)
print("measured", out["measured"])
json.dump(out, open(sys.argv[3], "w"), indent=1)
