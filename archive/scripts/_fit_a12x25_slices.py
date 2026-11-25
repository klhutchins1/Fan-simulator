"""Cylinder-slice chord/stagger of reference STL vs stock recipe (gold ✕ fit aid)."""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import trimesh

from fansim.geometry.blade import build_impeller_preview
from fansim.geometry.config import load_blade_params

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "validation" / "reference" / "a12x25_impeller.stl"
YAML = ROOT / "config" / "problems" / "a12x25_reference_v1.yaml"
RADII = (27.0, 37.0, 53.0)


def section_metrics_from_cloud(xyz: np.ndarray, r0: float) -> dict | None:
    if len(xyz) < 8:
        return None
    th = np.arctan2(xyz[:, 1], xyz[:, 0])
    med = float(np.median(th))
    th = (th - med + np.pi) % (2.0 * np.pi) - np.pi
    s = r0 * th
    z = xyz[:, 2]
    X = np.c_[s - s.mean(), z - z.mean()]
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    axis = vt[0]
    proj = X @ axis
    i0, i1 = int(np.argmin(proj)), int(np.argmax(proj))
    p0 = np.array([s[i0], z[i0]])
    p1 = np.array([s[i1], z[i1]])
    chord = float(np.linalg.norm(p1 - p0))
    d = p1 - p0
    stagger = float(abs(np.degrees(np.arctan2(d[1], d[0]))))
    wall = float(np.ptp(X @ vt[1]))
    return {"chord": chord, "stagger_deg": stagger, "wall": wall, "n": len(xyz)}


def slice_mesh(mesh: trimesh.Trimesh, r0: float, dr: float = 0.6) -> list[dict]:
    v = np.asarray(mesh.vertices)
    r = np.linalg.norm(v[:, :2], axis=1)
    mask = np.abs(r - r0) <= dr
    pts = v[mask]
    th_all = np.arctan2(pts[:, 1], pts[:, 0]) if len(pts) else np.array([])
    if len(pts) < 30:
        return []
    bins = np.linspace(-np.pi, np.pi, 10)
    out: list[dict] = []
    for i in range(9):
        m2 = (th_all >= bins[i]) & (th_all < bins[i + 1])
        if int(m2.sum()) < 8:
            continue
        mtr = section_metrics_from_cloud(pts[m2], r0)
        if mtr and 10.0 < mtr["chord"] < 60.0:
            out.append(mtr)
    return out


def median_slice(mesh: trimesh.Trimesh, r0: float) -> dict | None:
    rows = slice_mesh(mesh, r0)
    if not rows:
        return None
    return {k: float(np.median([r[k] for r in rows])) for k in ("chord", "stagger_deg", "wall")}


def preview_trimesh(params) -> trimesh.Trimesh:
    mesh, _ = build_impeller_preview(params)
    if isinstance(mesh, trimesh.Trimesh):
        return mesh
    return trimesh.Trimesh(
        vertices=np.asarray(mesh.points),
        faces=np.asarray(mesh.faces),
        process=False,
    )


def report(label: str, mesh: trimesh.Trimesh) -> None:
    print(label)
    for r0 in RADII:
        print(f"  r={r0:.0f}: {median_slice(mesh, r0)}")


def main() -> None:
    ref = trimesh.load(REF, force="mesh")
    report("REF a12x25_impeller.stl", ref)

    base = load_blade_params(YAML)
    report("STOCK current yaml", preview_trimesh(base))

    les = copy.deepcopy(base)
    st = sorted(les.stations, key=lambda s: s.r_frac)
    st[1].le_skew = float(st[1].skew)
    st[1].skew = 0.0
    st[2].le_skew = float(st[2].skew)
    st[2].skew = 0.0
    les.stations = st
    report("STOCK skew->le_skew (3/13)", preview_trimesh(les))


if __name__ == "__main__":
    main()
