"""QA r14 Task B1-B4 (PREREG_R14 586bbe9): independent maths check. Expected values are computed here from first
principles BEFORE the unit under test is called. Usage: python b_maths.py <out.json>"""
import json, math, sys, tempfile, random
from pathlib import Path
import numpy as np
import fansim; assert fansim.__file__.startswith("/workspace/fansim/qa/run_r14"), fansim.__file__
OUT = sys.argv[1]; R = {}
def agree(got, exp, rel=0.01, ab=0.001):
    return abs(got - exp) <= max(rel * abs(exp), ab)
# ---------------- B1 cfm_from_outlet_flow ----------------
FT3 = 0.3048 ** 3; CFM = 60.0 / FT3; RHO = 1.2
def write_case(d, flows_by_time, p_in=0.0, p_out=0.0, n=None):
    d = Path(d)
    for t0, flows in flows_by_time.items():
        it0 = int(t0)
        def wr(fo, fn, rows):
            p = d / "postProcessing" / fo / str(t0); p.mkdir(parents=True, exist_ok=True)
            (p / fn).write_text("# Time value\n" + "".join(f"{it0 + i + 1}\t{r}\n" for i, r in enumerate(rows)))
        N = len(flows)
        wr("outletFlow", "surfaceFieldValue.dat", [f"{f:.10g}" for f in flows])
        wr("inletP", "surfaceFieldValue.dat", [f"{p_in}"] * N)
        wr("outletP", "surfaceFieldValue.dat", [f"{p_out}"] * N)
        wr("forces", "force.dat", ["(0 0 0.01) (0 0 0) (0 0 0)"] * N)
        wr("forces", "moment.dat", ["(0 0 -0.002) (0 0 0) (0 0 0)"] * N)
cases = {}
osc = [0.05] * 100 + [0.02 + 0.004 * math.sin(2 * math.pi * i / 50) for i in range(1, 401)]
cases["a_const"] = ({"0": [0.025] * 200}, 0.025 * CFM, None)
cases["b_negative"] = ({"0": [-0.010] * 200}, -0.010 * CFM, None)
tail = osc[int(len(osc) * 0.75):]
cases["c_osc_tail25"] = ({"0": osc}, sum(tail) / len(tail) * CFM, None)
cases["d_restart_latest"] = ({"0": [0.010] * 100, "500": [0.020] * 100, "1000": [0.030] * 100}, 0.030 * CFM, None)
cases["e_pressure"] = ({"0": [0.02] * 100}, 0.02 * CFM, 5.0 * RHO)
R["B1_expected_first"] = {k: {"cfm": v[1], "dp": v[2]} for k, v in cases.items()}
from fansim.cfd.metrics import parse_fan_metrics, CFM_PER_M3S
b1 = {}
for k, (fl, ecfm, edp) in cases.items():
    with tempfile.TemporaryDirectory() as td:
        write_case(td, fl, *((-2.0, 3.0) if k == "e_pressure" else (0.0, 0.0)))
        m = parse_fan_metrics(td, omega_rad_s=2000 * 2 * math.pi / 60)
        row = {"cfm": m.cfm, "exp_cfm": ecfm, "agree_cfm": agree(m.cfm, ecfm), "sign_ok": (m.cfm > 0) == (ecfm > 0)}
        if edp is not None: row.update(dp=m.static_pressure_rise_pa, exp_dp=edp, agree_dp=agree(m.static_pressure_rise_pa, edp))
        if k == "c_osc_tail25":
            # convention probe: which row window matches?
            n = len(osc); row["n_rows"] = n
            for lo in (int(n * 0.75) - 1, int(n * 0.75), int(n * 0.75) + 1):
                row[f"mean_rows_{lo}_end"] = sum(osc[lo:]) / len(osc[lo:]) * CFM
        b1[k] = row
