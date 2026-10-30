"""QA r22 C (PREREG_R22 715891f): arithmetic only. Evaluates the formulas read from scripts/prop_section_2d.py
write_case (476-483: a = radians(alpha); U = u*(cos a, sin a, 0); liftDir = (-sin a, cos a, 0); dragDir = (cos a, sin a, 0))
and the bookkeeping rules; plus the 'fixed liftDir' what-if on Ladson values. Does not import or run the script.
Usage: python3 c_alpha_table.py <out.csv>"""
import csv, math, sys
LADSON = {0: (0.0, 0.00808), 5: (0.537, 0.0085), 10: (1.063, 0.0120)}  # Cl, Cd (Cd 5/10 deg Ladson-level, report-only)
rows = []
for al in (0, 5, 10):
    a = math.radians(al); u = 1.0
    U = (u * math.cos(a), u * math.sin(a)); L = (-math.sin(a), math.cos(a)); D = (math.cos(a), math.sin(a))
    eff = math.degrees(math.atan2(U[1], U[0]))  # chord along +x, geometry not rotated (mesh built at 0 deg, copied)
    par = abs(D[0] * U[1] - D[1] * U[0]) < 1e-12 and D[0] * U[0] + D[1] * U[1] > 0
    perp = abs(L[0] * D[0] + L[1] * D[1]) < 1e-12
    suction = L[0] * -U[1] + L[1] * U[0] > 0  # liftDir = U rotated +90 deg (toward +y, suction side at +alpha)
    cl, cd = LADSON[al]
    fixed = cl * math.cos(a) + cd * math.sin(a)  # what-if: liftDir left at (0,1,0) while U rotated
    rows.append(dict(alpha_deg=al, U=f"({U[0]:.6f} {U[1]:.6f} 0)", liftDir=f"({L[0]:.6f} {L[1]:.6f} 0)",
                     dragDir=f"({D[0]:.6f} {D[1]:.6f} 0)", alpha_U=al, alpha_liftDir=al, alpha_dragDir=al, geometry_alpha=0,
                     effective_alpha=round(eff, 6), dragDir_par_U=par, liftDir_perp_dragDir=perp, lift_suction_side=suction,
                     consistent=par and perp and suction and abs(eff - al) <= 0.01,
                     whatif_fixed_liftDir_Cl_err_pct=round(100 * (fixed / cl - 1), 2) if cl else ""))
w = csv.DictWriter(open(sys.argv[1], "w", newline=""), fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows: print(r)
