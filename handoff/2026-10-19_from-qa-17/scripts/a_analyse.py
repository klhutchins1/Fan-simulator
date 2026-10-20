"""QA r17 Task A analysis (PREREG_R17 a212b29): anchor rule, spread rule, CSVs. Usage: python a_analyse.py"""
import csv, json, statistics as st
A = "/workspace/fansim/qa/r17/a"; O = "/workspace/fansim/repo-r17/docs/qa/r17"
TOOLS = [("neuralfoil", 9), ("neuralfoil", 5), ("xfoil", 9), ("xfoil", 5)]
P = [json.loads(l) for l in open(f"{A}/fansim_naca4406_polars.jsonl")]; E = [json.loads(l) for l in open(f"{A}/e387_polars.jsonl")]
M = [r for r in csv.DictReader(l for l in open(f"{O}/r17-A-e387-tm4062-measured.csv") if not l.startswith("#"))]


def meas_at(re, a=4.0):  # mean of repeats at exactly a, else linear interpolation between neighbours
    rows = sorted(((float(r["alpha_deg"]), float(r["cl"]), float(r["cd"])) for r in M if float(r["Re"]) == re))
    at = [r for r in rows if abs(r[0] - a) < 1e-9]
    if at: return dict(cl=st.mean(r[1] for r in at), cd=st.mean(r[2] for r in at), n=len(at), cl_range=[min(r[1] for r in at), max(r[1] for r in at)])
    lo = max(r for r in rows if r[0] < a); hi = min(r for r in rows if r[0] > a); w = (a - lo[0]) / (hi[0] - lo[0])
    return dict(cl=lo[1] + w * (hi[1] - lo[1]), cd=lo[2] + w * (hi[2] - lo[2]), n=0)


def get(R, t, n, re, a):
    return next(x for x in R if x["tool"] == t and x["ncrit"] == n and x["Re"] == re and x["alpha"] == a)


anchor = {}
for re in (6e4, 1e5):
    m = meas_at(re); anchor[re] = {"measured": m, "tools": {}}
    for t, n in TOOLS:
        r = get(E, t, n, re, 4.0)
        if "cl" not in r: anchor[re]["tools"][f"{t}_N{n}"] = {"verdict": "NOCONV"}; continue
        ecl, ecd = r["cl"] / m["cl"] - 1, r["cd"] / m["cd"] - 1
        anchor[re]["tools"][f"{t}_N{n}"] = dict(cl=r["cl"], cd=r["cd"], e_cl=ecl, e_cd=ecd, verdict="PASS" if abs(ecl) <= .10 and abs(ecd) <= .30 else "FAIL")
ANCH = {6e4: 6e4, 8e4: 1e5, 1.2e5: 1e5}


def classify(sl, sd, k):
    if k < 2: return "UNUSABLE"
    if sl <= .10 and sd <= .30: return "CERTAIN"
    if sl <= .20 and sd <= .60: return "UNCERTAIN"
    return "UNUSABLE"


ref = []
for re in (6e4, 8e4, 1.2e5):
    cred = [f"{t}_N{n}" for t, n in TOOLS if anchor[ANCH[re]]["tools"][f"{t}_N{n}"]["verdict"] == "PASS"]
    for a in range(11):
        row = {"Re": int(re), "alpha_deg": a, "anchor_Re": int(ANCH[re]), "credible_tools": "+".join(cred)}
        for lab, tools in (("cred", cred), ("all", [f"{t}_N{n}" for t, n in TOOLS])):
            vals = [get(P, k.split("_N")[0], int(k.split("_N")[1]), re, float(a)) for k in tools]
            vals = [v for v in vals if "cl" in v]; cl = [v["cl"] for v in vals]; cd = [v["cd"] for v in vals]
            if len(vals) >= 1:
                mcl, mcd = st.median(cl), st.median(cd)
                sl, sd = (max(cl) - min(cl)) / mcl, (max(cd) - min(cd)) / mcd
            else:
                mcl = mcd = sl = sd = float("nan")
            row.update({f"{lab}_n": len(vals), f"{lab}_cl_median": round(mcl, 4), f"{lab}_cl_min": round(min(cl), 4) if cl else "", f"{lab}_cl_max": round(max(cl), 4) if cl else "",
                        f"{lab}_S_l": round(sl, 4), f"{lab}_cd_median": round(mcd, 5), f"{lab}_cd_min": round(min(cd), 5) if cd else "", f"{lab}_cd_max": round(max(cd), 5) if cd else "",
                        f"{lab}_S_d": round(sd, 4), f"{lab}_class": classify(sl, sd, len(vals))})
        ref.append(row)
with open(f"{O}/r17-A-reference-spread.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(ref[0])); w.writeheader(); w.writerows(ref)
F = ["airfoil", "tool", "ncrit", "Re", "alpha", "converged", "cl", "cd", "cm", "xtr_top", "xtr_bot", "conf"]
with open(f"{O}/r17-A-polars.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=F, extrasaction="ignore"); w.writeheader()
    for r in P + E:
        r = dict(r); r.setdefault("converged", True); w.writerow({k: (round(v, 5) if isinstance(v, float) and k not in ("Re", "alpha") else v) for k, v in r.items()})
import shutil
shutil.copy(f"{A}/section_builder_n60.csv", f"{O}/r17-A-section-naca4406-builder-n60.csv")
with open(f"{O}/r17-A-e387-tm4062-coords.csv", "w") as fh:
    fh.write("# NASA TM-4062 Table I design ordinates (thickened TE), Selig order TE-upper-LE-lower-TE. US-Gov work.\nx_c,y_c\n")
    for l in open(f"{A}/e387_tm4062_design.dat").read().splitlines()[1:]: fh.write(",".join(l.split()) + "\n")
dec = next(r for r in ref if r["Re"] == 80000 and r["alpha_deg"] == 4)
json.dump({"anchor": {str(k): v for k, v in anchor.items()}, "decision_point": dec,
           "nf_resolution": json.load(open(f"{A}/nf_resolution_check.json"))}, open(f"{A}/a_summary.json", "w"), indent=1)
print(json.dumps(dec, indent=0))
for r in ref: print(r["Re"], r["alpha_deg"], r["cred_class"], r["cred_S_l"], r["cred_S_d"], "| all", r["all_class"], r["all_S_l"], r["all_S_d"])
