"""Distance from each Stock recipe build to the real A12x25 STL, aligned over rotation + axial shift (27.4 V5 diagnosis)."""
import os, sys, tempfile, json
from pathlib import Path
import numpy as np, trimesh
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.config import load_blade_params
ref = trimesh.load("validation/reference/a12x25_impeller.stl", force="mesh"); ref.merge_vertices()
pq = trimesh.proximity.ProximityQuery(ref)
def rot(pts, a):
    c, s = np.cos(a), np.sin(a); return pts @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]).T
out = {}
for name, yml in (("planar", "config/problems/a12x25_reference_planar.yaml"), ("cylinder", "config/problems/a12x25_reference.yaml")):
    p = load_blade_params(yml)
    with tempfile.TemporaryDirectory() as td:
        stl = Path(td) / "b.stl"; export_stl(build_impeller(p), stl)
        m = trimesh.load(stl, force="mesh")
    pts, _ = trimesh.sample.sample_surface_even(m, 6000, seed=1)
    r = np.hypot(pts[:, 0], pts[:, 1]); sel = r > p.hub_radius + 1.0   # blade surface only
    P = pts[sel]
    best = None
    pitch = 2 * np.pi / p.n_blades
    for a in np.linspace(0, pitch, 37)[:-1]:
        for dz in np.linspace(-2, 2, 9):
            Q = rot(P, a) + [0, 0, dz]
            d = np.abs(pq.signed_distance(Q[::6]))
            if best is None or d.mean() < best[0]: best = (d.mean(), a, dz)
    _, a, dz = best
    for a2 in np.linspace(a - pitch / 36, a + pitch / 36, 7):
        for dz2 in np.linspace(dz - 0.5, dz + 0.5, 5):
            d = np.abs(pq.signed_distance(rot(P, a2) + [0, 0, dz2]))
            if d.mean() < best[0]: best = (d.mean(), a2, dz2)
    _, a, dz = best
    d = np.abs(pq.signed_distance(rot(P, a) + [0, 0, dz])); rr = r[sel] / p.tip_radius
    bands = {f"{lo:.1f}-{lo+0.1:.1f}": round(float(np.mean(d[(rr >= lo) & (rr < lo + 0.1)])), 3) for lo in np.arange(0.4, 1.0, 0.1) if np.any((rr >= lo) & (rr < lo + 0.1))}
    out[name] = {"mean_mm": round(float(d.mean()), 3), "p95_mm": round(float(np.percentile(d, 95)), 3), "max_mm": round(float(d.max()), 3), "by_r/R": bands, "rot_deg": round(float(np.degrees(a)), 2), "dz_mm": round(float(dz), 2)}
    print(name, out[name], flush=True)
Path("T:/Projects/Fan Simulator/runs/cyl_sections/geom_diff.json").write_text(json.dumps(out, indent=1))
sys.stdout.flush(); os._exit(0)
