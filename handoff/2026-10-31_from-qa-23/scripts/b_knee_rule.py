"""R23 B: score rule R23-KNEE (PREREG_R23 @0006f9b) on A12x25 Stock, lt120, FAN-01. No CFD run.
Inputs typed from repo docs (cited per row) + b_bem.json (pq_curve, no CFD). Cybenetics-derived A12x25 references are
used only as % errors (report terms unclear: table not stored)."""
import json, sys, time
t0 = time.monotonic()
bem = json.load(open(sys.argv[1]))
SH = {"a12x25": bem["a12x25_stock"]["euler"]["shutoff_dp_pa"], "lt120": bem["lt120_validation_params"]["euler"]["shutoff_dp_pa"], "fan01": None}
SH_AF = {"a12x25": bem["a12x25_stock"]["axial_force"]["shutoff_dp_pa"], "lt120": bem["lt120_validation_params"]["axial_force"]["shutoff_dp_pa"], "fan01": None}
# fan, P, Q0 (free CFD, None if not run), Q1, converged, err_pct (None = no reference), bistable, source
C = [
 ("a12x25", 5.0, 59.8, 52.5, True, +8.9, False, "audit-02 s4 (close-ref STL); ref Cybenetics 100% PWM interp 48.2 CFM"),
 ("a12x25", 10.0, 59.8, 41.0, True, +1.9, False, "audit-02 s4; ref Cybenetics interp 40.2 CFM"),
 ("a12x25", 15.0, 59.8, 26.8, False, +10.3, False, "audit-02 s4: unconverged near stall"),
 ("a12x25", 20.0, 59.8, 2.2, False, -56.0, False, "audit-02 s4: unconverged near stall"),
 ("lt120", 6.85, None, 89.6, True, +6.7, False, "2026-10-18 lt120 prereg, 5.8 mm (6.2 mm: 92.0, +9.5 %)"),
 ("lt120", 13.71, None, 74.7, True, +24.5, False, "2026-10-18, 5.8 mm (6.2 mm: 76.2, +27.0 %); tip-gap audit G3, not monotone"),
 ("fan01", 7.0, None, 2.131, True, +2.6, False, "fan01_report.md"),
 ("fan01", 64.0, None, 1.859, True, +3.1, False, "fan01_report.md"),
 ("fan01", 126.0, None, 1.163, False, -17.0, False, "fan01_report.md: osc 28 %"),
 ("fan01", 135.0, None, 1.062, False, None, False, "fan01_report.md: osc 27 %, measured multi-valued"),
 ("fan01", 205.0, None, 0.025, False, None, False, "fan01_report.md: collapse, osc 362 %"),
 ("fan01", 253.0, None, -0.325, False, None, False, "fan01_report.md: reversed, osc 81 %"),
]
# exploratory Q0 proxies (NOT the prereg rule): lt120 BEM free delivery (euler, CFM); FAN-01 7 Pa CFD point (m3/s)
Q0_PROXY = {"lt120": bem["lt120_validation_params"]["euler"]["free_delivery_cfm"], "fan01": 2.131}
def label(conv, err, bist):
    if not conv or bist: return "bad"
    if err is None: return "unlabelled"
    a = abs(err)
    return "good" if a <= 10 else ("bad" if a > 15 else "grey")
def outcome(flag, lab):
    if lab == "bad": return "hit" if flag else "miss"
    if lab == "good": return "false flag" if flag else "clear"
    return lab
rows = []; counts = {k: {} for k in ("K1", "K2", "K3", "OR", "K3_axial_force_expl", "OR_expl_Q0proxy_AF")}
for fan, P, q0, q1, conv, err, bist, src in C:
    lab = label(conv, err, bist)
    k1 = not conv
    phi = (q1 / q0) if (q0 and conv) else None
    k2 = phi is not None and phi <= 0.60
    k3 = SH[fan] is not None and P >= 0.60 * SH[fan]
    orr = k1 or k2 or k3
    # exploratory variants
    k3af = SH_AF[fan] is not None and P >= 0.60 * SH_AF[fan]
    q0x = q0 or Q0_PROXY.get(fan)
    phix = q1 / q0x if q0x else None
    k2x = phix is not None and phix <= 0.60
    orx = k1 or k2x or k3af
    r = {"fan": fan, "P_pa": P, "Q0": q0, "Q1": q1, "converged": conv, "err_pct": err, "label": lab,
         "phi": None if phi is None else round(phi, 3), "phi_expl_any_Q1": None if not q0x else round(q1 / q0x, 3),
         "K1": k1, "K2": k2, "K3": k3, "P_over_shutoff_euler": None if SH[fan] is None else round(P / SH[fan], 3),
         "OR": orr, "outcome_OR": outcome(orr, lab),
         "K3_axial_force_expl": k3af, "OR_expl_Q0proxy_AF": orx, "source": src}
    rows.append(r)
    for k, f in (("K1", k1), ("K2", k2), ("K3", k3), ("OR", orr), ("K3_axial_force_expl", k3af), ("OR_expl_Q0proxy_AF", orx)):
        o = outcome(f, lab); counts[k][o] = counts[k].get(o, 0) + 1
# false-flag risk on the stable branch: share of the published curve from knee to free delivery flagged by K2/K3
risk = {
 "lt120": {"stable_branch": "60-84 CFM (13.71-6.85 Pa; no measured free point)",
           "K3_euler_threshold_pa": round(0.6 * SH["lt120"], 2), "K3_af_threshold_pa": round(0.6 * SH_AF["lt120"], 2),
           "K3_flags_share": 0.0, "K2": "n/a (no CFD free point); with BEM-free proxy 93.7 CFM: phi>=0.64 on 60-84 CFM -> 0 %"},
 "a12x25": {"stable_branch": "approx 24-56 CFM (Cybenetics, 15.3 Pa to free); K3 euler threshold %.1f Pa > 15.3 -> 0 %%; axial_force %.1f Pa -> flags P>=13.8 Pa, i.e. approx 24-31 CFM of the branch (~20 %%)" % (0.6 * SH["a12x25"], 0.6 * SH_AF["a12x25"]),
            "K2": "phi<=0.60 means Q1<=35.9 CFM -> branch 24-35.9 CFM flagged (~37 % of 24-56 CFM) using CFD Q0 59.8"},
 "fan01": {"K3": "n/a (no BladeParams)", "K2": "n/a (no CFD free point); exploratory Q0=2.131 (7 Pa): phi<=0.6 -> Q1<=1.28 m3/s, measured stable branch ~1.4-2.1 -> 0 %"},
}
out = {"rows": rows, "counts": counts, "bem_shutoff_euler": SH, "bem_shutoff_axial_force": SH_AF, "risk": risk,
       "worth_landing": counts["OR"].get("miss", 0) == 0 and counts["OR"].get("false flag", 0) <= 1,
       "elapsed_s": round(time.monotonic() - t0, 3)}
json.dump(out, open(sys.argv[2], "w"), indent=1)
for r in rows:
    print(f"{r['fan']:7s} {r['P_pa']:6.2f} conv={str(r['converged']):5s} err={r['err_pct']} lab={r['label']:10s} phi={r['phi']} phiX={r['phi_expl_any_Q1']} P/sh={r['P_over_shutoff_euler']} K1={r['K1']:d} K2={r['K2']:d} K3={r['K3']:d} OR={r['OR']:d} -> {r['outcome_OR']} | K3af={r['K3_axial_force_expl']:d} ORx={r['OR_expl_Q0proxy_AF']:d}")
print(json.dumps(out["counts"])); print("worth_landing", out["worth_landing"])