b1["CFM_PER_M3S"] = CFM_PER_M3S; b1["exact_CFM_PER_M3S"] = CFM; b1["const_rel_err"] = CFM_PER_M3S / CFM - 1
R["B1"] = b1
# ---------------- B2 motor derate ----------------
BUDGET = 12.0 * 0.14 * 0.50
exp_lam = {P: min(1.0, (BUDGET / P) ** (1 / 3)) for P in (0.5, 0.84, 1.68, 3.0)}
def my_op(Qf, pf, Ql, pl, k_pa, eta_f, eta_l):
    # line P(Q) = pf + (pl-pf)*(Q-Qf)/(Ql-Qf), Q in m3/s; hose P = k Q^2, k = k_pa/(50 CFM)^2
    qf, ql = Qf / CFM, Ql / CFM; k = k_pa / (50.0 / CFM) ** 2; s = (pl - pf) / (ql - qf)
    # k Q^2 - s Q - (pf - s qf) = 0
    a, b, c = k, -s, -(pf - s * qf); q = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
    if not (0 < q < qf): q = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)
    t = (q - qf) / (ql - qf); t = min(1, max(0, t))
    return q * CFM, k * q * q, eta_f + t * (eta_l - eta_f)
Qf, pf, Ql, load = 55.0, 1.5, 44.0, 8.0; ef, el = 0.12, 0.20
rated_op = my_op(Qf, pf, Ql, load, load, ef, el)
R["B2_expected_first"] = {"budget_w": BUDGET, "lambda": exp_lam, "rated_op": rated_op}
from fansim.fan_spec import get_fan_spec
from fansim.motor.envelope import A12X25_MOTOR
from fansim.optimize.rederate import derate_factor, rederate_scale, rescore_from_raw
spec = get_fan_spec("a12x25"); b2 = {"spec_budget": spec.max_shaft_power_w_leeway, "motor_env_budget": A12X25_MOTOR.max_shaft_power_w,
      "budget_agree": agree(spec.max_shaft_power_w_leeway, BUDGET) and agree(A12X25_MOTOR.max_shaft_power_w, BUDGET), "cases": []}
for P, lam in exp_lam.items():
    got_l = derate_factor(BUDGET, P)
    raw = {"free": {"cfm": Qf, "static_pressure_rise_pa": pf, "shaft_power_w": P * 0.9, "efficiency": ef},
           "load": {"cfm": Ql, "static_pressure_rise_pa": load, "shaft_power_w": P, "efficiency": el}}
    got = rescore_from_raw(raw, budget_w=BUDGET, target_rpm=2000.0, load_pa=load)
    e_free, e_load, e_eta = lam * Qf, lam * rated_op[0], rated_op[2] * 100
    # the derated op pressure we expect: lam^2 * rated op pressure
    row = {"P": P, "lam_exp": lam, "lam_got": got_l, "lam_agree": agree(got_l, lam),
           "cfm_free": got["cfm_free"], "cfm_free_exp": e_free, "cfm_load": got["cfm_load"], "cfm_load_exp": e_load,
           "eta": got["efficiency"], "eta_exp": e_eta, "rpm": got["actual_rpm"], "rpm_exp": 2000 * lam,
           "dp_op_exp": lam ** 2 * rated_op[1], "dp_op_from_hose_got": (load / (50 / CFM) ** 2) * (got["cfm_load"] / CFM) ** 2}
    row["all_agree"] = all(agree(row[a], row[b]) for a, b in (("cfm_free", "cfm_free_exp"), ("cfm_load", "cfm_load_exp"), ("eta", "eta_exp"), ("rpm", "rpm_exp"), ("dp_op_from_hose_got", "dp_op_exp"))) and row["lam_agree"]
    b2["cases"].append(row)
