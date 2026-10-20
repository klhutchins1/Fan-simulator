"""QA r17 Task B: uncertainties, B-rep (method 2 manual reads vs method 1), B-text, CSVs. Usage: python b_finalise.py"""
import csv, json, math
B = "/workspace/fansim/qa/r17/b"; O = "/workspace/fansim/repo-r17/docs/qa/r17"
S7 = json.load(open(f"{B}/shig_fig7_m1.json")); S8 = json.load(open(f"{B}/shig_fig8_m1.json")); E = json.load(open(f"{B}/epj_m1.json"))
# method 2: manual reads from calibrated zoom crops (b_overlay.py), recorded by hand in r17 (see note)
M2 = {
 ("shig7", "exp_total"): [(0.200, 405), (0.250, 389.3), (0.550, 508), (0.7997, 414.3), (0.8498, 367.3), (0.9006, 308), (1.0830, -0.8)],
 ("shig7", "cal_total"): [(0.220, 411.5), (0.3847, 449.5), (0.550, 499.7), (0.7153, 470.7), (0.8796, 313.9)],
 ("shig7", "cal_rear"): [(0.2222, 251.7), (0.3885, 339.8), (0.552, 386.0), (0.715, 376.7), (0.8847, 341.4)],
 ("shig7", "cal_front"): [(0.2216, 127.3), (0.3866, 84.5), (0.550, 71.8), (0.716, 57.4), (0.881, -49.8)],
 ("shig8", "cal_rear"): [(0.3846, 53.2), (0.5513, 64.8), (0.7167, 77.6), (0.8795, 73.9)],
 ("shig8", "cal_total"): [(0.3846, 39.4), (0.5513, 46.6), (0.7154, 41.3), (0.8795, 17.5)],
 ("shig8", "cal_front"): [(0.3846, 21.3), (0.5513, 15.3), (0.7167, -3.3), (0.8795, -36.6)],
 ("fig6", "B_const_rpm_9000"): [(13.1, 414.5), (30.8, 419.7), (59.3, 426.7), (85.2, 429.8), (119.8, 420.6), (144.6, 403.6), (155.3, 391.3), (192.6, 349.6), (225.9, 301.3), (260.2, 243.0), (278.1, 208.7)],
 ("fig6", "A_const_current_9000"): [(6.0, 436.3), (31.5, 439.3), (147.9, 393.0)],
 ("fig7", "plastic_6000"): [(22.7, 183.7), (33.3, 183.7), (72.9, 181.5), (118.9, 161.1), (166.8, 111.6)],
 ("fig7", "plastic_11000"): [(164.3, 610.3), (236.1, 530.6), (265.1, 483.8), (308.0, 388.6), (332.0, 331.3)],
 ("fig8", "plastic_wheel0_9000"): [(17.3, 413.2), (34.7, 420.5), (59.9, 424.6), (86.3, 425.5), (110.2, 421.4)],
}
# manual-only points (method 1 merged the overlapping markers at Q 0.22 in Shigemitsu Fig 8)
MANUAL_ONLY = {("shig8", "cal_rear"): [(0.2202, 31.9)], ("shig8", "cal_total"): [(0.220, 28.6)]}
rows = []
def add(paper, fig, curve, Q, y, uQ, uy, qunit, yunit, method, src_note, rpm=""):
    rows.append(dict(paper=paper, figure=fig, curve=curve, rpm=rpm, Q=round(Q, 5), Q_unit=qunit, y=round(y, 3), y_unit=yunit,
                     u_Q=round(uQ, 5), u_y=round(uy, 3), method=method, note=src_note))
c7 = S7["cal"]; qpx, ppx = S7["q_per_px"], S7["pa_per_px"]
for p in S7["points"]:
    half = p.get("marker_r_px") or p["marker_w_px"] / 2.0; half = max(half, 1.57)
    uQ = math.hypot(c7["x_res_max"], half * qpx); uy = math.hypot(c7["y_res_max"], half * ppx)
    kind = "measured" if p["curve"] == "exp_total" else "CFD (paper's own ANSYS CFX URANS; not a measurement)"
    add("Shigemitsu2018", "Fig7", p["curve"], p["Q"], p["dP"], uQ, uy, "m3/min", "Pa (fan static pressure dPs)", "m1_auto_raster", kind, "15000/14000")
