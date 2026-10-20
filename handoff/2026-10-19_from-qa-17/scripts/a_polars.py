"""QA r17 Task A (PREREG_R17 a212b29): NACA 4406 (fansim naca4 0.04/0.4/0.06) polars, NeuralFoil + XFOIL.
Usage: python a_polars.py <outdir> [airfoil_name coords.dat Re1,Re2,...]  (default: the prop section)"""
import json, os, subprocess, sys, time
import numpy as np
import neuralfoil as nf
from fansim.geometry.airfoil import naca4
XF = "/workspace/fansim/qa/xfoil_build/Xfoil/bin/xfoil"
ALPHA = np.arange(0.0, 10.0 + 1e-9, 1.0)


def dedupe(xy):
    keep = [0] + [i for i in range(1, len(xy)) if np.hypot(*(xy[i] - xy[i - 1])) > 1e-9]
    xy = xy[keep]
    return xy[:-1] if np.allclose(xy[0], xy[-1]) else xy


def write_dat(xy, fn, name):
    with open(fn, "w") as fh:
        fh.write(name + "\n"); [fh.write(f"{x:.7f} {y:.7f}\n") for x, y in xy]


def xfoil(dat, re, ncrit, tag, wd):
    pol = os.path.join(wd, f"{tag}_Re{re:.0f}_N{ncrit}.pol")
    if os.path.exists(pol): os.remove(pol)
    cmd = f"PLOP\nG F\n\nLOAD {dat}\n\nPANE\nOPER\nVISC {re:.0f}\nITER 300\nVPAR\nN {ncrit}\n\nPACC\n{pol}\n\nASEQ 0 10 1\nPACC\n\nQUIT\n"
    t0 = time.monotonic()
    try:
        log = subprocess.run([XF], input=cmd, capture_output=True, text=True, timeout=300).stdout
    except subprocess.TimeoutExpired:
        log = "TIMEOUT"
    rows = {}
    if os.path.exists(pol):
        for l in open(pol).read().splitlines()[12:]:
            v = l.split()
            if len(v) >= 7: rows[round(float(v[0]), 3)] = dict(cl=float(v[1]), cd=float(v[2]), cm=float(v[4]), xtr_top=float(v[5]), xtr_bot=float(v[6]))
    return rows, round(time.monotonic() - t0, 1), log.count("VISCAL:  Convergence failed")


def run(name, xy, res, outdir):
    wd = os.path.join(outdir, "xf"); os.makedirs(wd, exist_ok=True)
    dat = os.path.join(wd, f"{name}.dat"); write_dat(xy, dat, name)
    out = []
    for re in res:
        for nc in (9, 5):
            a = nf.get_aero_from_coordinates(coordinates=xy, alpha=ALPHA, Re=re, n_crit=nc, model_size="xxxlarge")
            for j, al in enumerate(ALPHA):
                out.append(dict(airfoil=name, tool="neuralfoil", ncrit=nc, Re=re, alpha=float(al), cl=float(a["CL"][j]), cd=float(a["CD"][j]),
                                cm=float(a["CM"][j]), conf=float(a["analysis_confidence"][j]), xtr_top=float(a["Top_Xtr"][j]), xtr_bot=float(a["Bot_Xtr"][j])))
            rows, sec, nfail = xfoil(dat, re, nc, name, wd)
            for al in ALPHA:
                r = rows.get(round(float(al), 3))
                out.append(dict(airfoil=name, tool="xfoil", ncrit=nc, Re=re, alpha=float(al), converged=r is not None, **(r or {})))
            print(name, re, nc, "xfoil conv", len(rows), "/11", sec, "s", flush=True)
    return out


if __name__ == "__main__":
    outdir = sys.argv[1]; os.makedirs(outdir, exist_ok=True)
    if len(sys.argv) > 2:
        name, fn, res = sys.argv[2], sys.argv[3], [float(x) for x in sys.argv[4].split(",")]
        xy = dedupe(np.loadtxt(fn, skiprows=1))
    else:
        name, res = "fansim_naca4406", [6e4, 8e4, 1.2e5]
        xy60 = dedupe(naca4(0.04, 0.4, 0.06, 60)); xy = dedupe(naca4(0.04, 0.4, 0.06, 160))
        np.savetxt(os.path.join(outdir, "section_builder_n60.csv"), xy60, delimiter=",", header="x_c,y_c", comments="", fmt="%.7f")
        np.savetxt(os.path.join(outdir, "section_n160.csv"), xy, delimiter=",", header="x_c,y_c", comments="", fmt="%.7f")
        # report-only resolution check: NeuralFoil at 60 vs 160 points
        res60 = {}
        for re in res:
            a60 = nf.get_aero_from_coordinates(coordinates=xy60, alpha=ALPHA, Re=re, n_crit=9, model_size="xxxlarge")
            a160 = nf.get_aero_from_coordinates(coordinates=xy, alpha=ALPHA, Re=re, n_crit=9, model_size="xxxlarge")
            res60[str(re)] = dict(max_dcl=float(np.max(np.abs(a60["CL"] - a160["CL"]))), max_rel_dcd=float(np.max(np.abs(a60["CD"] / a160["CD"] - 1))))
        json.dump(res60, open(os.path.join(outdir, "nf_resolution_check.json"), "w"), indent=1)
        print("thickness max", float(np.max(xy[:, 1]) - 0), flush=True)
    out = run(name, xy, res, outdir)
    with open(os.path.join(outdir, f"{name}_polars.jsonl"), "w") as fh:
        [fh.write(json.dumps(r) + "\n") for r in out]
    print("DONE", flush=True)
