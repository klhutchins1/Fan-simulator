"""One search for the plate leading-edge wall. Rule committed first:

docs/validation/audits/2026-11-15-stock-le-face-prereg.md

Does not edit config/problems/a12x25_reference.yaml. Does not change te_face.
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
from scripts.outline_te_face import TARGETS, TIP, _cut_extent  # noqa: E402

REF = ROOT / "validation" / "reference" / "a12x25_impeller.stl"
YAML = ROOT / "config" / "problems" / "a12x25_outline.yaml"
OUT_JSON = ROOT / "runs" / "outline_le" / "result.json"


def _wire(params, station, face: float) -> tuple[float, float]:
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
        le_skew=float(station.le_skew), te_face=float(station.te_face),
        le_face=float(face), **kw,
    )
    z = np.array([p.z for p in pts], dtype=float)
    return float(z.max() - z.min()), float(z[int(np.argmin(x))])


def _closest(params, station, ref_extent: float) -> tuple[float, float]:
    samples = np.linspace(0.0, 1.0, 21)
    scored = []
    for face in samples:
        extent, _le = _wire(params, station, float(face))
        scored.append((abs(extent - ref_extent), float(face), extent))
    best = min(scored, key=lambda row: (row[0], row[1]))
    lo = max(0.0, best[1] - 0.05)
    hi = min(1.0, best[1] + 0.05)
    for face in np.linspace(lo, hi, 11):
        extent, _le = _wire(params, station, float(face))
        row = (abs(extent - ref_extent), float(face), extent)
        if row[0] < best[0] - 1e-9 or (abs(row[0] - best[0]) <= 1e-9 and row[1] < best[1]):
            best = row
    return best[1], best[2]


def main() -> int:
    params = load_blade_params(YAML)
    ref = trimesh.load(REF, force="mesh")
    stations = list(params.stations)
    rows = []
    chosen = {}
    for target in TARGETS:
        station = min(
            stations,
            key=lambda s: abs((params.hub_radius - params.root_embed
                               + (params.tip_radius - (params.hub_radius - params.root_embed)) * s.r_frac)
                              / TIP - target),
        )
        ref_extent = _cut_extent(ref, target * TIP)
        face, extent = _closest(params, station, ref_extent)
        _full, le_full = _wire(params, station, 1.0)
        _got, le = _wire(params, station, face)
        rows.append({
            "r_over_R": target,
            "r_frac": float(station.r_frac),
            "te_face": float(station.te_face),
            "le_face": round(face, 4),
            "extent_mm": round(extent, 3),
            "ref_extent_mm": round(ref_extent, 3),
            "extent_error_mm": round(extent - ref_extent, 3),
            "le_shift_mm": round(le - le_full, 3),
        })
        chosen[float(station.r_frac)] = face
        print(
            f"r/R {target:.2f} le_face {face:.3f} te_face {station.te_face:.3f} "
            f"extent {extent:.3f} ref {ref_extent:.3f} err {extent - ref_extent:+.3f} "
            f"le_shift {le - le_full:+.3f}",
            flush=True,
        )
    root = min(stations, key=lambda s: s.r_frac)
    tip = max(stations, key=lambda s: s.r_frac)
    chosen[float(root.r_frac)] = chosen[rows[0]["r_frac"]]
    chosen[float(tip.r_frac)] = chosen[rows[-1]["r_frac"]]
    params.stations = [
        dataclasses.replace(s, le_face=float(chosen[float(s.r_frac)])) for s in stations
    ]
    l1 = all(abs(row["extent_error_mm"]) <= 0.40 for row in rows)
    l2 = all(abs(row["le_shift_mm"]) <= 0.20 for row in rows)
    save_blade_params(params, YAML)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(
        {"passed": bool(l1 and l2), "L1": l1, "L2": l2, "rows": rows}, indent=2,
    ), encoding="utf-8")
    print("L1", "PASS" if l1 else "FAIL", "L2", "PASS" if l2 else "FAIL", flush=True)
    print("PASSED" if l1 and l2 else "FAILED", flush=True)
    return 0 if l1 and l2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