c8 = S8["cal"]
for p in S8["points"]:
    half = max(p["marker_w_px"] / 2.0, 1.57)
    add("Shigemitsu2018", "Fig8", p["curve"], p["Q"], p["eta"], math.hypot(c8["x_res_max"], half * S8["q_per_px"]), math.hypot(c8["y_res_max"], half * S8["pct_per_px"]),
        "m3/min", "% (static-pressure efficiency)", "m1_auto_raster", "CFD only (paper's ANSYS CFX)", "15000/14000")
for (fg, cv), pts in MANUAL_ONLY.items():
    for q, y in pts:
        add("Shigemitsu2018", "Fig8", cv, q, y, 12.5 * S8["q_per_px"], 12.5 * S8["pct_per_px"], "m3/min", "% (static-pressure efficiency)", "m2_manual_only", "overlapping markers; CFD only", "15000/14000")
RPM = {"A_const_current_9000": "9000 (constant current)", "B_const_rpm_9000": "9000", "plastic_6000": "6000", "plastic_9000": "9000", "plastic_11000": "11000", "plastic_wheel0_9000": "9000"}
for fid, F in E["figs"].items():
    c = F["cal"]; ax, ay = c["x_fit"][0], c["y_fit"][0]
    for p in F["points"]:
        h = max(p["w_pt"] / 2.0, 0.24)
        if c["logx"]:
            uQ = p["Q"] * (10 ** math.hypot(h * abs(ax), c["x_res_max"]) - 1); uy = p["dP"] * (10 ** math.hypot(h * abs(ay), c["y_res_max"]) - 1)
        else:
            uQ = math.hypot(h * abs(ax), c["x_res_max"]); uy = math.hypot(h * abs(ay), c["y_res_max"])
        add("EPJ2018_02023", fid.replace("fig", "Fig"), p["curve"], p["Q"], p["dP"], uQ, uy, "L/min", "Pa (working pressure pb)", "m1_vector_pdf",
            "measured; plastic (injection-moulded) wheel 0" if "plastic" in p["curve"] or "B_" in p["curve"] else "measured; constant current, rpm drifts (paper)", RPM[p["curve"]])
# B-rep
rep = {}; rr = []
KEY = {"shig7": ("Shigemitsu2018", "Fig7"), "shig8": ("Shigemitsu2018", "Fig8"), "fig6": ("EPJ2018_02023", "Fig6"), "fig7": ("EPJ2018_02023", "Fig7"), "fig8": ("EPJ2018_02023", "Fig8")}
for (fg, cv), pts in M2.items():
    pap, fig = KEY[fg]; cand = [r for r in rows if r["paper"] == pap and r["figure"] == fig and r["curve"] == cv and r["method"].startswith("m1")]
    ok = 0
    for q, y in pts:
        best = min(cand, key=lambda r: ((r["Q"] - q) / r["u_Q"]) ** 2 + ((r["y"] - y) / r["u_y"]) ** 2)
        dq, dy = q - best["Q"], y - best["y"]; good = abs(dq) <= 2 * best["u_Q"] and abs(dy) <= 2 * best["u_y"]; ok += good
        rr.append(dict(paper=pap, figure=fig, curve=cv, m2_Q=q, m2_y=y, m1_Q=best["Q"], m1_y=best["y"], dQ=round(dq, 5), dy=round(dy, 3), u_Q=best["u_Q"], u_y=best["u_y"], within_2u=good))
    n = len(pts); rep[f"{pap}/{fig}/{cv}"] = dict(n=n, within=ok, verdict=("PASS" if ok / n >= 0.9 else "FAIL") + ("" if n >= 5 or n == len(cand) else f" ({n} of {len(cand)} re-read; fewer than 5)"))