lo = (BUDGET / 1.68) ** (1 / 3); hi = min(1.0, lo * 2 ** (1 / 3))
b2["rederate_scale"] = {"got": rederate_scale(2000 * lo, 2000, BUDGET, 2 * BUDGET), "exp": hi / lo}
b2["rederate_scale"]["agree"] = agree(b2["rederate_scale"]["got"], b2["rederate_scale"]["exp"])
b2["rederate_down"] = {"got": rederate_scale(2000.0, 2000, 1.68, BUDGET), "exp": (BUDGET / 1.68) ** (1 / 3)}
b2["rederate_down"]["agree"] = agree(b2["rederate_down"]["got"], b2["rederate_down"]["exp"])
R["B2"] = b2
# ---------------- B3 bem_prescreen ----------------
import optuna; optuna.logging.set_verbosity(optuna.logging.WARNING)
from fansim.optimize.search_space import suggest_params
from fansim.optimize.study import optimizer_max_tip_radius
from fansim.fan_spec import mount_min_hub_radius
from fansim.geometry.blade import validate_blade_params
from fansim.fan_bem import pq_curve, operating_point
lo_h = mount_min_hub_radius(spec); hub_rng = (lo_h, max(lo_h + 0.1, spec.hub_dia_mm[1] / 2)); mtip = optimizer_max_tip_radius(spec)
st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=14002)); designs = []; tries = 0
while len(designs) < 5 and tries < 200:
    tr = st.ask(); tries += 1
    p = suggest_params(tr, space="guided", hub_radius_range=hub_rng, max_tip_radius=mtip)
    try: validate_blade_params(p)
    except ValueError: continue
    designs.append((tr.number, p))
b3 = {"tries": tries, "designs": []}
for num, p in designs:
    U = 2000 * 2 * math.pi / 60 * p.tip_radius / 1000
    for model in ("euler", "axial_force"):
        c = pq_curve(p, 2000.0, pressure_model=model); bad = []
        for pt in c.points:
            if pt.efficiency > 1.0 + 1e-9: bad.append(("eta>1", pt.flow_cfm, pt.efficiency))
            if pt.flow_m3s * pt.dp_static_pa > pt.power_w + 0.005 + 0.005 * pt.flow_m3s: bad.append(("Q*dp>P", pt.flow_cfm, pt.flow_m3s * pt.dp_static_pa, pt.power_w))
            if pt.dp_static_pa > RHO * U * U: bad.append(("dp>rhoU2", pt.flow_cfm, pt.dp_static_pa))
        fp = operating_point(p, 2000.0, c.free_delivery_cfm / CFM, pressure_model=model)
        tol = max(0.01 * abs(c.shutoff_dp_pa), 0.05)
        # sign bracket around the reported free delivery
        br = None
        for a, b in zip(c.points, c.points[1:]):
            if a.flow_cfm <= c.free_delivery_cfm <= b.flow_cfm: br = (a.dp_static_pa, b.dp_static_pa)
        b3["designs"].append({"trial": num, "model": model, "n_blades": p.n_blades, "free_cfm": c.free_delivery_cfm, "free_status": c.free_status,
            "shutoff": c.shutoff_dp_pa, "peak_eff": c.peak_efficiency, "dp_at_free": fp.dp_static_pa, "free_tol": tol,
            "free_ok": c.free_status == "crossed" and abs(fp.dp_static_pa) <= tol, "bracket": br, "bound_violations": bad,
            "max_QdP_over_P": max((pt.flow_m3s * pt.dp_static_pa / pt.power_w) for pt in c.points if pt.power_w > 0)})
R["B3"] = b3
# ---------------- B4 wrapped section ----------------
r, c, beta, m, pp, tt, lean, skew = 40.0, 30.0, 30.0, 0.04, 0.4, 0.12, 20.0, 5.0
def my_naca(n=4000):
    th = np.linspace(0, np.pi, n); x = 0.5 * (1 - np.cos(th))
    yt = 5 * tt * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1036 * x**4)
    yc = np.where(x < pp, m / pp**2 * (2 * pp * x - x**2), m / (1 - pp)**2 * ((1 - 2 * pp) + 2 * pp * x - x**2))
    dy = np.where(x < pp, 2 * m / pp**2 * (pp - x), 2 * m / (1 - pp)**2 * (pp - x)); ang = np.arctan(dy)
    xu, yu = x - yt * np.sin(ang), yc + yt * np.cos(ang); xl, yl = x + yt * np.sin(ang), yc - yt * np.cos(ang)
    return np.concatenate([xu[::-1], xl[1:]]), np.concatenate([yu[::-1], yl[1:]])
