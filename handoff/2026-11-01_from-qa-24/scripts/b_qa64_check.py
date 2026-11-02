"""QA r24 B (PREREG_R24 88c4e79): QA-64 wording check, no CFD. Reads committed docs/data only.
Usage: repo-r24/.venv/bin/python b_qa64_check.py <repo> <out.json>"""
import csv, json, sys
from pathlib import Path
R = Path(sys.argv[1])
def pmax(path, col):
    return max(float(r[col]) for r in csv.DictReader(open(R / path)))
fans = {
  "A12x25": {"P": 0.0, "Pmax": 22.9, "Pmax_src": "docs/a12x25-reference.md:13 (Noctua spec 2.34 mmH2O)",
             "E_headline": 100 * (59.8 / 60.1 - 1), "E_src": "docs/validation/a12x25_pq_report.md:27 (59.8 vs 60.1 CFM)",
             "E_alt": {"no prism layers (same STL)": 100 * (58.4 / 60.1 - 1)}, "alt_src": "a12x25_pq_report.md:53",
             "published": "Noctua datasheet (docs/a12x25-reference.md:5)", "validated": "free air validated; all physics PASS (a12x25_pq_report.md:27,36)"},
  "FAN-01": {"P": 7.0, "Pmax": pmax("validation/reference/fan01/characteristic.csv", "p_chamber_static_pa"),
             "Pmax_src": "validation/reference/fan01/characteristic.csv (max p_chamber_static_pa)",
             "E_headline": 100 * (2.131 / 2.078 - 1), "E_src": "docs/validation/fan01/fan01_report.md:23 (2.131 vs 2.078 m3/s)",
             "E_alt": {"64 Pa (mid-curve, report-only)": 100 * (1.859 / 1.804 - 1)}, "alt_src": "fan01_report.md:24",
             "published": "Zenodo 10787093, CC-BY-4.0 (validation/reference/fan01/README.md)", "validated": "high-flow branch validated (fan01_report.md:32-33)"},
  "lt120": {"P": 6.85, "Pmax": pmax("docs/qa/benchmarks/lt120/curve.csv", "dp_pa"),
            "Pmax_src": "docs/qa/benchmarks/lt120/curve.csv (max dp_pa)",
            "E_headline": 100 * ((89.6 + 92.0) / 2 / 84.0 - 1),
            "E_src": "docs/validation/audits/2026-10-18-lt120-validation-prereg.md:69 (84.0 meas; 89.6 / 92.0 CFD)",
            "E_alt": {"5.8 mm mesh": 100 * (89.6 / 84.0 - 1), "6.2 mm mesh": 100 * (92.0 / 84.0 - 1)},
            "alt_src": "same line",
            "E_tipgap_report_only": {"0.5 mm": 6.6, "1.0 mm": 13.0, "1.5 mm": 6.3},
            "tipgap_src": "docs/validation/audits/2026-10-30-lt120-tip-gap-prereg.md:51-53",
            "published": "Lin & Tsai 2011 Proc IMechE C doi:10.1243/09544062JMES2231, via Tutar & Cam CC BY 4.0 (docs/qa/benchmarks/lt120/source.md:6,8)",
            "validated": "±10 % rule passes at 6.85 Pa; audit overall TRENDS (2026-10-18-lt120-validation-prereg.md:74-75)",
            "lowest_load_measured": None},
}
dps = sorted(float(r["dp_pa"]) for r in csv.DictReader(open(R / "docs/qa/benchmarks/lt120/curve.csv")))
fans["lt120"]["lowest_load_measured"] = dps[0]
for f in fans.values():
    f["P_over_Pmax"] = f["P"] / f["Pmax"]
    f["i_published"] = True
    f["ii_validated"] = True
    f["iii_near_free_air"] = f["P"] == 0 or f["P_over_Pmax"] <= 0.10
    f["iv_within_8"] = abs(round(f["E_headline"], 1)) <= 8.0
    f["within_10_all"] = abs(f["E_headline"]) <= 10.0 and all(abs(v) <= 10.0 for k, v in f["E_alt"].items() if "report-only" not in k)
claim = all(f["i_published"] and f["ii_validated"] and f["iii_near_free_air"] and f["iv_within_8"] for f in fans.values())
prop = (all(f["within_10_all"] for f in fans.values()) and fans["lt120"]["lowest_load_measured"] == 6.85
        and fans["A12x25"]["iii_near_free_air"] and fans["FAN-01"]["iii_near_free_air"])
verdict = "supported as worded" if claim else ("needs grok's proposed wording" if prop else "overstated")
out = {"fans": fans, "claim_supported": claim, "proposed_wording_holds": prop, "verdict": verdict}
json.dump(out, open(sys.argv[2], "w"), indent=1)
for n, f in fans.items():
    print(f"{n:7} P={f['P']:5.2f} Pmax={f['Pmax']:6.2f} P/Pmax={f['P_over_Pmax']:.3f} E={f['E_headline']:+.2f}% "
          f"alt={ {k: round(v, 2) for k, v in f['E_alt'].items()} } near={f['iii_near_free_air']} <=8={f['iv_within_8']} <=10={f['within_10_all']}")
print("lt120 lowest measured load", fans["lt120"]["lowest_load_measured"], "| VERDICT:", verdict)
