"""QA-12 blend rules R1-R4, R6 (docs/qa/notes/prop-lowre-blend-criteria.md, sha256 e91b2804...). Run from repo root."""
import sys, os, math, json; sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
import numpy as np
import test_prop_uiuc_gws as T
from fansim.propeller.bemt import analyze, _section_aero
from fansim.propeller.polar import nondim
from fansim.prop_spec import _REGISTRY
from fansim.propeller.params_io import prop_params_from_flat
tag = sys.argv[1] if len(sys.argv) > 1 else "x"
D = T.D_M; g = T._gws_blade()
ct = lambda p, rpm: nondim(analyze(p, rpm).thrust_n, analyze(p, rpm).power_w, rpm=rpm, diameter_m=D, v_inf=0)["CT"]
pre = prop_params_from_flat(_REGISTRY["fpv_5inch"], {})
p4, p30 = ct(pre, 4000.0), ct(pre, 30000.0); r1 = p30 / p4 - 1
st = T._table("gwsdd_5x4.3_static_0493rd.txt")
c74 = ct(g, 7406.667); ratios = [(r, ct(g, r) / c) for r, c, _ in st]
spread = max(x for r, x in ratios if r >= 2500) - min(x for r, x in ratios if r >= 2500)
rm = 6047.0; errs = []
for J, c, cp, e in T._table("gwsdd_5x4.3_0512rd_6047.txt"):
    v = J * rm / 60 * D; pf = analyze(g, rm, v_forward=v)
    errs.append(nondim(pf.thrust_n, pf.power_w, rpm=rm, diameter_m=D, v_inf=v)["CT"] - c)
rms = math.sqrt(np.mean(np.square(errs)))
jumps = []
for a in (0, 4, 8):
    kw = {"low_re_blend": True} if "low_re_blend" in _section_aero.__code__.co_varnames else {}
    lo = _section_aero(math.radians(a), 0.04, re=39999.0, thickness=0.0633, **kw); hi = _section_aero(math.radians(a), 0.04, re=40000.0, thickness=0.0633, **kw)
    jumps.append((a, abs(lo[0] - hi[0]) / abs(hi[0]), abs(lo[1] - hi[1]) / abs(hi[1])))
mxj = max(max(j[1], j[2]) for j in jumps)
res = dict(tag=tag, preset_ct0_4k=p4, preset_ct0_30k=p30, creep=r1, gws_ct0_7407=c74, gws_ct0_err=c74 / 0.148983 - 1,
           ratios={int(r): x for r, x in ratios}, spread=spread, jrms=rms, jbias=float(np.mean(errs)), jumps=jumps, max_jump=mxj,
           preset_curve={r: ct(pre, float(r)) for r in (4000, 8000, 15000, 22000, 30000)})
json.dump(res, open(f"/workspace/fansim/research/proto/r3/blend_{tag}.json", "w"), indent=1)
print(f"[{tag}] R1 creep {100*r1:+.1f}% (CT0 {p4:.3f}->{p30:.3f}) | R2 GWS CT0@7407 {c74:.4f} ({100*(c74/0.148983-1):+.1f}%) | "
      f"R3 spread {spread:.3f} (ratios {min(x for _,x in ratios):.2f}..{max(x for _,x in ratios):.2f}) | R4 J-rms {rms:.4f} bias {np.mean(errs):+.4f} | R6 max jump {100*mxj:.1f}%")
print("  preset CT0:", {k: round(v, 3) for k, v in res["preset_curve"].items()})
