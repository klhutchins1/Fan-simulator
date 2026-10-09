# Run from the repo root: uv run python handoff/2026-10-09_from-qa/scripts/creep.py
"""CT0 rpm-creep attribution (monkeypatch only). Run from repo root. Prints a table + writes JSON."""
import sys, os, re, json, math; sys.path.insert(0, os.getcwd())
import numpy as np
import fansim.propeller.bemt as BM
import fansim.propeller.polars as PO
from fansim.prop_spec import _REGISTRY
from fansim.propeller.params_io import prop_params_from_flat
from fansim.propeller.polar import nondim
from fansim.geometry.blade import BladeParams, RadialStation

U = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uiuc_gws_5x4.3")
def rows(fn): return np.array([l.split() for l in open(fn) if re.match(r"^\s*[-0-9.]", l)], float)
g = rows(f"{U}/gwsdd_5x4.3_geom.txt"); g = g[g[:, 0] <= 0.99]; R = 63.5; hub = g[0, 0] * R
st = [RadialStation((a * R - hub) / (R - hub), c * R, b, 0.08, 0.04, 0.4) for a, c, b in g]; st[-1].r_frac = 1.0
GWS = BladeParams(n_blades=2, hub_radius=hub, tip_radius=R, stations=st)
GST = rows(f"{U}/gwsdd_5x4.3_static_0493rd.txt"); GJ = rows(f"{U}/gwsdd_5x4.3_0512rd_6047.txt")
PRE = prop_params_from_flat(_REGISTRY["fpv_5inch"], {})
D = 0.127
orig_sa, orig_comp, orig_tab = BM._section_aero, BM._compressibility_cl_cd, PO.section_table
RE_LO = 4.0e4

def setup(M=True, F=True, T=True, fix_re=None, fb="clamp"):
    """M: Mach on; F: analytic fallback below RE_LO on (else fb='clamp' -> lowest table);
    T: table Re trend on (else every section evaluated at fix_re)."""
    BM._compressibility_cl_cd = orig_comp if M else (lambda cl, cd, m, **k: (cl, cd))
    def sa(alpha, camber, re=None, thickness=0.12):
        r = re
        if not T and r is not None: r = fix_re
        if not F and r is not None and r < RE_LO: r = RE_LO
        return orig_sa(alpha, camber, re=r, thickness=thickness)
    BM._section_aero = sa

def ct0(p, rpm):
    pf = BM.analyze(p, rpm); nd = nondim(pf.thrust_n, pf.power_w, rpm=rpm, diameter_m=D, v_inf=0); return nd["CT"], nd["CP"]

def re75(p, rpm):
    ch, _, _, _, r0, rt = BM._interp_geom(p); r = r0 + 0.75 * (rt - r0)
    return rpm * 2 * math.pi / 60 * r / 1000 * ch(r) / 1000 / BM.NU_AIR

V = {
 "as is": dict(),
 "no Mach (M off)": dict(M=False),
 "no fallback (F off: clamp to 4e4 table)": dict(F=False),
 "M+F off": dict(M=False, F=False),
 "fixed Re 4e4, M off (T,F off)": dict(M=False, T=False, fix_re=4e4),
 "fixed Re 8e4, M off": dict(M=False, T=False, fix_re=8e4),
 "fixed Re 1.6e5, M off": dict(M=False, T=False, fix_re=1.6e5),
 "fixed Re 4e4, Mach on": dict(T=False, fix_re=4e4),
}
RPMS = [4000, 8000, 15000, 22000, 30000]
out = {"re75_preset": {r: round(re75(PRE, r)) for r in RPMS}, "re75_gws": {int(r): round(re75(GWS, r)) for r in GST[:, 0]}}
print("Re at 0.75R preset:", out["re75_preset"]); print("Re at 0.75R GWS:", out["re75_gws"])
for name, kw in V.items():
    setup(**kw)
    pre = [ct0(PRE, r)[0] for r in RPMS]
    gr = [ct0(GWS, r)[0] / c for r, c, _ in GST]
    g74 = ct0(GWS, 7406.667)[0]
    rm = 6047.0; ctj = []
    for J, c, *_ in GJ:
        pf = BM.analyze(GWS, rm, v_forward=J * rm / 60 * D); ctj.append(nondim(pf.thrust_n, pf.power_w, rpm=rm, diameter_m=D, v_inf=J * rm / 60 * D)["CT"] - c)
    rms = math.sqrt(np.mean(np.square(ctj)))
    sel = GST[:, 0] >= 2500
    spread = max(np.array(gr)[sel]) - min(np.array(gr)[sel])
    out[name] = dict(preset=dict(zip(RPMS, pre)), creep=pre[-1] / pre[0] - 1, gws_ratio=dict(zip([int(x) for x in GST[:, 0]], gr)), gws74=g74, spread=spread, jrms=rms)
    print(f"{name:42s} preset CT0 " + " ".join(f"{x:.3f}" for x in pre) + f" | creep {100*(pre[-1]/pre[0]-1):+5.0f}% | GWS@7407 {g74:.3f} ({100*(g74/0.149-1):+.0f}%) "
          f"ratio 1.5k..7.9k " + " ".join(f"{x:.2f}" for x in gr) + f" spread(>=2.5k) {spread:.3f} | J-rms {rms:.4f}")
setup()
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "creep.json"), "w"), indent=1, default=float)
