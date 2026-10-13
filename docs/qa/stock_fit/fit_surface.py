"""QA r9 Task C prototype (PREREG_R9 a0260c0): fit the wrapped Stock recipe to the A12x25 STL SURFACE.
Start: config/problems/a12x25_reference.yaml (v3, cylinder). Variables (always on): per station 1..6
d_sweep, d_skew (mm), d_stagger (deg); camber deltas at stations 2..6 (bounded +/-0.004 so V2's 0.005
camber tolerance is not spent). Objective (proxy, for speed): unsigned distance from 2500 fixed points on
the reference blade surface (r/R 0.45-1.0) to 9 rotated copies of ONE built blade (chord realisation frozen
at the v3 loft chords, tip-trimmed, hub-face clipped), after a rigid rotation+axial alignment fixed at the
start. scipy least_squares (trf, bounded). The proposal is then judged ONLY by surf_lib.official_distance
on a full build_impeller build (normal chord realisation) and surf_lib.v2_check.
Usage: python fit_surface.py <outdir>"""
import dataclasses, json, sys, time, tempfile
from pathlib import Path
import numpy as np, trimesh, yaml
from scipy.optimize import least_squares
sys.path.insert(0, str(Path(__file__).parent))
from surf_lib import official_distance, v2_check, build_full, rot, REF
from fansim.geometry.config import load_blade_params
from fansim.geometry.blade import build_blade_solid, clip_blade_below, _hub_axial_range
from fansim.geometry.chord_realisation import prepare_loft_chords
from fansim.geometry import export_stl
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True); LOG = open(OUT / "fit_log.txt", "a")
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n"); LOG.flush()
p0 = load_blade_params("config/problems/a12x25_reference.yaml"); tip = p0.tip_radius
loft0 = prepare_loft_chords(p0); loft_chords = [s.chord for s in loft0.stations]
ref = trimesh.load(REF, force="mesh"); ref.merge_vertices()
rp, _ = trimesh.sample.sample_surface_even(ref, 12000, seed=7); rr = np.hypot(rp[:, 0], rp[:, 1]) / tip
rp = rp[(rr >= 0.45) & (rr <= 1.0)]; rp = rp[np.random.default_rng(7).choice(len(rp), min(2500, len(rp)), replace=False)]
IS = list(range(1, 7)); IC = list(range(2, 7))
def unpack(x):
    st = []
    for i, s in enumerate(p0.stations):
        d = {}
        if i in IS:
            k = IS.index(i); d = dict(sweep=s.sweep + x[3 * k], skew=s.skew + x[3 * k + 1], stagger_deg=s.stagger_deg + x[3 * k + 2])
        if i in IC: d["max_camber"] = s.max_camber + x[3 * len(IS) + IC.index(i)]
        st.append(dataclasses.replace(s, **d))
    return dataclasses.replace(p0, stations=st)
def proxy_mesh(p):
    pl = dataclasses.replace(p, stations=[dataclasses.replace(s, chord=c) for s, c in zip(p.stations, loft_chords)])
    b = build_blade_solid(pl, _chord_realized=True); b = clip_blade_below(pl, b, _hub_axial_range(pl)[0])
    with tempfile.TemporaryDirectory() as td:
        export_stl(b, Path(td) / "b.stl"); m = trimesh.load(Path(td) / "b.stl", force="mesh")
    ms = []
    for k in range(p.n_blades):
        mk = m.copy(); a = 2 * np.pi * k / p.n_blades
        T = np.eye(4); T[:2, :2] = [[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]; mk.apply_transform(T); ms.append(mk)
    return trimesh.util.concatenate(ms)
ALIGN = None
def resid(x, tag=""):
    t = time.monotonic(); m = proxy_mesh(unpack(x)); pq = trimesh.proximity.ProximityQuery(m)
    a, dz = ALIGN; q = rot(rp - [0, 0, dz], -a)
    _, d, _ = pq.on_surface(q)
    reg = np.concatenate([0.05 * x[:3 * len(IS)], 5.0 * x[3 * len(IS):]])
    if tag: log(tag, f"proxy mean {d.mean():.4f} outer {d[np.hypot(q[:,0],q[:,1])/tip >= 0.8].mean():.4f} ({time.monotonic()-t:.1f}s)")
    return np.concatenate([d, reg])
# fixed alignment from the start recipe: search rotation (one pitch) + dz on the proxy
x0 = np.zeros(3 * len(IS) + len(IC)); m0 = proxy_mesh(p0); pq0 = trimesh.proximity.ProximityQuery(m0); best = None
pitch = 2 * np.pi / p0.n_blades
for a in np.linspace(0, pitch, 73)[:-1]:
    for dz in np.linspace(-2, 2, 17):
        _, d, _ = pq0.on_surface(rot(rp[::5] - [0, 0, dz], -a))
        if best is None or d.mean() < best[0]: best = (d.mean(), a, dz)
ALIGN = best[1:]; log("align", ALIGN, "start proxy", round(best[0], 4))
resid(x0, "start")
lb = np.concatenate([np.tile([-3.0, -3.0, -1.0], len(IS)), -0.004 * np.ones(len(IC))]); ub = -lb
xs = np.concatenate([np.tile([0.3, 0.3, 0.2], len(IS)), 0.002 * np.ones(len(IC))])
t0 = time.monotonic()
sol = least_squares(resid, x0, bounds=(lb, ub), x_scale=xs, diff_step=0.02, max_nfev=12, method="trf", verbose=0)
log("lsq", sol.status, sol.message, "nfev", sol.nfev, f"{(time.monotonic()-t0)/60:.1f} min")
resid(sol.x, "end")
json.dump({"x": sol.x.tolist(), "align": list(ALIGN)}, open(OUT / "fit_x.json", "w"))
p1 = unpack(sol.x)
def to_yaml(p, path, head):
    d = yaml.safe_load(open("config/problems/a12x25_reference.yaml"))
    d["stations"] = [{k: round(float(getattr(s, k)), 4) for k in ("r_frac", "chord", "stagger_deg", "thickness", "max_camber", "camber_pos", "sweep", "skew", "lean_deg", "le_sweep", "le_skew")} for s in p.stations]
    with open(path, "w") as fh:
        fh.write(head); yaml.safe_dump(d, fh, sort_keys=False, default_flow_style=None, width=200)
to_yaml(p1, OUT / "a12x25_reference_surface_fit_proposal.yaml",
        "# QA round 9 Task C PROPOSAL (not shipped): v3 wrapped recipe + surface-distance fit (docs/qa/stock_fit/fit_surface.py).\n"
        "# Changed vs v3: per-station sweep/skew/stagger (stations 1-6) and camber (stations 2-6). Everything else = v3.\n")
for name, p in (("proposal", p1),):
    stl = OUT / f"/tmp/qa9c_{name}.stl"; m = build_full(p, f"/tmp/qa9c_{name}.stl")
    dist = official_distance(p, m); ok, rows = v2_check(f"/tmp/qa9c_{name}.stl")
    log(name, json.dumps({"dist": dist, "v2_ok": ok, "v2": rows}))
    json.dump({"dist": dist, "v2_ok": ok, "v2": rows, "x": sol.x.tolist()}, open(OUT / f"{name}_eval.json", "w"), indent=1)
