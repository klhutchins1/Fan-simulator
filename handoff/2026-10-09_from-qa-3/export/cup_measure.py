"""Cup Ø / depth / grip pads by axis-ray casting (E7-E9 follow-up; export_check's median heuristic missed the cup).
Usage: python cup_measure.py <stl> ... -> one JSON line per STL."""
import json, math, sys
import numpy as np
import trimesh


def prof(m, z, n):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    loc, idx, _ = m.ray.intersects_location(np.tile([0, 0, z], (n, 1)), np.c_[np.cos(a), np.sin(a), 0 * a])
    r = np.full(n, np.inf)
    for p, i in zip(loc, idx):
        rr = math.hypot(p[0], p[1])
        if rr > 1e-6:
            r[i] = min(r[i], rr)
    return r


for f in sys.argv[1:]:
    m = trimesh.load(f, force="mesh"); lo, hi = m.bounds
    zs = np.arange(lo[2] + 0.01, hi[2], 0.02)
    meds = []
    for z in zs:
        r = prof(m, z, 90); fin = r[np.isfinite(r)]
        meds.append(np.median(fin) if len(fin) == 90 else np.nan)
    meds = np.array(meds)
    cupz = zs[(meds > 17.5) & (meds < 19.5)]
    zmid = float(cupz.mean())
    r = prof(m, zmid, 2880)
    wall = float(np.median(r)); tip = float(r.min())
    pad = r < wall - 0.35
    grips = int(np.sum(pad & ~np.roll(pad, 1)))
    bore = prof(m, float(zs[np.nanargmin(meds)]), 360)
    print(json.dumps({"stl": f.split("/")[-1], "cup_z": [round(float(cupz.min()) - 0.01, 3), round(float(cupz.max()) + 0.01, 3)],
                      "cup_depth_mm": round(float(cupz.max() - cupz.min()) + 0.02, 3),
                      "open_side": "zmin" if abs(cupz.min() - lo[2]) < 0.1 else ("zmax" if abs(cupz.max() - hi[2]) < 0.1 else "none"),
                      "cup_dia_mm": round(2 * wall, 3), "grip_tip_dia_mm": round(2 * tip, 3),
                      "grip_protrude_mm": round(wall - tip, 3), "grip_count": grips,
                      "bore_dia_mm": round(2 * float(np.median(bore[np.isfinite(bore)])), 3)}))