# expected placement (my derivation): chordwise a from mid-chord, thickness b; LE must lead (+t) and sit upstream (+z)
# for a rotor spinning +theta that pumps -Z; t = a' cos(beta) - b sin(beta) + skew with a' = -(x-0.5)c (LE at +a');
# z = a' sin(beta) + b cos(beta). Wrap: theta = lean + t/r, so the unrolled section (s = r(theta-lean), z) is this 2-D shape.
X, Y = my_naca(); bb = math.radians(beta)
A = -(X - 0.5) * c; Bv = Y * c
exp_s = A * math.cos(bb) - Bv * math.sin(bb) + skew; exp_z = A * math.sin(bb) + Bv * math.cos(bb)
R["B4_expected_first"] = {"chord": c, "stagger": beta, "camber": m, "LE_exp_sz": [float(exp_s[np.argmin(X)]), float(exp_z[np.argmin(X)])]}
from fansim.geometry.blade import _section_loop
from fansim.geometry.features import Features
xp, pts = _section_loop(r=r, r_frac=0.5, chord=c, stagger_deg=beta, thickness=tt, max_camber=m, camber_pos=pp, sweep=0.0,
                        skew=skew, le_sweep=0.0, lean_deg=lean, n_chord=80, features=Features(), wrap=True)
P = np.array([[v.x, v.y, v.z] for v in pts]); rho_ = np.hypot(P[:, 0], P[:, 1])
s = r * (np.arctan2(P[:, 1], P[:, 0]) - math.radians(lean)); z = P[:, 2]
poly = np.column_stack([exp_s, exp_z]); d = np.array([np.min(np.hypot(poly[:, 0] - a, poly[:, 1] - b)) for a, b in zip(s, z)])
def est(s, z):
    pts2 = np.column_stack([s, z]); te = 0.5 * (pts2[0] + pts2[-1])
    le = pts2[np.argmax(np.hypot(*(pts2 - te).T))]; ch = np.hypot(*(le - te)); u = (le - te) / ch; nrm = np.array([-u[1], u[0]])
    xi = (pts2 - te) @ u; eta = (pts2 - te) @ nrm; ile = int(np.argmax(xi))
    s1, s2 = (xi[:ile + 1], eta[:ile + 1]), (xi[ile:], eta[ile:])
    g = np.linspace(0.02 * ch, 0.98 * ch, 400)
    e1 = np.interp(g, *(arr[np.argsort(s1[0])] for arr in s1)); e2 = np.interp(g, *(arr[np.argsort(s2[0])] for arr in s2))
    camber = np.max(np.abs(0.5 * (e1 + e2))) / ch
    stag = math.degrees(math.atan2(abs(le[1] - te[1]), abs(le[0] - te[0])))
    return ch, stag, camber, le, te
ch, stg, cam, le, te = est(s, z); chx, stx, cmx, _, _ = est(exp_s, exp_z)
R["B4"] = {"max_radius_err_mm": float(np.max(np.abs(rho_ - r))), "a_ok": bool(np.max(np.abs(rho_ - r)) <= 1e-6),
           "max_shape_dev_mm": float(d.max()), "shape_tol_mm": max(0.001, 0.01 * tt * c), "b_ok": bool(d.max() <= max(0.001, 0.01 * tt * c)),
           "est_code": [ch, stg, cam], "est_mine_on_my_naca": [chx, stx, cmx],
           "c_ok": bool(agree(ch, c) and agree(stg, beta) and agree(cam, m)),
           "LE_sz": le.tolist(), "TE_sz": te.tolist(), "n_pts": len(P)}
# side check: which surface faces +Z? mean z of upper-surface (b>0) points vs lower
up = np.array([pt for pt, yy in zip(np.column_stack([s, z]), np.r_[np.ones(len(s))]) ])
R["B4"]["LE_leads_plus_theta"] = bool(le[0] > te[0]); R["B4"]["LE_upstream_plus_z"] = bool(le[1] > te[1])
json.dump(R, open(OUT, "w"), indent=1, default=float); print("DONE")
