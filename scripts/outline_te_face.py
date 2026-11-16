"""One search for the plate trailing-edge wall. Rule committed first:

docs/validation/audits/2026-11-15-stock-te-face-prereg.md

Does not edit config/problems/a12x25_reference.yaml.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.geometry.blade import _section_loop, _thick_scale_kw  # noqa: E402
from fansim.geometry.config import load_blade_params, save_blade_params  # noqa: E402
from fansim.geometry.features import Features  # noqa: E402
from scripts.outline_hub import with_hub  # noqa: E402
from scripts.outline_match import _candidate  # noqa: E402

TARGETS = (0.50, 0.60, 0.70, 0.80, 0.90)
TIP = 54.5
REF = ROOT / "validation" / "reference" / "a12x25_impeller.stl"
OUT_YAML = ROOT / "config" / "problems" / "a12x25_outline.yaml"
OUT_JSON = ROOT / "runs" / "outline_te" / "result.json"


def _cut_extent(mesh: trimesh.Trimesh, radius: float) -> float:
    """Median blade axial span where the scan crosses a cylinder of this radius."""
    v = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces)
    radial = np.hypot(v[:, 0], v[:, 1])
    pts = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ia = faces[:, a]
        ib = faces[:, b]
        ra = radial[ia]
        rb = radial[ib]
        denom = rb - ra
        cross = (ra - radius) * (rb - radius) <= 0.0
        ok = cross & (np.abs(denom) > 1e-9)
        t = np.zeros(len(faces))
        t[ok] = (radius - ra[ok]) / denom[ok]
        keep = ok & (t >= -1e-6) & (t <= 1.0 + 1e-6)
        if not np.any(keep):
            continue
        tri_a = v[ia[keep]]
        tri_b = v[ib[keep]]
        tt = t[keep][:, None]
        pts.append(tri_a + tt * (tri_b - tri_a))
    if not pts:
        raise RuntimeError(f"no cylinder cut at r={radius}")
    cloud = np.vstack(pts)
    ang = np.arctan2(cloud[:, 1], cloud[:, 0])
    order = np.argsort(ang)
    ang = ang[order]
    cloud = cloud[order]
    # Split the circle at the nine large gaps between blades.
    step = np.diff(ang, append=ang[0] + 2.0 * np.pi)
    gaps = np.argsort(step)[-9:]
    bounds = np.sort(gaps)
    spans = []
    for i, start in enumerate(bounds):
        end = bounds[(i + 1) % len(bounds)]
        if end > start:
            group = cloud[start:end]
        else:
            group = np.vstack([cloud[start:], cloud[:end]])
        if len(group) < 3:
            continue
        spans.append(float(group[:, 2].max() - group[:, 2].min()))
    if len(spans) < 9:
        raise RuntimeError(f"expected 9 blades at r={radius}, saw {len(spans)}")
    return float(np.median(spans))


def _wire(params, station, face: float) -> tuple[float, float]:
    """Axial extent and leading-edge Z of one placed section."""
    r0 = params.hub_radius - params.root_embed
    r = r0 + (params.tip_radius - r0) * float(station.r_frac)
    kw = _thick_scale_kw(params)
    x, pts = _section_loop(
        r=r, r_frac=float(station.r_frac), chord=float(station.chord),
        stagger_deg=float(station.stagger_deg), thickness=float(station.thickness),
        max_camber=float(station.max_camber), camber_pos=float(station.camber_pos),
        sweep=float(station.sweep), skew=float(station.skew),
        le_sweep=float(station.le_sweep), lean_deg=float(station.lean_deg),
        n_chord=int(params.n_chord), features=Features(),
        le_skew=float(station.le_skew), te_face=float(face), **kw,
    )
    z = np.array([p.z for p in pts], dtype=float)
    return float(z.max() - z.min()), float(z[int(np.argmin(x))])


def _closest_face(params, station, ref_extent: float) -> tuple[float, float]:
    """te_face in [0, 1] whose extent is closest to the Noctua span."""
    samples = np.linspace(0.0, 1.0, 21)
    scored = []
    for face in samples:
        extent, _le = _wire(params, station, float(face))
        scored.append((abs(extent - ref_extent), float(face), extent))
    best = min(scored, key=lambda row: (row[0], row[1]))
    # One local refinement around that sample. Still the same search.
    lo = max(0.0, best[1] - 0.05)
    hi = min(1.0, best[1] + 0.05)
    for face in np.linspace(lo, hi, 11):
        extent, _le = _wire(params, station, float(face))
        row = (abs(extent - ref_extent), float(face), extent)
        if row[0] < best[0] - 1e-9 or (abs(row[0] - best[0]) <= 1e-9 and row[1] < best[1]):
            best = row
    return best[1], best[2]


def main() -> int:
    v3 = load_blade_params(ROOT / "config" / "problems" / "a12x25_reference.yaml")
    params = with_hub(_candidate(v3, 1.0), 26.0, 6.5)
    ref = trimesh.load(REF, force="mesh")
    stations = list(params.stations)
    by_rr = []
    rows = []
    for target in TARGETS:
        station = min(
            stations,
            key=lambda s: abs((params.hub_radius - params.root_embed
                               + (params.tip_radius - (params.hub_radius - params.root_embed)) * s.r_frac)
                              / TIP - target),
        )
        radius = target * TIP
        ref_extent = _cut_extent(ref, radius)
        face, extent = _closest_face(params, station, ref_extent)
        _full, le_full = _wire(params, station, 1.0)
        _thin, le = _wire(params, station, face)
        rows.append({
            "r_over_R": target,
            "r_frac": float(station.r_frac),
            "te_face": round(face, 4),
            "extent_mm": round(extent, 3),
            "ref_extent_mm": round(ref_extent, 3),
            "extent_error_mm": round(extent - ref_extent, 3),
            "le_shift_mm": round(le - le_full, 3),
        })
        by_rr.append((float(station.r_frac), face))
        print(
            f"r/R {target:.2f} te_face {face:.3f} extent {extent:.3f} "
            f"ref {ref_extent:.3f} err {extent - ref_extent:+.3f} le_shift {le - le_full:+.3f}",
            flush=True,
        )
    face_of = dict(by_rr)
    root = min(stations, key=lambda s: s.r_frac)
    tip = max(stations, key=lambda s: s.r_frac)
    face_of[float(root.r_frac)] = face_of[rows[0]["r_frac"]]
    face_of[float(tip.r_frac)] = face_of[rows[-1]["r_frac"]]
    params.stations = [
        dataclasses.replace(s, te_face=float(face_of[float(s.r_frac)])) for s in stations
    ]
    f1 = all(abs(row["extent_error_mm"]) <= 0.40 for row in rows)
    f2 = all(abs(row["le_shift_mm"]) <= 0.20 for row in rows)
    save_blade_params(params, OUT_YAML)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {"passed": bool(f1 and f2), "F1": f1, "F2": f2, "rows": rows,
               "yaml": str(OUT_YAML)}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("F1", "PASS" if f1 else "FAIL", "F2", "PASS" if f2 else "FAIL", flush=True)
    print("PASSED" if payload["passed"] else "FAILED", flush=True)
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
