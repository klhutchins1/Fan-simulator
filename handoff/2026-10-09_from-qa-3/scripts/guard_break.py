"""Round-4 request 1b: try to break system_curve.bem_exploit_reason (Claude 5396796). Run from r4_axial root.
Pre-registered junk criteria J1/J2/J3 (docs/qa/notes/r4-prereg-axial-crosscheck-eff-audit.md, sha256 1252f73f...)."""
import copy, json, math, os, sys
sys.path.insert(0, os.getcwd())
import numpy as np
import fansim.fan_bem as FB
from fansim.geometry.config import load_blade_params
from fansim.optimize.search_space import blade_from_flat
from fansim.optimize.system_curve import bem_exploit_reason, EXPLOIT_MIN_PEAK_EFF
from fansim.geometry.blade import blade_solidity
RPM = 2000.0; N_EL = 20
def elem_flags(bp, q_m3s):
    hub, tip = bp.hub_radius / 1e3, bp.tip_radius / 1e3
    area = math.pi * (tip * tip - hub * hub); Vx = q_m3s / area; om = RPM * 2 * math.pi / 60
    ch, sg, cb = FB._interp_geometry(bp); e = np.linspace(hub, tip, N_EL + 1); st = neg = 0
    for i in range(N_EL):
        r = 0.5 * (e[i] + e[i + 1]); rf = (r - hub) / (tip - hub); U = om * r
        phi1 = math.atan2(Vx, U); w1 = math.hypot(Vx, U); re = w1 * ch(rf) / 1e3 / FB.NU_AIR
        a = math.radians(sg(rf)) - phi1
        band = math.radians(max(8.0, min(15.0, 10.0 + 3.0 * math.log10(max(re, 5000.0) / 20000.0))))
        st += abs(a) > band; neg += a < 0
    return st / N_EL, neg / N_EL
def assess(name, bp, cls):
    c = FB.pq_curve(bp, RPM, pressure_model="axial_force"); ce = FB.pq_curve(bp, RPM)
    why = bem_exploit_reason(bp, RPM, None)
    pk = max(c.points, key=lambda p: p.efficiency)
    q_pk = pk.flow_cfm / FB.CFM_PER_M3S if hasattr(FB, "CFM_PER_M3S") else pk.flow_cfm / 2118.88
    q_half = 0.5 * max(float(c.free_delivery_cfm), float(ce.free_delivery_cfm), 1.0) / 2118.88
    s1, n1 = elem_flags(bp, q_pk); s2, n2 = elem_flags(bp, q_half)
    stg = [s.stagger_deg for s in bp.stations]
    j3 = sum(1 for s in stg if s >= 70 or s < 0) / len(stg) >= 1 / 3
    j1, j2 = max(s1, s2) >= 0.5, max(n1, n2) >= 0.3
    try: sol = blade_solidity(bp)
    except Exception: sol = {"mid": float("nan")}
    return dict(name=name, cls=cls, guard=why or "PASS", peak_eff=float(c.peak_efficiency), status=c.free_status,
                ax_free=float(c.free_delivery_cfm), ax_shut=float(c.shutoff_dp_pa), eu_free=float(ce.free_delivery_cfm),
                eu_peak_eff=float(ce.peak_efficiency), stall_frac=max(s1, s2), neg_frac=max(n1, n2), stall_pk=s1, stall_half=s2, neg_pk=n1, neg_half=n2, J1=j1, J2=j2, J3=j3,
                junk=bool(j1 or j2 or j3), sol_mid=float(sol.get("mid", float("nan"))), nb=bp.n_blades)
R = []
stock = load_blade_params("config/problems/a12x25_reference.yaml")
def flat(nb, sr, sm, st, cr, cm, ct, cam, cam_r=None, cam_t=None):
    return {"n_blades": nb, "stagger_root": sr, "stagger_mid": sm, "stagger_tip": st, "chord_root": cr, "chord_mid": cm,
            "chord_tip": ct, "max_camber": cam, "camber_root": cam if cam_r is None else cam_r, "camber_mid": cam,
            "camber_tip": cam if cam_t is None else cam_t, "thickness_root": 0.08, "thickness_mid": 0.06, "thickness_tip": 0.04,
            "camber_pos": 0.4, "hub_radius": 21.5, "tip_radius": 54.5, "sweep_mid": 0, "sweep_tip": 0, "lean_mid": 0, "lean_tip": 0,
            "chord_basis": "measured"}
