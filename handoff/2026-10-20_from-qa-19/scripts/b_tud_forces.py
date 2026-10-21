"""QA r19 B (PREREG_R19 cab2825): digitise TUD benchmark Figs 19-20 'Measurements' vector polylines (Casalino et al. 2021, CC BY 4.0).
Usage: python b_tud_forces.py <pdf> <out.json>"""
import json, sys
import numpy as np, pdfplumber
# Axis labels read "C_T x 10^2" and "C_Q x 10^3" (400-dpi crop). The paper's BEMT section defines C_T = T/(rho Omega^2 pi R^4) and
# C_Q = Q/(rho Omega^2 pi R^5) (text extraction garbles Omega^2 as "2"). Converted here to the propeller convention:
# C_T,prop = T/(rho n^2 D^4) = C_T,paper * pi^3/4 ; C_Q,prop = Q/(rho n^2 D^5) = C_Q,paper * pi^3/8 ; C_P = 2 pi C_Q,prop.
PI3_4 = np.pi ** 3 / 4.0; PI3_8 = np.pi ** 3 / 8.0
p = pdfplumber.open(sys.argv[1]).pages[12]
BLK = [l for l in p.lines if str(l.get("stroking_color")) == "0.0"]
MEAS = [c for c in p.curves if str(c.get("stroking_color")).startswith("(0.58") and len(c["pts"]) == 9]
MEAS.sort(key=lambda c: c["top"])
out = {}
for k, (name, ytop, ybot, y0, dy, scale) in enumerate([("CT", 60, 180, -0.2, 0.2, 0.01 * PI3_4), ("CQ", 215, 330, 0.0, 0.2, 0.001 * PI3_8)]):
    xt = sorted({round(l["x0"], 2) for l in BLK if abs(l["x0"] - l["x1"]) < 1e-6 and ytop < l["top"] < ybot and l["bottom"] > ybot - 10})
    yt = sorted({round(l["top"], 2) for l in BLK if abs(l["top"] - l["bottom"]) < 1e-6 and ytop < l["top"] < ybot and l["x0"] < 100}, reverse=True)
    xv = np.arange(len(xt)) * 0.1; yv = y0 + np.arange(len(yt)) * dy
    ax = np.polyfit(xt, xv, 1); ay = np.polyfit(yt, yv, 1)
    rx = float(np.max(np.abs(np.polyval(ax, xt) - xv)) / (xv[-1] - xv[0])); ry = float(np.max(np.abs(np.polyval(ay, yt) - yv)) / (yv[-1] - yv[0]))
    lw = float(MEAS[k].get("linewidth", 0.44)); u_y = (lw / 2) * abs(ay[0]) + ry * (yv[-1] - yv[0]); u_x = (lw / 2) * abs(ax[0]) + rx * 0.8
    pts = [(float(np.polyval(ax, x)), float(np.polyval(ay, y)) * scale) for x, y in MEAS[k]["pts"]]
    out[name] = dict(xticks=xt, yticks=yt, resid_x_frac=rx, resid_y_frac=ry, u_J=u_x, u_val=u_y * scale, linewidth=lw,
                     points=[dict(J=j, val=v) for j, v in pts])
    print(name, "ticks", len(xt), len(yt), "resid %.2e %.2e" % (rx, ry), "u", round(u_x, 4), "%.2e" % (u_y * scale))
    for j, v in pts: print("  J %.4f  %s %.5f" % (j, name, v))
out["CP"] = [dict(J=a["J"], val=2 * np.pi * a["val"]) for a in out["CQ"]["points"]]
out["B_cal"] = all(out[n]["resid_x_frac"] <= 0.005 and out[n]["resid_y_frac"] <= 0.005 for n in ("CT", "CQ"))
out["J_match_max"] = max(abs(a["J"] - b["J"]) for a, b in zip(out["CT"]["points"], out["CQ"]["points"]))
out["convention"] = "values are propeller convention (rho n^2 D^4 / rho n^2 D^5); paper convention = value / (pi^3/4) for C_T, / (pi^3/8) for C_Q"
rho = 1.225; n = 5000 / 60; D = 0.3
out["sanity_dimensional_J0"] = dict(T_N=out["CT"]["points"][0]["val"] * rho * n**2 * D**4, Q_Nm=out["CQ"]["points"][0]["val"] * rho * n**2 * D**5,
                                    load_cell_cap_N=22.2, torque_cell_cap_Nm=0.18)
print(out["sanity_dimensional_J0"])
json.dump(out, open(sys.argv[2], "w"), indent=1); print("B_cal", out["B_cal"], "J_match_max", out["J_match_max"])
