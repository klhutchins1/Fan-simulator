"""QA r16 hang (PREREG 52eca5f) Option A: cheap predictors of BUILT hang, fit on a 50/50 split of P2 (seed 16004),
scored on the hold-out. A-0 designed; A-1 1.75 x designed; A-2 no-CAD emulation of the 2-iteration chord fixed point
(clip chord loss read from wrapped section points at each measured station) with <=2 fitted constants; A-3 linear on
h_d + physics features. Usage: python optA.py <p1.jsonl> <p2.jsonl> <out.json>"""
import json, math, sys, time
from dataclasses import replace
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from p2_built import params_of
from fansim.geometry import blade as B
from fansim.geometry.chord_realisation import _station_measure_fracs, with_loft_chords


def station_section_zmin(p, rf):
    """min z and stagger of the wrapped section of params p at span fraction rf (interpolated like the loft)."""
    ctrl = sorted(p.stations, key=lambda s: s.r_frac); rs = [s.r_frac for s in ctrl]
    g = {n: float(np.interp(rf, rs, [getattr(s, n) for s in ctrl])) for n in
         ("chord", "stagger_deg", "thickness", "max_camber", "camber_pos", "sweep", "skew", "le_sweep", "le_skew", "lean_deg")}
    r0 = p.hub_radius - p.root_embed; kw = B._thick_scale_kw(p)
    pts = B._section_points_3d(r=r0 + (p.tip_radius - r0) * rf, r_frac=rf, chord=g["chord"], stagger_deg=g["stagger_deg"],
        thickness=g["thickness"], max_camber=g["max_camber"], camber_pos=g["camber_pos"], sweep=g["sweep"], skew=g["skew"],
        le_sweep=g["le_sweep"], lean_deg=g["lean_deg"], n_chord=p.n_chord, features=p.features, le_skew=g["le_skew"],
        tip_notch_count=p.tip_notch_count, tip_notch_depth_mm=p.tip_notch_depth_mm, **kw)
    return min(v.z for v in pts), g["stagger_deg"]


def emulate(p, n_iter=2, k_loss=1.0):
    """Loft chords after n_iter fixed-point updates where measured = loft - k_loss * clip loss (no CAD)."""
    face = float(B._hub_axial_range(p)[0]); fr = _station_measure_fracs(p); tip = float(p.tip_radius)
    r0 = p.hub_radius - p.root_embed; span = tip - r0; tgt = [float(s.chord) for s in p.stations]; loft = list(tgt)
    for _ in range(n_iter):
        q = with_loft_chords(p, loft)
        for i, f in enumerate(fr):
            if f is None: continue
            rf = min(1.0, (f * tip - r0) / span); zmin, stg = station_section_zmin(q, rf)
            loss = k_loss * max(0.0, face - zmin) / max(math.sin(math.radians(abs(stg))), 0.05)
            m = loft[i] - loss
            if m >= 2.0: loft[i] = float(np.clip(loft[i] * tgt[i] / m, 5.0, 90.0))
    q = with_loft_chords(p, loft)
    return float(face - min_z(q))


def min_z(p):
    it = B._interp_stations(p, p.n_span); r0 = p.hub_radius - p.root_embed; kw = B._thick_scale_kw(p); z = math.inf
    for i in range(p.n_span):
        rf = float(it["r_frac"][i])
        pts = B._section_points_3d(r=r0 + (p.tip_radius - r0) * rf, r_frac=rf, chord=float(it["chord"][i]),
            stagger_deg=float(it["stagger_deg"][i]), thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]), skew=float(it["skew"][i]),
            le_sweep=float(it["le_sweep"][i]), lean_deg=float(it["lean_deg"][i]), n_chord=p.n_chord, features=p.features,
            le_skew=float(it["le_skew"][i]), tip_notch_count=p.tip_notch_count, tip_notch_depth_mm=p.tip_notch_depth_mm, **kw)
        z = min(z, min(v.z for v in pts))
    return z


def score(y, yh):
    e = yh - y; over, under = y > 2.0, y <= 2.0
    return dict(n=len(y), MAE=float(np.mean(np.abs(e))), p95_abs=float(np.percentile(np.abs(e), 95)), bias=float(np.mean(e)),
                sens_at_2=float(np.mean(yh[over] > 2.0)) if over.any() else None, n_over2=int(over.sum()),
                false_refusal_at_2=float(np.mean(yh[under] > 2.0)) if under.any() else None)


