"""Rules (a), (b), (b2) of docs/qa/notes/axial-force-retune-criteria.md (sha256 17e1e9c4...f7e2),
using the patch's own constants (no overrides). Run from the repo root with the axial-force patch applied:
    uv run python handoff/2026-10-09_from-qa/check_rules_abd.py [--screen-dir /path/to/screen/designs]
Rule (d) = default 'euler' curves byte-identical to the unpatched tree + existing tests pass (see README)."""
import argparse, copy, json, sys, os
from pathlib import Path
sys.path.insert(0, os.getcwd())
from fansim import fan_bem as FB
from fansim.geometry.blade import BladeParams
from fansim.geometry.config import load_blade_params
from fansim.optimize.search_space import blade_from_flat

ap = argparse.ArgumentParser(); ap.add_argument("--screen-dir", default="/workspace/fansim/screen/designs")
a = ap.parse_args()
stock = load_blade_params("config/problems/a12x25_reference.yaml")
def restag(v):
    p = copy.deepcopy(stock)
    for s in p.stations: s.stagger_deg = v
    return p
cases = {"stock7": stock, "paddle89": restag(89.0), "rev-45": restag(-45.0), "rev-60": restag(-60.0),
         "zero_blades": BladeParams(n_blades=0)}
top = sorted(Path(a.screen_dir).glob("0[1-5]_*.flat.json"))
for f in top: cases[f.name.split(".")[0]] = blade_from_flat(json.loads(f.read_text()))
print(f"AX_SLIP={FB.AX_SLIP} AX_K_FRICTION={FB.AX_K_FRICTION} CD_90={FB.CD_90}")
R = {}
for n, p in cases.items():
    for m in ("euler", "axial_force"):
        c = FB.pq_curve(p, 2000.0, pressure_model=m)
        R[(m, n)] = dict(free=float(c.free_delivery_cfm), shut=float(c.shutoff_dp_pa), eff=float(c.peak_efficiency), st=c.free_status)
    print(f"{n:12s} euler {R[('euler', n)]}\n{'':12s} axial {R[('axial_force', n)]}")
ax = {n: R[("axial_force", n)] for n in cases}; s = ax["stock7"]
ra = 54.1 <= s["free"] <= 66.1 and 17.2 <= s["shut"] <= 28.6
bad = lambda r: r["st"] == "no_rise" or (r["free"] < 0.5 * s["free"] and r["eff"] < 0.5 * s["eff"])
rb = all(bad(ax[n]) for n in ("paddle89", "rev-45", "rev-60")) and ax["zero_blades"]["free"] == 0.0
tn = [n for n in cases if n[:2] in ("01", "02", "03", "04", "05")]
rb2 = len(tn) == 5 and all(ax[n]["st"] == "crossed" and ax[n]["free"] >= 0.8 * s["free"] and ax[n]["eff"] >= 0.5 * s["eff"] for n in tn)
print(f"RULE (a) {'PASS' if ra else 'FAIL'}: Stock {s['free']} CFM in [54.1,66.1], shut-off {s['shut']} Pa in [17.2,28.6]")
print(f"RULE (b) {'PASS' if rb else 'FAIL'}: limits free < {0.5*s['free']:.1f} CFM and eff < {0.5*s['eff']:.3f}, or no_rise; 0-blade free {ax['zero_blades']['free']}")
print(f"RULE (b2) {'PASS' if rb2 else 'FAIL'}: top-5 need crossed, free >= {0.8*s['free']:.1f}, eff >= {0.5*s['eff']:.3f} (n={len(tn)}); beat Stock: {sum(ax[n]['free'] > s['free'] for n in tn)}/5")
