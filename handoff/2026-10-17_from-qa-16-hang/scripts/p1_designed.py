"""QA r16 hang (PREREG 52eca5f) P1: designed hang, signed margin and low-point decomposition, analytic (no CAD).
Population: R7 stress inputs (unshrouded, no sample_error, forced cylinder wrap) + 600 guided samples (seed 16001).
Usage: python p1_designed.py <out.jsonl>"""
import gzip, json, math, sys, time
import numpy as np, optuna
import fansim
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat, blade_to_flat, suggest_params
from fansim.geometry import blade as B

R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
SL = ["n_blades", "chord_root", "chord_mid", "chord_tip", "stagger_root", "stagger_mid", "stagger_tip", "sweep_mid",
      "sweep_tip", "lean_mid", "lean_tip", "skew_mid", "skew_tip", "max_camber", "thickness_root", "thickness_mid",
      "thickness_tip", "camber_pos", "hub_radius", "tip_radius", "winglet_sweep", "winglet_lean", "le_sweep_mid",
      "le_sweep_tip"]


def low_point(p):
    """Signed designed margin and its decomposition at the low point (same loop as blade_hang_below_hub_mm)."""
    z_face, z_top = B._hub_axial_range(p)
    it = B._interp_stations(p, p.n_span); r0 = p.hub_radius - p.root_embed; kw = B._thick_scale_kw(p)
    best = (math.inf, None, None)
    for i in range(p.n_span):
        rf = float(it["r_frac"][i])
        pts = B._section_points_3d(r=r0 + (p.tip_radius - r0) * rf, r_frac=rf, chord=float(it["chord"][i]),
            stagger_deg=float(it["stagger_deg"][i]), thickness=float(it["thickness"][i]),
            max_camber=float(it["max_camber"][i]), camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]), lean_deg=float(it["lean_deg"][i]),
            n_chord=p.n_chord, features=p.features, le_skew=float(it["le_skew"][i]), tip_notch_count=p.tip_notch_count,
            tip_notch_depth_mm=p.tip_notch_depth_mm, **kw)
        z = min(v.z for v in pts)
        if z < best[0]: best = (z, i, rf)
    zl, i, rf = best
    c, beta, sw = float(it["chord"][i]), math.radians(float(it["stagger_deg"][i])), float(it["sweep"][i])
    te_drop = 0.5 * c * math.sin(beta)
    rlo, rhi = B._root_axial_span(p)
    st0 = min(p.stations, key=lambda s: s.r_frac)
    root_drop = 0.5 * st0.chord * math.sin(math.radians(st0.stagger_deg))
    return dict(s_d=float(z_face - zl), h_d=max(0.0, float(z_face - zl)), z_face=float(z_face), z_top=float(z_top),
                hub_h=float(z_top - z_face), root_lo=float(rlo), root_hi=float(rhi), low_rf=rf,
                low_r=r0 + (p.tip_radius - r0) * rf, low_chord=c, low_stagger=math.degrees(beta), low_sweep=sw,
                te_drop=te_drop, low_thick_term=float(zl - (-te_drop + sw)), root_drop=root_drop,
                root_thick_term=float(-rlo - root_drop), face_gap=float(rlo - z_face))


def rec_of(src, did, stratum, flat, feats):
    p = blade_from_flat(dict(flat, section_wrap="cylinder"), Features(**(feats or {})))
    p.section_wrap = "cylinder"
    r = dict(src=src, id=did, stratum=stratum, flat={k: flat.get(k) for k in SL if flat.get(k) is not None},
             n_span=int(p.n_span), n_stations=len(p.stations), features_active=bool(p.features.active),
             section_family=str(p.section_family), span_interp=str(p.span_interp))
    r.update(low_point(p)); r["validator_hang"] = B.blade_hang_below_hub_mm(p)
    assert abs(r["validator_hang"] - r["h_d"]) < 1e-9
    return r


def main(out):
    t0 = time.monotonic(); n = 0
    with open(out, "w") as fh:
        for x in (json.loads(l) for l in gzip.open(R7)):
            if x.get("sample_error") or float(x["flat"].get("shroud_thick_mm") or 0): continue
            fh.write(json.dumps(rec_of("r7", x["id"], x["stratum"], x["flat"], x.get("features"))) + "\n"); n += 1
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=16001))
        for k in range(600):
            tr = st.ask(); bp = suggest_params(tr, space="guided", with_extended=True)
            flat = blade_to_flat(bp); flat["hub_radius"] = bp.hub_radius; flat["tip_radius"] = bp.tip_radius
            fh.write(json.dumps(rec_of("guided", f"G_{k:04d}", "G", flat, None)) + "\n"); n += 1
    print("DONE", n, round(time.monotonic() - t0, 1), "s", fansim.__file__, flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