# Fig 7 9000 = Fig 6 B (same test, replotted): cross-figure consistency used as its re-read
f6 = [r for r in rows if r["figure"] == "Fig6" and r["curve"] == "B_const_rpm_9000"]; f7 = [r for r in rows if r["figure"] == "Fig7" and r["curve"] == "plastic_9000"]
dd = [(abs(a["Q"] - b["Q"]), abs(a["y"] - b["y"])) for a, b in zip(sorted(f6, key=lambda r: r["Q"]), sorted(f7, key=lambda r: r["Q"]))]
rep["EPJ2018_02023/Fig7/plastic_9000"] = dict(n=len(dd), max_dQ=max(d[0] for d in dd), max_dy=max(d[1] for d in dd), verdict="PASS (vs Fig6 B, same data replotted)" if all(d[0] <= 2 * f7[0]["u_Q"] and d[1] <= 2 * 9.6 for d in dd) else "FAIL")
# B-text (Shigemitsu text: max dPs 510 Pa at Qo 0.55; Qmax 1.08; CFD 500 Pa at Qo; rear ~77 % at Qo; eta_total 46.7 % at Qo)
ex = [r for r in rows if r["figure"] == "Fig7" and r["curve"] == "exp_total"]; pk = max(ex, key=lambda r: r["y"]); fd = max(ex, key=lambda r: r["Q"])
ct = [r for r in rows if r["figure"] == "Fig7" and r["curve"] == "cal_total"]; cr = [r for r in rows if r["figure"] == "Fig7" and r["curve"] == "cal_rear"]
ctq = min(ct, key=lambda r: abs(r["Q"] - 0.55)); crq = min(cr, key=lambda r: abs(r["Q"] - 0.55))
e8 = min([r for r in rows if r["figure"] == "Fig8" and r["curve"] == "cal_total"], key=lambda r: abs(r["Q"] - 0.55))
share = crq["y"] / ctq["y"]; u_share = share * math.hypot(crq["u_y"] / crq["y"], ctq["u_y"] / ctq["y"])
text = {"peak 510 Pa at 0.55": dict(dig=(pk["Q"], pk["y"]), ok=abs(pk["y"] - 510) <= 2 * pk["u_y"] and abs(pk["Q"] - 0.55) <= 2 * pk["u_Q"]),
        "max flow 1.08 m3/min": dict(dig=fd["Q"], ok=abs(fd["Q"] - 1.08) <= 2 * fd["u_Q"]),
        "CFD 500 Pa at Qo": dict(dig=ctq["y"], ok=abs(ctq["y"] - 500) <= 2 * ctq["u_y"]),
        "rear ~77 % of total at Qo (CFD)": dict(dig=share, u=u_share, ok=abs(share - 0.77) <= 2 * u_share),
        "eta_s total 46.7 % at Qo (CFD)": dict(dig=e8["y"], ok=abs(e8["y"] - 46.7) <= 2 * e8["u_y"])}
F = list(rows[0].keys())
for pap, fn in (("Shigemitsu2018", "r17-B-shigemitsu2018-digitised.csv"), ("EPJ2018_02023", "r17-B-epj2018-02023-digitised.csv")):
    with open(f"{O}/{fn}", "w", newline="") as fh:
        fh.write("# " + ("Shigemitsu T., Miyazaki T., Hirosawa S., Fukuda Y. (2018) Performance and Internal Flow of Contra-Rotating Small-Sized Cooling Fan. Open J. Fluid Dyn. 8:181-194, doi:10.4236/ojfd.2018.82013. CC BY 4.0 (statement on p.1 of the PDF). Digitised by QA r17 (grok), prereg a212b29; values are QA readings of the figures, not the authors' data."
                       if pap.startswith("Shig") else "Dvorak V., Votrubec R., Safka J., Kracik J. (2018) Experimental investigation of centrifugal fans for personal protection equipment - effect of used 3D printing technologies. EPJ Web Conf. 180:02023, doi:10.1051/epjconf/201818002023. CC BY 4.0 (statement on p.1 of the PDF). Digitised by QA r17 (grok) from the PDF's vector marker paths, prereg a212b29; values are QA readings, not the authors' data.") + "\n")
        w = csv.DictWriter(fh, fieldnames=F); w.writeheader(); w.writerows([r for r in rows if r["paper"] == pap])
with open(f"{O}/r17-B-reread-check.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rr[0].keys())); w.writeheader(); w.writerows(rr)
cal = {"Shigemitsu2018/Fig7": S7["cal"], "Shigemitsu2018/Fig8": S8["cal"], **{f"EPJ2018_02023/{k}": v["cal"] for k, v in E["figs"].items()}}
json.dump(dict(B_cal={k: v["B_cal"] for k, v in cal.items()}, cal=cal, B_rep=rep, B_text=text, n_rows=len(rows)), open(f"{B}/b_summary.json", "w"), indent=1, default=str)
print(json.dumps(dict(B_cal={k: v["B_cal"] for k, v in cal.items()}, B_rep=rep, B_text=text), indent=0, default=str))
