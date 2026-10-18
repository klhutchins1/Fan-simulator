"""QA r14 Task D: scan the local UIUC propDB archive (not committed) for static CT0 runs with Re(0.75R) in 6e4-1.5e5.
Re75 = 0.75*Omega*R*c75/nu (UIUC static-plot definition), nu = 1.5e-5 m^2/s. Usage: python d_uiuc_re.py <extracted UIUC-propDB dir> <out.json>"""
import glob, json, math, os, re, sys
import numpy as np
root, out = sys.argv[1], sys.argv[2]; NU = 1.5e-5; rows = []
for f in sorted(glob.glob(f"{root}/volume-*/data/*_static_*.txt")):
    base = os.path.basename(f); stem = base.split("_static_")[0]; vol = f.split("/")[-3]
    m = re.search(r"_(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", stem)
    if not m: continue
    D_in, P_in = float(m.group(1)), float(m.group(2))
    geo = glob.glob(f"{root}/volume-*/data/{stem}_geom.txt")
    try:
        d = np.loadtxt(f, skiprows=1, ndmin=2)
    except Exception: continue
    rec = {"file": base, "vol": vol, "prop": stem, "D_in": D_in, "pitch_in": P_in, "rpm": [float(d[:, 0].min()), float(d[:, 0].max())],
           "CT0": [float(d[:, 1].min()), float(d[:, 1].max())], "n": len(d), "geom": bool(geo)}
    if geo:
        g = np.loadtxt(geo[0], skiprows=1, ndmin=2); c75R = float(np.interp(0.75, g[:, 0], g[:, 1])); R = D_in * 0.0254 / 2
        rey = lambda rpm: 0.75 * rpm * 2 * math.pi / 60 * R * c75R * R / NU
        rec.update(c75_over_R=c75R, Re75=[rey(rec["rpm"][0]), rey(rec["rpm"][1])],
                   in_band=int(sum(6e4 <= rey(x) <= 1.5e5 for x in d[:, 0])))
        ib = [(x, y) for x, y in zip(d[:, 0], d[:, 1]) if 6e4 <= rey(x) <= 1.5e5]
        if ib: rec["CT0_in_band"] = [min(y for _, y in ib), max(y for _, y in ib)]; rec["rpm_in_band"] = [min(x for x, _ in ib), max(x for x, _ in ib)]
    rows.append(rec)
sel = [r for r in rows if 5 <= r["D_in"] <= 9.0 and r.get("in_band", 0) >= 3]
json.dump({"n_static": len(rows), "n_with_geom": sum(r["geom"] for r in rows), "selected": sel, "all": rows}, open(out, "w"), indent=1, default=float)
print(len(rows), sum(r["geom"] for r in rows), len(sel))
for r in sorted(sel, key=lambda r: (r["D_in"], r["prop"])): print(r["vol"], r["file"], r["D_in"], r["pitch_in"], [round(x) for x in r["rpm"]], [round(x) for x in r["Re75"]], r["in_band"], r.get("CT0_in_band"))
