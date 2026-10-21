"""QA r19 B analysis (PREREG_R19 cab2825). Usage: python b_analyse.py <b_bemt.jsonl> <tud_forces.json> <uiuc_dir> <out_dir_csv> <summary.json>"""
import csv, json, os, sys
import numpy as np
R = [json.loads(l) for l in open(sys.argv[1])]; F = json.load(open(sys.argv[2])); U = sys.argv[3]; OUT = sys.argv[4]
by = {r["key"]: r for r in R}


def rows(path):
    o = []
    for line in open(path):
        try: o.append([float(x) for x in line.split()])
        except ValueError: pass
    return np.array(o)


ST = rows(os.path.join(U, "da4002_9x6.75_static_1107rd.txt"))
JS = {5028: rows(os.path.join(U, "da4002_9x6.75_1104rd_5028.txt")), 3030: rows(os.path.join(U, "da4002_9x6.75_1101md_3030.txt"))}


def meas(prop, rpm, J):
    if prop == "TUD":
        k = int(np.argmin([abs(p["J"] - J) for p in F["CT"]["points"]]))
        return F["CT"]["points"][k]["val"], F["CP"][k]["val"], "Casalino2021 Fig19/20 (digitised)"
    if J == 0.0:
        k = int(np.argmin(abs(ST[:, 0] - rpm))); return ST[k, 1], ST[k, 2], f"static row {ST[k,0]:.0f} rpm"
    a = JS[rpm]
    if J < a[:, 0].min() or J > a[:, 0].max(): return None, None, "outside measured J"
    return float(np.interp(J, a[:, 0], a[:, 1])), float(np.interp(J, a[:, 0], a[:, 2])), f"J-sweep {rpm} rpm"


tab = []
for r in R:
    for x in r["res"]:
        ctm, cpm, src = meas(r["prop"], int(r["rpm"]), x["J"])
        small = ctm is not None and abs(ctm) < 0.02
        e_t = None if ctm is None or small else x["CT"] / ctm - 1; e_p = None if cpm is None or small else x["CP"] / cpm - 1
        tab.append(dict(key=r["key"], prop=r["prop"], geom=r.get("geom", ""), section=r["section"], backend=r["backend"], variant=r["variant"],
                        rpm=r["rpm"], J=x["J"], CT_bemt=x["CT"], CP_bemt=x["CP"], converged=x["converged"],
                        CT_meas=ctm, CP_meas=cpm, e_CT=e_t, e_CP=e_p, dCT_abs=None if ctm is None else x["CT"] - ctm, meas_src=src))


def pick(key, J): return next(t for t in tab if t["key"] == key and abs(t["J"] - J) < 0.02)


def verdict(key):
    pts = [pick(key, 0.0), pick(key, 0.4)]
    ok = all(p["converged"] and p["e_CT"] is not None and abs(p["e_CT"]) <= 0.15 and abs(p["e_CP"]) <= 0.20 for p in pts)
    fails = [f"J{p['J']:.2f}: eCT {p['e_CT']:+.1%} eCP {p['e_CP']:+.1%}" for p in pts if not (abs(p["e_CT"]) <= 0.15 and abs(p["e_CP"]) <= 0.20)]
    return ("AGREE" if ok else "DISAGREE"), fails, pts


S = {}
for key in sorted({t["key"] for t in tab}):
    v, fails, pts = verdict(key)
    S[key] = dict(verdict=v, fails=fails, eCT_J0=pts[0]["e_CT"], eCP_J0=pts[0]["e_CP"], eCT_J04=pts[1]["e_CT"], eCP_J04=pts[1]["e_CP"],
                  G_pp=100 * (pts[1]["e_CT"] - pts[0]["e_CT"]), all_converged=all(t["converged"] for t in tab if t["key"] == key))
diag = {}
for prop, gk in (("TUD", ""), ("DA4002", "design"), ("DA4002", "surveyed")):
    for be in ("table", "neuralfoil"):
        kn = f"{prop}|{gk}|{'known_naca4412' if prop == 'TUD' else 'sda1075_mapped'}|{be}|nominal|{5000 if prop == 'TUD' else 5028}"
        kg = f"{prop}|{gk}|generic_naca4406|{be}|nominal|{5000 if prop == 'TUD' else 5028}"
        Gk, Gg = S[kn]["G_pp"], S[kg]["G_pp"]
        cls = "SECTION-DRIVEN" if abs(Gk) <= 10 and abs(Gg) >= abs(Gk) + 10 else "NOT-SECTION" if abs(Gk) > 10 and Gk < 0 else "MIXED"
        diag[f"{prop}|{gk}|{be}"] = dict(G_known_pp=Gk, G_generic_pp=Gg, cls=cls)
json.dump(dict(per_case=S, section_diag=diag), open(sys.argv[5], "w"), indent=1)
keys = list(tab[0]); w = csv.DictWriter(open(os.path.join(OUT, "r19-B-bemt-vs-measured.csv"), "w", newline=""), fieldnames=keys)
w.writeheader()
for t in tab:
    tt = {k: (round(v, 5) if isinstance(v, float) else v) for k, v in t.items()}
    if t["prop"] == "DA4002": tt["CT_meas"] = tt["CP_meas"] = ""   # UIUC raw values not committed (citation-only licence)
    w.writerow(tt)
for k, s in S.items():
    print(k, s["verdict"], "J0 %+.1f%%/%+.1f%%" % (100 * s["eCT_J0"], 100 * s["eCP_J0"]), "J.4 %+.1f%%/%+.1f%%" % (100 * s["eCT_J04"], 100 * s["eCP_J04"]), "G %+.1f" % s["G_pp"], "conv", s["all_converged"])
print(json.dumps(diag, indent=0))