# --- editor-range grid + targeted shapes
for nb in (5, 7, 9, 11):
    for s in (15, 25, 35, 45, 55):
        for ch in (14, 30, 50):
            for cam in (0.0, 0.03, 0.06):
                R.append(assess(f"E_grid_b{nb}_s{s}_c{ch}_cam{cam}", blade_from_flat(flat(nb, s, s, s, ch, ch, ch, cam)), "editor"))
for nb in (5, 9, 11):
    for (sr, sm, st) in ((55, 35, 15), (15, 35, 55), (55, 55, 15), (15, 15, 55), (55, 15, 55), (15, 55, 15)):
        for ch in (14, 40):
            for cam in (0.0, 0.06):
                R.append(assess(f"E_twist_b{nb}_{sr}-{sm}-{st}_c{ch}_cam{cam}", blade_from_flat(flat(nb, sr, sm, st, ch, ch, ch, cam)), "editor"))
rng = np.random.default_rng(4)
for i in range(1500):
    sr, sm, st = rng.uniform(15, 55, 3); cr, cm, ct = rng.uniform(14, 50), rng.uniform(14, 60), rng.uniform(14, 70)
    cams = rng.uniform(0, 0.06, 3)
    R.append(assess(f"E_rand{i:04d}", blade_from_flat(flat(int(rng.integers(5, 12)), sr, sm, st, cr, cm, ct, cams[1], cams[0], cams[2])), "editor"))
# --- file-loadable (outside the editor): partial paddles, mixed hand, 2-3 blades, low solidity
n = len(stock.stations)
for k in range(1, n + 1):
    for ang in (75.0, 89.0):
        for side in ("outer", "inner"):
            p = copy.deepcopy(stock); idx = range(n - k, n) if side == "outer" else range(k)
            for j in idx: p.stations[j].stagger_deg = ang
            R.append(assess(f"F_paddle_{side}{k}_{ang:.0f}", p, "file"))
    for ang in (-20.0, -45.0):
        for side in ("outer", "inner"):
            p = copy.deepcopy(stock); idx = range(n - k, n) if side == "outer" else range(k)
            for j in idx: p.stations[j].stagger_deg = ang
            R.append(assess(f"F_revhand_{side}{k}_{ang:.0f}", p, "file"))
for nb in (1, 2, 3):
    p = copy.deepcopy(stock); p.n_blades = nb; R.append(assess(f"F_stock_{nb}blades", p, "file"))
for sc in (0.1, 0.2, 0.3, 0.5):
    p = copy.deepcopy(stock)
    for s in p.stations: s.chord *= sc
    R.append(assess(f"F_stock_chord_x{sc}", p, "file"))
for sc in (0.1, 0.2):
    p = copy.deepcopy(stock); p.n_blades = 2
    for s in p.stations: s.chord *= sc
    R.append(assess(f"F_2blade_chord_x{sc}", p, "file"))
for ang in (60.0, 65.0, 70.0, 80.0, 89.0):
    p = copy.deepcopy(stock)
    for s in p.stations: s.stagger_deg = ang
    R.append(assess(f"F_uniform_stagger_{ang:.0f}", p, "file"))
json.dump(R, open("/workspace/fansim/research/proto/r4/guard_break.json", "w"), indent=0, default=float)
slip = [r for r in R if r["guard"] == "PASS" and r["junk"]]
fr = [r for r in R if r["guard"] != "PASS" and r["cls"] == "editor" and not r["junk"] and r["eu_free"] >= 20]
print("n", len(R), "editor", sum(r["cls"] == "editor" for r in R), "refused", sum(r["guard"] != "PASS" for r in R))
print("SLIP editor", sum(r["cls"] == "editor" for r in slip), "SLIP file", sum(r["cls"] == "file" for r in slip), "FALSE REFUSALS", len(fr))
