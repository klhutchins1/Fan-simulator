"""QA r20 B (PREREG_R20 2c4380d): Ladson TM-4074 NACA 0012 reference at Re 6e6, M 0.15, tripped (80/120/180 grit).
Tables IX/XI/XIII (Re 5.95/6.00/5.95 x10^6) as transcribed and checked against the page images; the TMR file
CLCD_Ladson_expdata.dat is the cross-check. Usage: python b_ladson.py <tmr.dat> <out.json>"""
import json, math, sys

# My transcription of TM-4074 Tables IX/XI/XIII (alpha, cd, cl) is kept box-only (outside raw data is not committed):
TABLE = {k: [tuple(r) for r in v] for k, v in json.load(open('/workspace/fansim/qa/r20_src/tm4074_tables_box_only.json')).items()}
REP = {"cl": 0.004, "cd": 0.0002}  # TM-4074 'Accuracy': repeat points at alpha 0 (normal force 0.004, drag 0.0002)


def read_tmr(path):
    z, cur = {}, None
    for l in open(path):
        if l.startswith("zone"):
            cur = l.split('"')[1]; z[cur] = []
        elif cur and l.strip() and not l[0].isalpha() and not l.startswith("#"):
            a, cl, cd = map(float, l.split()); z[cur].append((a, cd, cl))
    return z


def interp(rows, a, k):
    rows = sorted(rows)
    for (a0, *v0), (a1, *v1) in zip(rows, rows[1:]):
        if a0 <= a <= a1:
            lin = v0[k] + (v1[k] - v0[k]) * (a - a0) / (a1 - a0)
            near = v0[k] if abs(a - a0) <= abs(a1 - a) else v1[k]
            return lin, near, (a0, a1)
    raise ValueError(a)


def main(tmr, outp):
    T = read_tmr(tmr); out = {"points": [], "tmr_vs_table": []}
    for (g, rows), (tg, trows) in zip(TABLE.items(), T.items()):
        for r, t in zip(rows, trows):
            d = [abs(x - y) for x, y in zip(r, t)]
            if max(d) > 1e-9: out["tmr_vs_table"].append({"grit": g, "table": r, "tmr": t})
        assert len(rows) <= len(trows)
    for a in (0.0, 5.0, 10.0):
        for qn in ("cl", "cd"):
            per = {g: interp(rows, a, 0 if qn == "cd" else 1) for g, rows in TABLE.items()}
            lins = [v[0] for v in per.values()]; mean = sum(lins) / len(lins)
            half_range = (max(lins) - min(lins)) / 2
            interp_err = max(abs(v[0] - v[1]) for v in per.values())
            band = math.sqrt(half_range ** 2 + interp_err ** 2 + REP[qn] ** 2)
            out["points"].append({"alpha": a, "q": qn, "ref": mean, "band": band, "half_range_grit": half_range,
                "interp_lin_vs_nearest": interp_err, "repeatability": REP[qn], "band_pct": 100 * band / abs(mean) if abs(mean) > 1e-3 else None,
                "per_grit": {g: {"lin": v[0], "nearest": v[1], "bracket": v[2]} for g, v in per.items()}})
    # context: McCroskey best-fit slope (Re 6e6, M 0.15) and thin-airfoil
    sl = (0.1025 + 0.00485 * math.log10(6.0)) / math.sqrt(1 - 0.15 ** 2)
    out["context"] = {"mccroskey_cl5": 5 * sl, "mccroskey_cl10": 10 * sl, "mccroskey_slope_per_deg": sl,
                      "ladson_slope_0_to_10": None}
    p = {(x["alpha"], x["q"]): x["ref"] for x in out["points"]}
    out["context"]["ladson_slope_0_to_10"] = (p[(10.0, "cl")] - p[(0.0, "cl")]) / 10
    # flags per prereg: band > 2 % of Cl or > 10 % of Cd
    out["flags"] = [f"{x['q']} a={x['alpha']}: band {x['band_pct']:.1f} %" for x in out["points"] if x["band_pct"] is not None and
                    ((x["q"] == "cl" and x["band_pct"] > 2) or (x["q"] == "cd" and x["band_pct"] > 10))]
    # POST-HOC (not pre-registered): the pre-registered 'linear vs nearest point' term is ~half a 2-deg step of the lift
    # curve at mid-bracket, i.e. it measures the table spacing, not interpolation error. Alternative: |linear - quadratic|
    # through the 3 nearest rows, RSS with the same grit and repeatability terms.
    import numpy as np
    out["posthoc_band_quadratic"] = []
    for x in out["points"]:
        k = 0 if x["q"] == "cd" else 1; errs = []
        for g, rows in TABLE.items():
            rs = sorted(rows, key=lambda r: abs(r[0] - x["alpha"]))[:3]
            c = np.polyfit([r[0] for r in rs], [r[1 + k] for r in rs], 2)
            errs.append(abs(np.polyval(c, x["alpha"]) - x["per_grit"][g]["lin"]))
        b = math.sqrt(x["half_range_grit"] ** 2 + max(errs) ** 2 + REP[x["q"]] ** 2)
        out["posthoc_band_quadratic"].append({"alpha": x["alpha"], "q": x["q"], "interp_lin_vs_quad": max(errs), "band": b,
                                              "band_pct": 100 * b / abs(x["ref"]) if abs(x["ref"]) > 1e-3 else None})
        print("posthoc", x["alpha"], x["q"], round(max(errs), 5), round(b, 5), out["posthoc_band_quadratic"][-1]["band_pct"])
    json.dump(out, open(outp, "w"), indent=1)
    for x in out["points"]:
        print(x["alpha"], x["q"], round(x["ref"], 5), "+-", round(x["band"], 5), x["band_pct"] and round(x["band_pct"], 2),
              {g[:8]: round(v["lin"], 5) for g, v in x["per_grit"].items()})
    print("tmr_vs_table", out["tmr_vs_table"]); print("context", out["context"]); print("flags", out["flags"])


if __name__ == "__main__":
    main(*sys.argv[1:])
