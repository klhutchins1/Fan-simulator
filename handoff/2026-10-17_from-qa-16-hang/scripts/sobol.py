"""QA r16 hang (report-only addition to PREREG 52eca5f A2): Sobol first-order (S1) and total (ST) indices of the
designed signed margin s_d over the optimizer guided + extended box, using the exact validator geometry (no CAD).
Saltelli sampling, Jansen estimators, N base samples. Usage: python sobol.py <out.json> [N]"""
import json, sys, time
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from p1_designed import low_point
from fansim.geometry.features import Features
from fansim.optimize.search_space import GUIDED, EXTENDED, blade_from_flat

BOX = dict(GUIDED); BOX.update({k: EXTENDED[k] for k in ("hub_radius", "tip_radius", "thickness_root", "thickness_mid",
                                                         "thickness_tip", "camber_pos")})
NAMES = list(BOX)


def f(u):
    flat = {k: BOX[k][0] + float(v) * (BOX[k][1] - BOX[k][0]) for k, v in zip(NAMES, u)}
    flat["n_blades"] = int(round(flat["n_blades"]))
    p = blade_from_flat(dict(flat, section_wrap="cylinder"), Features()); p.section_wrap = "cylinder"
    return low_point(p)["s_d"]


def main(out, N=512):
    N = int(N); t0 = time.monotonic(); rng = np.random.default_rng(16006); k = len(NAMES)
    A = rng.random((N, k)); Bm = rng.random((N, k))
    fA = np.array([f(u) for u in A]); fB = np.array([f(u) for u in Bm]); V = np.var(np.concatenate([fA, fB]))
    S1, ST = {}, {}
    for j, n in enumerate(NAMES):
        AB = A.copy(); AB[:, j] = Bm[:, j]; fAB = np.array([f(u) for u in AB])
        S1[n] = float(np.mean(fB * (fAB - fA)) / V)          # Saltelli 2010
        ST[n] = float(0.5 * np.mean((fA - fAB) ** 2) / V)     # Jansen
    res = dict(N=N, var=float(V), box=BOX, S1=S1, ST=ST, interaction_share=1.0 - sum(S1.values()),
               frac_hang=float(np.mean(fA > 0)), frac_over2=float(np.mean(fA > 2)), mono_s=round(time.monotonic() - t0, 1))
    json.dump(res, open(out, "w"), indent=1)
    for n in sorted(NAMES, key=lambda n: -ST[n]):
        print(f"{n:15s} S1 {S1[n]:+.3f}  ST {ST[n]:.3f}")
    print("sum S1", round(sum(S1.values()), 3), "frac hang", res["frac_hang"], "over2", res["frac_over2"], res["mono_s"], "s")


if __name__ == "__main__":
    main(*sys.argv[1:])