def main(p1, p2, out):
    P1 = {json.loads(l)["id"]: json.loads(l) for l in open(p1)}
    Q = [json.loads(l) for l in open(p2)]; Q = [q for q in Q if "s_b" in q]
    rng = np.random.default_rng(16004); ids = sorted(q["id"] for q in Q); rng.shuffle(ids)
    fit_ids = set(ids[: len(ids) // 2]); t0 = time.monotonic(); rows = []
    for q in Q:
        p = params_of(P1[q["id"]]); t1 = time.monotonic(); e1 = emulate(p); dt = time.monotonic() - t1
        rows.append(dict(id=q["id"], fit=q["id"] in fit_ids, h_d=q["h_d"], s_d=q["s_d"], h_b=q["h_b"], s_b=q["s_b"],
                         emu=e1, emu_s=dt, flat=P1[q["id"]]["flat"]))
    print("emulated", len(rows), round(time.monotonic() - t0), "s", flush=True)
    F = [r for r in rows if r["fit"]]; H = [r for r in rows if not r["fit"]]
    yF = np.array([r["h_b"] for r in F]); yH = np.array([r["h_b"] for r in H])
    pos = lambda v: np.maximum(0.0, v)
    res = {"n_fit": len(F), "n_holdout": len(H), "emulator_s_per_design_median": float(np.median([r["emu_s"] for r in rows]))}
    res["A-0 designed"] = score(yH, np.array([r["h_d"] for r in H]))
    res["A-1 1.75x designed"] = score(yH, 1.75 * np.array([r["h_d"] for r in H]))
    # A-2: emulator, then a fitted affine correction (2 constants) on the signed emulator output
    eF = np.array([r["emu"] for r in F]); eH = np.array([r["emu"] for r in H])
    res["A-2a emulator raw"] = score(yH, pos(eH))
    sF = np.array([r["s_b"] for r in F]); a, b = np.polyfit(eF, sF, 1)
    res["A-2b emulator affine"] = dict(score(yH, pos(a * eH + b)), a=float(a), b=float(b))
    # A-3: linear on h_d, s_d and physics features (fit half)
    def feats(r):
        f = r["flat"]; X = [0.5 * f[f"chord_{k}"] * math.sin(math.radians(f[f"stagger_{k}"])) - float(f.get(f"sweep_{k}", 0) or 0)
                            for k in ("root", "mid", "tip")]
        return [r["s_d"], r["h_d"], X[1] - X[0], X[2] - X[0], 1.0]
    XF = np.array([feats(r) for r in F]); XH = np.array([feats(r) for r in H]); w = np.linalg.lstsq(XF, sF, rcond=None)[0]
    res["A-3 linear"] = dict(score(yH, pos(XH @ w)), coef=[float(v) for v in w], terms=["s_d", "h_d", "Xmid-Xroot", "Xtip-Xroot", "1"])
    # A-1b report-only: single fitted ratio on hanging designs of the fit half
    k = float(np.sum(yF * np.array([r["h_d"] for r in F])) / np.sum(np.array([r["h_d"] for r in F]) ** 2))
    res["A-1b fitted ratio (report-only)"] = dict(score(yH, k * np.array([r["h_d"] for r in H])), k=k)
    res["ratio_hb_over_hd_hd_ge_1"] = float(np.median([r["h_b"] / r["h_d"] for r in rows if r["h_d"] >= 1.0]))
    res["ratio_hb_over_hd_hd_ge_0p5"] = float(np.median([r["h_b"] / r["h_d"] for r in rows if r["h_d"] >= 0.5]))
    res["counts"] = dict(designed_over2=sum(r["h_d"] > 2 for r in rows), built_over2=sum(r["h_b"] > 2 for r in rows),
                         hang_built_not_designed=sum(r["h_b"] > 0 and r["h_d"] <= 0 for r in rows))
    json.dump(dict(res, rows=rows), open(out, "w"), indent=1)
    for kk, v in res.items(): print(kk, v)


if __name__ == "__main__":
    main(*sys.argv[1:])
