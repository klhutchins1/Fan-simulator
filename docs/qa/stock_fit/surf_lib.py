"""QA r9 Task C helpers (PREREG_R9 a0260c0). Prototype only; the shipped recipe is not touched.
official_distance(): the method of scripts/stock_surface_distance.py (full build_impeller, 6000 even samples
seed 1, blade surface r > hub+1, alignment over rotation in one pitch + axial shift, mean |signed distance|).
v2_check(): fit_recipe_to_stl.py's V2 measurement (smoothed reference cubic over r/R 0.50-0.99 vs built
measure_sections at r/R 0.50,0.60,...,0.90,0.99, TOL from fansim.validation.recipe_fit)."""
import dataclasses, tempfile
from pathlib import Path
import numpy as np, trimesh
from fansim.geometry import build_impeller, export_stl
from fansim.validation.recipe_fit import TOL, residuals, within_tol
from fansim.validation.section_compare import measure_sections
REF = "validation/reference/a12x25_impeller.stl"
_ref = trimesh.load(REF, force="mesh"); _ref.merge_vertices(); PQ = trimesh.proximity.ProximityQuery(_ref)

def rot(pts, a):
    c, s = np.cos(a), np.sin(a); return pts @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]).T

def build_full(p, path):
    export_stl(build_impeller(p), path); return trimesh.load(path, force="mesh")

def official_distance(p, mesh=None):
    if mesh is None:
        with tempfile.TemporaryDirectory() as td: mesh = build_full(p, Path(td) / "b.stl")
    pts, _ = trimesh.sample.sample_surface_even(mesh, 6000, seed=1)
    r = np.hypot(pts[:, 0], pts[:, 1]); sel = r > p.hub_radius + 1.0; P = pts[sel]
    pitch = 2 * np.pi / p.n_blades; best = None
    for a in np.linspace(0, pitch, 37)[:-1]:
        for dz in np.linspace(-2, 2, 9):
            d = np.abs(PQ.signed_distance((rot(P, a) + [0, 0, dz])[::6]))
            if best is None or d.mean() < best[0]: best = (d.mean(), a, dz)
    _, a, dz = best
    for a2 in np.linspace(a - pitch / 36, a + pitch / 36, 7):
        for dz2 in np.linspace(dz - 0.5, dz + 0.5, 5):
            d = np.abs(PQ.signed_distance(rot(P, a2) + [0, 0, dz2]))
            if d.mean() < best[0]: best = (d.mean(), a2, dz2)
    _, a, dz = best
    d = np.abs(PQ.signed_distance(rot(P, a) + [0, 0, dz])); rr = r[sel] / p.tip_radius
    bands = {f"{lo:.1f}-{lo+0.1:.1f}": round(float(np.mean(d[(rr >= lo) & (rr < lo + 0.1)])), 3)
             for lo in np.arange(0.4, 1.0, 0.1) if np.any((rr >= lo) & (rr < lo + 0.1))}
    outer = d[(rr >= 0.8) & (rr <= 1.0 + 1e-9)]
    return {"mean_mm": round(float(d.mean()), 3), "outer_0.8-1.0_mm": round(float(outer.mean()), 3),
            "p95_mm": round(float(np.percentile(d, 95)), 3), "by_r/R": bands, "rot_rad": float(a), "dz_mm": float(dz)}

_fit = None
def _smooth():
    global _fit
    if _fit is None:
        rows = [r for r in measure_sections(REF, tuple(np.round(np.arange(0.50, 0.9901, 0.01), 3))) if r["n_blades"] > 0]
        x = np.array([r["r_frac"] for r in rows])
        _fit = {k: np.polynomial.Polynomial.fit(x, [r[k] for r in rows], 3) for k in ("chord_mm", "stagger_deg", "camber_ratio", "thickness_ratio")}
    return _fit

RADII = (0.50, 0.60, 0.70, 0.80, 0.90, 0.99)
def v2_check(stl_path):
    fit = _smooth(); built = measure_sections(str(stl_path), RADII); rows = []
    for rr, b in zip(RADII, built):
        if not b["n_blades"]: rows.append({"r/R": rr, "ok": False, "err": "unmeasurable"}); continue
        res = residuals(b, {k: float(f(rr)) for k, f in fit.items()})
        rows.append({"r/R": rr, "ok": within_tol(res), **{k: round(v, 4) for k, v in res.items()}})
    return all(r["ok"] for r in rows), rows
