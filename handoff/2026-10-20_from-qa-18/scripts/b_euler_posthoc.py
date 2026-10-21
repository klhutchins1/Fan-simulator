"""QA r18 B post-hoc (report only, not pre-registered): ideal Euler pressure rise of both rotors at mid-span, generic 4 % camber + Carter."""
import json, math, sys
r = json.load(open(sys.argv[1])); CHI_TE = r["chi_TE"]; TH = r["theta"]; out = {}
for conv in "PX":
    pick = lambda rot: [x for x in r["rows"] if x["conv"] == conv and x["kc"] == 1 and x["ks"] == 1 and x["rotor"] == rot and x["station"] == "mid"][0]
    row = pick("rear"); fm = pick("front")
    sw = [s for s in r["swirl"] if s["conv"] == conv and s["kc"] == 1 and s["ks"] == 1][0]
    b2p = row["gamma_axis"] - CHI_TE; m = 0.23 * 0.64 + b2p / 500; dev = m * TH / math.sqrt(1.17); b2 = b2p + dev
    wu2 = row["c_ax"] * math.tan(math.radians(b2)); wu1 = row["U"] + row["cu_in"]; dP = 1.2 * row["U"] * (wu1 - wu2)
    out[conv] = dict(front_dP_ideal_Pa=sw["dP_euler_front_mid"], rear_dP_ideal_Pa=dP, total_ideal_Pa=sw["dP_euler_front_mid"] + dP,
                     measured_total_Pa=510.0, rear_exit_cu=wu2 - row["U"], naca_m_for_zero_LE_incidence_front_mid=0.2 * math.tan(math.radians(fm["i_chord"])) )
json.dump(out, open(sys.argv[2], "w"), indent=1); print(json.dumps(out, indent=1))
