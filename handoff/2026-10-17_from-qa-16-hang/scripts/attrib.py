"""QA r16 hang (PREREG 52eca5f) attribution A1/A2 on P1 (designed margin s_d) and, when given, P2 (A = built - designed).
numpy only (ridge with inner-CV alpha). Usage: python attrib.py <p1.jsonl> <out.json> [p2.jsonl]"""
import json, math, sys
import numpy as np

SL = ["n_blades", "chord_root", "chord_mid", "chord_tip", "stagger_root", "stagger_mid", "stagger_tip", "sweep_mid",
      "sweep_tip", "lean_mid", "lean_tip", "skew_mid", "skew_tip", "max_camber", "thickness_root", "thickness_mid",
      "thickness_tip", "camber_pos", "hub_radius", "tip_radius", "winglet_sweep", "winglet_lean"]
ALPHAS = [1e-4, 1e-3, 1e-2, 0.1, 1.0, 10.0]


def design(rows, names):
    X = np.array([[float(r["flat"].get(k, 0.0) or 0.0) for k in names] for r in rows])
    keep = [j for j in range(X.shape[1]) if np.ptp(X[:, j]) > 1e-9]
    return X[:, keep], [names[j] for j in keep]


def expand(Z, quad):
    cols = [Z]
    if quad:
        n = Z.shape[1]
        cols += [Z[:, [i]] * Z[:, [j]] for i in range(n) for j in range(i, n)]
    return np.hstack(cols)


def ridge_fit(F, y, a):
    mu, sd = F.mean(0), F.std(0) + 1e-12; G = (F - mu) / sd; ym = y.mean()
    w = np.linalg.solve(G.T @ G + a * len(y) * np.eye(G.shape[1]), G.T @ (y - ym))
    return lambda Fn: ((Fn - mu) / sd) @ w + ym


def r2(y, yh):
    return 1.0 - float(np.sum((y - yh) ** 2) / np.sum((y - y.mean()) ** 2))


def folds(n, k, seed):
    idx = np.random.default_rng(seed).permutation(n); return [idx[i::k] for i in range(k)]


def cv(Xraw, y, quad, seed=16003, perm_groups=None):
    mu, sd = Xraw.mean(0), Xraw.std(0) + 1e-12; Z = (Xraw - mu) / sd
    fs = folds(len(y), 5, seed); yh = np.zeros_like(y); imp = np.zeros(Z.shape[1]); rng = np.random.default_rng(seed + 1)
    for f in fs:
        tr = np.setdiff1d(np.arange(len(y)), f)
        inner = folds(len(tr), 3, seed + 2); best = (-1e9, None)
        for a in ALPHAS:  # inner CV for alpha
            s = []
            for g in inner:
                t2 = np.setdiff1d(np.arange(len(tr)), g)
                m = ridge_fit(expand(Z[tr][t2], quad), y[tr][t2], a); s.append(r2(y[tr][g], m(expand(Z[tr][g], quad))))
            if np.mean(s) > best[0]: best = (np.mean(s), a)
        m = ridge_fit(expand(Z[tr], quad), y[tr], best[1]); yh[f] = m(expand(Z[f], quad))
        if perm_groups:
            base = r2(y[f], yh[f])
            for j in range(Z.shape[1]):
                Zp = Z[f].copy(); Zp[:, j] = rng.permutation(Zp[:, j]); imp[j] += (base - r2(y[f], m(expand(Zp, quad)))) / 5
    return r2(y, yh), imp


def phys(rows):
    out = []
    for r in rows:
        f = r["flat"]; X = {}
        for k, sw in (("root", 0.0), ("mid", f.get("sweep_mid", 0.0)), ("tip", f.get("sweep_tip", 0.0))):
            X[k] = 0.5 * f[f"chord_{k}"] * math.sin(math.radians(f[f"stagger_{k}"])) - float(sw or 0.0)
        out.append([X["root"], X["mid"], X["tip"], X["mid"] - X["root"], X["tip"] - X["root"],
                    max(X["mid"], X["tip"]) - X["root"]])
    return np.array(out), ["X_root", "X_mid", "X_tip", "X_mid-X_root", "X_tip-X_root", "max(X_mid,X_tip)-X_root"]


