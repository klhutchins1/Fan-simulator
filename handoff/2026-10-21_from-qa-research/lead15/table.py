"""Lead 15: tolerance table from results.json, with the motor cup carved out of the hub volume (the builder's
build_impeller_parts hub is solid; the printed hub has the a12x25 cup 37.25 x 13 mm removed). Mass range:
low = blades solid + carved hub at 40 % infill; high = everything solid. U_per uses the mid mass."""
import csv, json, math, sys
d = json.load(open(sys.argv[1])); K = d["K"]; rho = 1270e-6  # g/mm3 PETG
cup = math.pi * (37.25 / 2) ** 2 * 13.0
rows = []
for r in d["rotors"]:
    fan = not r["rotor"].startswith("prop")
    hub = r["hub_vol_mm3"] - (cup if fan else 0.0)
    lo = (r["blade_vol_mm3"] + 0.4 * hub) * rho; hi = (r["blade_vol_mm3"] + hub) * rho; mid = 0.5 * (lo + hi)
    row = dict(rotor=r["rotor"], rpm=r["rpm"], mass_g_low=round(lo, 1), mass_g_high=round(hi, 1), mass_g_used=round(mid, 1))
    for G in (2.5, 6.3):
        U = K * G * mid / 1000 / r["rpm"]
        row[f"e_per_um_G{G}"] = round(K * G / r["rpm"], 2)
        row[f"U_per_gmm_G{G}"] = round(U, 3)
        row[f"blob_mg_at_0.9R_G{G}"] = round(1000 * U / (0.9 * r["tip_radius_mm"]), 2)
    row["typical_U_1pct_blade_scatter_gmm"] = r["exp_U_from_1pct_blade_scatter_gmm"]
    row["typical_U_50um_seat_offset_gmm"] = round(mid * 0.05, 3)
    rows.append(row)
with open(sys.argv[2], "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows: print(r)
