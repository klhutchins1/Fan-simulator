"""Lift the trailing edge onto the Noctua and hold the leading edge.

The pass rule is docs/validation/audits/2026-11-13-stock-z-edge-prereg.md,
written before the judging build. This script does not modify
config/problems/a12x25_reference.yaml.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.geometry.config import load_blade_params
from scripts.outline_hub import with_hub
from scripts.outline_match import _candidate

# Six cylinder cuts. r/R 1.00 is the tip cap, not a blade, so it is not here.
RADII = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95)
LE_TOL_MM = 0.20
EXT_TOL_MM = 0.40
MEAN_TOL_MM = 0.25
DAMP = 0.7
MAX_BUILDS = 4
SWEEP_LIM = 10.0
LE_SWEEP_LIM = 8.0
TIP_MM = 54.5
OUT = ROOT / "runs" / "outline_z"

# Hub-wall STL, measured before this run. The fast test locks the bar above these.
HUB26_ERRORS = {
    0.50: (-0.09, 2.02),
    0.60: (-0.01, 1.22),
    0.70: (0.03, 1.36),
    0.80: (0.06, 1.27),
    0.90: (0.01, 1.05),
    0.95: (0.12, 1.38),
}


def edge_shift(d_le: float, d_ext: float) -> tuple[float, float]:
    """(d_sweep, d_le_sweep) that cancels a leading-edge and extent error.

    ``d_le`` and ``d_ext`` are built minus reference, millimetres. Sweep moves
    the whole section. ``le_sweep`` moves the leading edge only, which changes
    the axial extent by the same amount when that edge is the high side.
    """
    d_le_sweep = -float(d_ext)
    d_sweep = -float(d_le) - d_le_sweep
    return d_sweep, d_le_sweep


def extrapolate_delta(r0: float, r1: float, d1: float, r2: float, d2: float) -> float:
    """Value at ``r0`` on the straight line through (r1, d1) and (r2, d2)."""
    return float(d1 + (r0 - r1) / (r2 - r1) * (d2 - d1))


def edges_pass(errors: dict) -> bool:
    if set(errors) != set(RADII):
        return False
    for d_le, d_ext in errors.values():
        if abs(d_le) > LE_TOL_MM or abs(d_ext) > EXT_TOL_MM:
            return False
    return True


def worst_edge(errors: dict) -> float:
    if set(errors) != set(RADII):
        return float("inf")
    return max(max(abs(a), abs(b)) for a, b in errors.values())


def section_errors(built: list[dict], ref: list[dict]) -> dict:
    by_b = {round(float(r["r_frac"]), 2): r for r in built}
    by_r = {round(float(r["r_frac"]), 2): r for r in ref}
    out = {}
    for rr in RADII:
        b, r = by_b.get(rr), by_r.get(rr)
        if not b or not r or not b.get("n_blades") or not r.get("n_blades"):
            out[rr] = (float("inf"), float("inf"))
            continue
        out[rr] = (
            float(b["le_z_mm"] - r["le_z_mm"]),
            float(b["axial_extent_mm"] - r["axial_extent_mm"]),
        )
    return out


def _clamp(value: float, limit: float) -> float:
    return float(min(limit, max(-limit, value)))


def apply_edge(params, errors: dict, damp: float = DAMP):
    """Add the damped edge step. Chord, stagger, camber and thickness stay put."""
    r0 = params.hub_radius - params.root_embed
    span = params.tip_radius - r0
    rr = [(r0 + s.r_frac * span) / params.tip_radius for s in params.stations]
    deltas: list[tuple[float, float] | None] = [None] * len(params.stations)
    for i, srr in enumerate(rr):
        if abs(srr - 1.0) <= 0.02:
            key = 0.95
        else:
            key = min(RADII, key=lambda k: abs(k - srr))
            if abs(key - srr) > 0.03:
                continue
        d_sweep, d_le_sweep = edge_shift(*errors[key])
        deltas[i] = (damp * d_sweep, damp * d_le_sweep)
    known = [(params.stations[i].r_frac, deltas[i]) for i in range(len(deltas)) if deltas[i]]
    known.sort()
    (f1, d1), (f2, d2) = known[0], known[1]
    new_stations = []
    for i, station in enumerate(params.stations):
        if deltas[i] is None:
            d_sweep = extrapolate_delta(station.r_frac, f1, d1[0], f2, d2[0])
            d_le_sweep = extrapolate_delta(station.r_frac, f1, d1[1], f2, d2[1])
        else:
            d_sweep, d_le_sweep = deltas[i]
        new_stations.append(dataclasses.replace(
            station,
            sweep=_clamp(station.sweep + d_sweep, SWEEP_LIM),
            le_sweep=_clamp(station.le_sweep + d_le_sweep, LE_SWEEP_LIM),
        ))
    return dataclasses.replace(params, stations=new_stations)


def starting_params():
    v3 = load_blade_params(ROOT / "config/problems/a12x25_reference.yaml")
    return with_hub(_candidate(v3, 1.0), 26.0, 6.5)


def search(params, measure):
    """Up to four measured builds. Returns the kept params and the measured rows."""
    kept = params
    kept_err = None
    kept_rows = None
    history = []
    for i in range(MAX_BUILDS):
        built, ref = measure(params)
        errors = section_errors(built, ref)
        err = worst_edge(errors)
        history.append({"build": i, "worst": None if err == float("inf") else round(err, 4),
                        "errors": {f"{k:.2f}": [round(a, 4), round(b, 4)] for k, (a, b) in errors.items()}})
        print(f"build {i} worst {err:.3f} pass {edges_pass(errors)}", flush=True)
        if kept_err is not None and err > kept_err + 1e-9:
            print("worse than the kept build; discarding", flush=True)
            return kept, kept_rows, history
        kept, kept_err, kept_rows = params, err, (built, ref, errors)
        if edges_pass(errors) or i == MAX_BUILDS - 1:
            return kept, kept_rows, history
        params = apply_edge(params, errors)
    return kept, kept_rows, history


def _distance_dz0(params, mesh):
    """Mean |signed distance| with rotation about Z and no axial slide."""
    import trimesh

    sys.path.insert(0, str(ROOT / "docs" / "qa" / "stock_fit"))
    from surf_lib import PQ, rot

    pts, _ = trimesh.sample.sample_surface_even(mesh, 6000, seed=1)
    radius = np.hypot(pts[:, 0], pts[:, 1])
    sel = radius > params.hub_radius + 1.0
    samples = pts[sel]
    pitch = 2 * np.pi / params.n_blades
    best = None
    for angle in np.linspace(0, pitch, 37)[:-1]:
        dist = np.abs(PQ.signed_distance(rot(samples, angle)[::6]))
        if best is None or dist.mean() < best[0]:
            best = (float(dist.mean()), float(angle))
    _, angle = best
    for angle2 in np.linspace(angle - pitch / 36, angle + pitch / 36, 7):
        dist = np.abs(PQ.signed_distance(rot(samples, angle2)))
        if dist.mean() < best[0]:
            best = (float(dist.mean()), float(angle2))
    return {"mean_mm": round(best[0], 3), "rot_rad": best[1], "dz_mm": 0.0}


def _preview(params):
    from fansim.geometry.blade import build_impeller_preview

    mesh, _vol = build_impeller_preview(params, tol=0.2, screen=False)
    return mesh


def _measure_mesh(mesh, radii):
    from fansim.validation.section_compare import measure_sections

    path = OUT / "_cut.stl"
    mesh.export(path)
    return measure_sections(path, radii, tip_radius_mm=TIP_MM)


def main() -> int:
    import trimesh

    from fansim.geometry.blade import build_impeller
    from fansim.geometry.export import export_stl
    from fansim.validation.section_compare import measure_sections

    sys.path.insert(0, str(ROOT / "docs" / "qa" / "stock_fit"))
    from surf_lib import v2_check

    OUT.mkdir(parents=True, exist_ok=True)
    ref_rows = measure_sections(
        ROOT / "validation/reference/a12x25_impeller.stl", RADII, tip_radius_mm=TIP_MM,
    )

    def measure(params):
        print("preview", flush=True)
        mesh = _preview(params)
        return _measure_mesh(mesh, RADII), ref_rows

    params, _rows, history = search(starting_params(), measure)
    print("full impeller", flush=True)
    stl = OUT / "z_edge.stl"
    export_stl(build_impeller(params), stl)
    built = measure_sections(stl, RADII, tip_radius_mm=TIP_MM)
    errors = section_errors(built, ref_rows)
    mesh = trimesh.load(stl, force="mesh")
    ok, v2_rows = v2_check(stl)
    dist = _distance_dz0(params, mesh)
    passed = bool(edges_pass(errors) and ok and dist["mean_mm"] <= MEAN_TOL_MM)
    payload = {
        "passed": passed,
        "e1_e2": edges_pass(errors),
        "v2_ok": ok,
        "v2": v2_rows,
        "errors": {f"{k:.2f}": [round(a, 4), round(b, 4)] for k, (a, b) in errors.items()},
        "dist": dist,
        "history": history,
        "stl": str(stl),
    }
    (OUT / "result.json").write_text(json.dumps(payload, indent=1))
    print("PASSED" if passed else "FAILED", payload["errors"], dist, "v2", ok, flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as exc:  # noqa: BLE001
        print("ERROR", exc, flush=True)
        rc = 2
    raise SystemExit(rc)
