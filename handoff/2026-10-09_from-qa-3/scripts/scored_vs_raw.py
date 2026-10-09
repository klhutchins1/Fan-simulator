"""Round-4 request 3: hand recompute of scored_free / scored_load / scored_eff for stock, t9005, bem_9504
from cfd_designs.csv raw columns + documented factors. Run from the r4_axial clone root."""
import csv, json, math, os, sys
sys.path.insert(0, os.getcwd())
from fansim.geometry.config import load_blade_params
from fansim.optimize.search_space import blade_from_flat
from fansim.optimize.print_penalty import PRINT_K_CFM, print_k_eta_for_thickness, tip_section_thickness
from fansim.structural.deflection import tip_deflection_mm
from fansim.cfd.domain import remaining_tip_gap_mm
from fansim.fan_spec import A12X25
from fansim.optimize.system_curve import k_from_pa, intersect_fan_line, CFM_PER_M3S
from fansim.optimize.presets import resolve_load
LOAD, _ = resolve_load(preset="case")
BUDGET = A12X25.max_shaft_power_w_leeway
rows = {r["design_id"]: r for r in csv.DictReader(open("/workspace/fansim/handoff_in/2026-10-09_to-qa-2/cfd_designs.csv"))}
out = {}
for did in ("stock", "t9005", "bem_9504"):
    r = rows[did]
    bp = load_blade_params("config/problems/a12x25_reference.yaml") if r["geometry"] == "stock" else blade_from_flat(json.loads(r["flat"]))
    t_tip = tip_section_thickness(bp); k_eta = print_k_eta_for_thickness(t_tip)
    gap = remaining_tip_gap_mm(bp, float(A12X25.tip_dia_mm[1]))
    defl = tip_deflection_mm(bp, material="PETG", load_pa=float(LOAD))
    k_fsi = max(0.90, 1.0 - 0.5 * min(defl / gap, 1.0)) if gap > 0 else 1.0
    raw_f, raw_l = float(r["cfd_free_cfm"]), float(r["cfd_load_cfm"])
    sf, sl, se = float(r["scored_free"]), float(r["scored_load"]), float(r["scored_eff"])
    lam = sf / (raw_f * PRINT_K_CFM * k_fsi)                 # implied motor derate
    shaft_rated = BUDGET / lam ** 3 if lam < 0.9999 else None  # implied CFD shaft power at rated rpm
    # hose intersection with documented derate scaling; p_free unknown -> try 0 and back it out
    k = k_from_pa(LOAD); q0, q1, p1 = raw_f * lam, raw_l * lam, LOAD * lam * lam
    q_op0, p_op0 = intersect_fan_line(q0, q1, p1, k, p_free_pa=0.0)
    hand_load_p0 = q_op0 * PRINT_K_CFM * k_fsi
    target = sl / (PRINT_K_CFM * k_fsi)                        # q_op before print
    # implied p_free: fan line through (q0,pf),(q1,p1) must pass (target, k*target^2)
    Q0, Q1, Qt = q0 / CFM_PER_M3S, q1 / CFM_PER_M3S, target / CFM_PER_M3S
    pt = k * Qt * Qt; tpar = (Qt - Q0) / (Q1 - Q0)            # P(Q)=pf+(p1-pf)*t  -> pf = (pt - p1 t)/(1-t)
    pf_implied = (pt - p1 * tpar) / (1 - tpar)
    out[did] = dict(tip_tc=t_tip, k_eta=k_eta, tip_gap_mm=gap, tip_defl_mm=defl, k_fsi=k_fsi, k_cfm=PRINT_K_CFM * k_fsi,
                    implied_derate=lam, implied_actual_rpm=2000 * lam, implied_shaft_rated_w=shaft_rated, budget_w=BUDGET,
                    hand_free_check=raw_f * lam * PRINT_K_CFM * k_fsi, scored_free=sf,
                    hand_load_if_pfree0=hand_load_p0, scored_load=sl, implied_q_op_preprint=target, implied_p_free_rated_pa=pf_implied / lam ** 2,
                    implied_t=tpar, eta_op_raw_pct=se / k_eta, scored_eff=se,
                    probe_air_power_w=raw_l / CFM_PER_M3S * LOAD)
    print(did, {k_: (round(v, 4) if isinstance(v, float) else v) for k_, v in out[did].items()})
json.dump(out, open("/workspace/fansim/research/proto/r4/scored_vs_raw.json", "w"), indent=1)
