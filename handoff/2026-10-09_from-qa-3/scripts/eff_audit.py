"""Round-4 request 2: Stock efficiency, BEM direct vs BEM-by-CFD-procedure vs CFD scored. Run from r4_axial root."""
import json, os, sys
sys.path.insert(0, os.getcwd())
import fansim.fan_bem as FB
from fansim.geometry.config import load_blade_params
from fansim.fan_spec import A12X25
from fansim.cfd.domain import remaining_tip_gap_mm
from fansim.optimize.system_curve import (probe_flow_cfm, intersect_fan_line, k_from_pa, score_operating_point, CFM_PER_M3S)
from fansim.optimize.print_penalty import print_k_eta_for_thickness, tip_section_thickness, PRINT_K_CFM
from fansim.optimize.presets import resolve_load
LOAD, _ = resolve_load(preset="case"); RPM = 2000.0; BUD = A12X25.max_shaft_power_w_leeway
bp = load_blade_params("config/problems/a12x25_reference.yaml")
gap = max(remaining_tip_gap_mm(bp, float(A12X25.tip_dia_mm[1])), 0.0)
k_eta = print_k_eta_for_thickness(tip_section_thickness(bp))
sv = json.load(open("/workspace/fansim/research/proto/r4/scored_vs_raw.json"))["stock"]
lam_cfd = sv["implied_derate"]
CFD = dict(raw_free=54.794, raw_probe=41.75, scored_eff=17.888, eta_op_raw=17.888 / k_eta)
op = lambda m, cfm: FB.operating_point(bp, RPM, cfm / CFM_PER_M3S, tip_gap_mm=gap, pressure_model=m)
res = {"k_eta": k_eta, "tip_gap": gap, "budget_w": BUD, "cfd": CFD, "cfd_implied_derate": lam_cfd}
for m in ("euler", "axial_force"):
    c = FB.pq_curve(bp, RPM, tip_gap_mm=gap, pressure_model=m)
    q0 = float(c.free_delivery_cfm); q1 = probe_flow_cfm(c, LOAD)
    q_op, p_op = intersect_fan_line(q0, q1, LOAD, k_from_pa(LOAD))
    a_direct = op(m, q_op).efficiency                               # (a) screen definition, pre-print
    e_free, e_probe = op(m, q0).efficiency, op(m, q1).efficiency
    shaft = max(op(m, q0).power_w, op(m, q1).power_w)
    lam = min(1.0, (BUD / shaft) ** (1 / 3))
    sop = score_operating_point(q0 * lam, q1 * lam, LOAD * lam * lam, e_free, e_probe, LOAD, p_free_pa=0.0)
    b_proc = sop.eta                                                # (b) CFD procedure on BEM numbers, pre-print
    # BEM at the CFD's own raw points (rated rpm): pressure and shaft power the BEM predicts there
    at_probe = op(m, CFD["raw_probe"]); at_free = op(m, CFD["raw_free"])
    res[m] = dict(q_free=q0, q_probe=q1, q_op=q_op, p_op=p_op, eta_direct=a_direct, eta_direct_scored=a_direct * k_eta,
                  eta_free=e_free, eta_probe=e_probe, shaft_max_w=shaft, derate=lam, t=(sop.q_op_cfm - q0 * lam) / (q1 * lam - q0 * lam),
                  eta_cfdproc=b_proc, eta_cfdproc_scored=b_proc * k_eta, peak_eff=float(c.peak_efficiency),
                  at_cfd_probe=dict(dp=at_probe.dp_static_pa, shaft_w=at_probe.power_w, eta=at_probe.efficiency),
                  at_cfd_free=dict(dp=at_free.dp_static_pa, shaft_w=at_free.power_w, eta=at_free.efficiency))
    r = res[m]
    print(f"{m}: free {q0:.2f} probe {q1:.2f} op {q_op:.2f} | eta direct {100*a_direct:.2f} (scored {100*a_direct*k_eta:.2f}) | "
          f"eta_free {100*e_free:.2f} eta_probe {100*e_probe:.2f} derate {lam:.4f} t {r['t']:.3f} -> CFD-procedure {100*b_proc:.2f} (scored {100*b_proc*k_eta:.2f}) | "
          f"at CFD probe 41.75 CFM: dp {at_probe.dp_static_pa:.2f} Pa shaft {at_probe.power_w:.3f} W eta {100*at_probe.efficiency:.1f} | at CFD free 54.79: dp {at_free.dp_static_pa:.2f} shaft {at_free.power_w:.3f}")
json.dump(res, open("/workspace/fansim/research/proto/r4/eff_audit.json", "w"), indent=1, default=float)