def analyse(rows, y, label):
    X, names = design(rows, SL)
    r1, imp1 = cv(X, y, False, perm_groups=True)
    r2q, imp2 = cv(X, y, True, perm_groups=True)
    P, pn = phys(rows); r3, _ = cv(P, y, False)
    r3q, _ = cv(P, y, True)
    order = np.argsort(-imp2)
    # sign of effect (extends/shrinks): mean partial slope of a linear fit on raw units
    A = np.hstack([X, np.ones((len(y), 1))]); coef = np.linalg.lstsq(A, y, rcond=None)[0]
    return dict(label=label, n=len(y), cv_r2_M1_linear=r1, cv_r2_M2_quadratic=r2q, cv_r2_M3_phys_linear=r3,
                cv_r2_M3_phys_quadratic=r3q, interactions_gain=r2q - r1,
                grouped_importance_M2=[(names[j], round(float(imp2[j]), 4)) for j in order],
                importance_M1=[(names[j], round(float(imp1[j]), 4)) for j in np.argsort(-imp1)],
                linear_slope_raw_units={names[j]: round(float(coef[j]), 4) for j in range(len(names))})


def pairwise_top(rows, y, top):
    """CV R^2 gain from adding each single pairwise product to the linear model (top drivers only)."""
    X, names = design(rows, SL); idx = [names.index(t) for t in top if t in names]
    base, _ = cv(X, y, False); res = []
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            Xa = np.hstack([X, X[:, [idx[a]]] * X[:, [idx[b]]]]); g, _ = cv(Xa, y, False)
            res.append((names[idx[a]] + " x " + names[idx[b]], round(g - base, 4)))
    return sorted(res, key=lambda t: -t[1])


def main(p1, out, p2=None):
    P1all = [json.loads(l) for l in open(p1)]
    # Deviation (logged in the note): the 5 CTL recipes carry a full station payload, so their geometry is not the
    # 3-slot sliders; with them in, ridge M2 extrapolated to CV R^2 = -1645. A2 uses the 2736 slider designs.
    P1 = [r for r in P1all if r["stratum"] != "CTL"]
    y = np.array([r["s_d"] for r in P1]); res = {"P1_s_d": analyse(P1, y, "designed signed margin, all P1")}
    G = [r for r in P1 if r["src"] == "guided"]; res["P1_guided_s_d"] = analyse(G, np.array([r["s_d"] for r in G]), "guided only")
    top = [n for n, _ in res["P1_s_d"]["grouped_importance_M2"][:8]]
    res["P1_pairwise_gain_top8"] = pairwise_top(P1, y, top)
    # A1 decomposition summary on hanging designs
    H = [r for r in P1all if r["s_d"] > 0]
    dec = np.array([[r["te_drop"], -r["low_sweep"], r["low_thick_term"] * -1, -r["root_drop"], -r["root_thick_term"],
                     -(r["face_gap"])] for r in H])
    s_rec = dec[:, 0] + dec[:, 1] + dec[:, 2] + dec[:, 3] + dec[:, 4] + dec[:, 5]
    res["A1"] = dict(n_hanging=len(H), terms=["TE drop c/2 sin(beta) at low point", "minus sweep at low point",
                     "TE thickness/camber below TE line", "minus root TE drop", "minus root thickness/camber",
                     "minus face gap (margin 1.5 + bias)"],
                     median_terms=[round(float(v), 3) for v in np.median(dec, 0)],
                     residual_max=float(np.max(np.abs(s_rec - np.array([r["s_d"] for r in H])))),
                     low_rf_counts={str(round(k, 3)): int(v) for k, v in zip(*np.unique([r["low_rf"] for r in H], return_counts=True))},
                     low_r_range=[min(r["low_r"] for r in H), max(r["low_r"] for r in H)],
                     low_r_range_refused=[min(r["low_r"] for r in H if r["s_d"] > 2), max(r["low_r"] for r in H if r["s_d"] > 2)])
    if p2:
        Q = {json.loads(l)["id"]: json.loads(l) for l in open(p2)}
        rows = [dict(r, **{"A": Q[r["id"]]["s_b"] - r["s_d"]}) for r in P1 if r["id"] in Q and "s_b" in Q[r["id"]]]
        Hh = [r for r in rows if r["s_d"] > 0]
        yA = np.array([r["A"] for r in Hh])
        res["P2_A_hanging"] = analyse(Hh, yA, "A = built - designed, designs with designed hang > 0")
        for r in Hh: r["flat"] = dict(r["flat"], h_d=r["s_d"])
        X, names = design(Hh, SL + ["h_d"]); Ab = np.hstack([X, np.ones((len(yA), 1))])
        res["P2_A_linear_with_hd"] = {n: round(float(c), 4) for n, c in zip(names + ["const"], np.linalg.lstsq(Ab, yA, rcond=None)[0])}
    json.dump(res, open(out, "w"), indent=1)
    for k, v in res.items():
        if isinstance(v, dict) and "cv_r2_M1_linear" in v:
            print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk.startswith("cv") or kk == "interactions_gain"})
            print("  top M2:", v["grouped_importance_M2"][:10])
    print("pairwise:", res["P1_pairwise_gain_top8"][:8]); print("A1:", res["A1"])


if __name__ == "__main__":
    main(*sys.argv[1:])
