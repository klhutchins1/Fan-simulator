"""Iterative fixed-point fit of the A12x25 Stock parametric recipe to the close-reference STL.

  uv run python scripts/fit_recipe_to_stl.py

Starts from config/problems/a12x25_reference_planar.yaml (the v2 recipe, NOT modified), re-stations the blade at the
measurable reference radii, and iterates build -> measure_sections -> update_station until every
measurable station is within tolerance (or 8 iterations). Writes
config/problems/a12x25_reference.yaml (promoted Stock v2).

Station layout (r/R = radius / tip): the recipe span coordinate runs hub_radius - root_embed (r/R
0.358) .. tip. Stations are placed at r/R = ROOT (0.358), 0.50, 0.60, 0.70, 0.80, 0.90, 1.00. The
reference has no measurable blade below r/R ~0.47 (inside the hub) nor exactly at the tip cut, so:
  * root (0.358): target = linear extrapolation of the smoothed reference from r/R 0.50/0.60, and its
    update reuses the residual of the first measurable station (0.50); it is NOT checked for
    convergence (no built measurement exists there).
  * tip (1.00): measured (built and reference) at r/R 0.99.
Reference profiles are smoothed (cubic polynomial in r/R over 0.50..0.99) before interpolation,
because the 20-bin camber-position estimate is quantised and camber/c is noisy at the +-0.005 level.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.geometry import build_impeller, export_stl  # noqa: E402
from fansim.geometry.blade import RadialStation, _interp_stations  # noqa: E402
from fansim.geometry.config import load_blade_params  # noqa: E402
from fansim.validation.recipe_fit import (  # noqa: E402
    DAMPING, SWEEP_SKEW_TRIGGER_MM, TOL, residuals, update_station, within_tol)
from fansim.validation.section_compare import measure_sections  # noqa: E402

STOCK = ROOT / "config/problems/a12x25_reference_planar.yaml"  # v2; v1 is older still
REF = ROOT / "validation/reference/a12x25_impeller.stl"
OUT = ROOT / "config/problems/a12x25_reference.yaml"
STATION_RR = [None, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]  # None = root at r0/tip
MEASURE_RR = {1.00: 0.99}  # station r/R -> radius actually measured
KEYS = ("chord_mm", "stagger_deg", "camber_ratio", "camber_pos", "thickness_ratio",
        "le_z_mm", "le_theta_deg")
FIELDS = ("chord", "stagger_deg", "thickness", "max_camber", "camber_pos", "sweep", "skew")
YAML_KEYS = ["r_frac", "chord", "stagger_deg", "thickness", "max_camber", "camber_pos", "sweep",
             "skew", "lean_deg", "le_sweep", "le_skew"]


def smooth_reference(dense_rr):
    rows = [r for r in measure_sections(REF, dense_rr) if r["n_blades"] > 0]
    x = np.array([r["r_frac"] for r in rows])
    return {k: np.polynomial.Polynomial.fit(x, [r[k] for r in rows], 3) for k in KEYS}


def ref_at(fit, rr):
    return {k: float(fit[k](rr)) for k in KEYS}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-iter", type=int, default=8)
    ap.add_argument("--wrap", choices=("cylinder", "planar"), default="cylinder",
                    help="section placement to fit with (roadmap 27.4; planar = the v2 recipe)")
    a = ap.parse_args()
    params = dataclasses.replace(load_blade_params(STOCK), section_wrap=a.wrap)
    tip = params.tip_radius
    r0 = params.hub_radius - params.root_embed
    rr_root = r0 / tip
    rr_list = [rr_root if v is None else v for v in STATION_RR]
    rfracs = [(rr * tip - r0) / (tip - r0) for rr in rr_list]

    # Initial stations: the Stock recipe evaluated at the new station spans.
    it = _interp_stations(params, 400)
    stations = [{k: float(np.interp(f, it["r_frac"], it[k])) for k in
                 FIELDS + ("le_sweep", "le_skew", "lean_deg")} | {"r_frac": float(f)}
                for f in rfracs]

    fit = smooth_reference(tuple(np.round(np.arange(0.50, 0.9901, 0.01), 3)))
    meas_rr = [None if v is None else MEASURE_RR.get(v, v) for v in STATION_RR]
    targets = []
    for m in meas_rr:
        if m is None:  # root: linear extrapolation from 0.50 / 0.60
            a5, a6 = ref_at(fit, 0.50), ref_at(fit, 0.60)
            f = (rr_root - 0.50) / 0.10
            targets.append({k: a5[k] + f * (a6[k] - a5[k]) for k in KEYS})
        else:
            targets.append(ref_at(fit, m))
    measure_radii = tuple(m for m in meas_rr if m is not None)

    tmp = tempfile.TemporaryDirectory()
    history, last_hits = [], {}
    converged = False
    for n in range(1, a.max_iter + 1):
        p = dataclasses.replace(params, stations=[RadialStation(**s) for s in stations])
        stl = Path(tmp.name) / f"iter{n}.stl"
        export_stl(build_impeller(p), stl)
        built_m = measure_sections(stl, measure_radii)
        assert all(r["n_blades"] > 0 for r in built_m), "built section not measurable"
        itr = iter(built_m)
        built = [None if m is None else next(itr) for m in meas_rr]
        # LE offsets vs reference (theta phase is arbitrary -> remove the mean over stations).
        dth = [b["le_theta_deg"] - t["le_theta_deg"] for b, t in zip(built, targets)
               if b is not None]
        th_mean = float(np.mean(dth))
        print(f"\n=== iteration {n} (built / smoothed reference) ===")
        print("r/R   | stagger      | chord        | camber/c      | cpos      | t/c          "
              "| dLEz dLEs mm")
        rows, all_ok = [], True
        for i, (b, t) in enumerate(zip(built, targets)):
            if b is None:
                print(f"{rr_list[i]:.3f} | root: extrapolated target, no built measurement")
                continue
            res = residuals(b, t)
            ok = within_tol(res)
            all_ok &= ok
            dz = b["le_z_mm"] - t["le_z_mm"]
            ds = float(np.radians(b["le_theta_deg"] - t["le_theta_deg"] - th_mean) * b["r_mm"])
            rows.append((i, res, dz, ds))
            print(f"{meas_rr[i]:.3f} | {b['stagger_deg']:5.1f}/{t['stagger_deg']:5.1f} | "
                  f"{b['chord_mm']:5.1f}/{t['chord_mm']:5.1f} | "
                  f"{b['camber_ratio']:.3f}/{t['camber_ratio']:.3f} | "
                  f"{b['camber_pos']:.2f}/{t['camber_pos']:.2f} | "
                  f"{b['thickness_ratio']:.3f}/{t['thickness_ratio']:.3f} | "
                  f"{dz:+.2f} {ds:+.2f} {'OK' if ok else ''}")
        history.append({"iter": n, "rows": rows})
        if all_ok:
            converged = True
            break
        if n == a.max_iter:
            break
        adj_z = any(abs(r[2]) > SWEEP_SKEW_TRIGGER_MM for r in rows)
        adj_s = any(abs(r[3]) > SWEEP_SKEW_TRIGGER_MM for r in rows)
        new_st = []
        for i, s in enumerate(stations):
            if built[i] is None:
                # root: pseudo-measurement that carries the first measurable station's residual
                b0, t0, tr = built[1], targets[1], targets[i]
                bb = {"chord_mm": tr["chord_mm"] * b0["chord_mm"] / t0["chord_mm"],
                      "stagger_deg": tr["stagger_deg"] + b0["stagger_deg"] - t0["stagger_deg"],
                      "camber_ratio": tr["camber_ratio"] * b0["camber_ratio"] / t0["camber_ratio"],
                      "camber_pos": tr["camber_pos"] + b0["camber_pos"] - t0["camber_pos"],
                      "thickness_ratio": tr["thickness_ratio"] * b0["thickness_ratio"]
                      / t0["thickness_ratio"]}
                ns, hit = update_station(s, bb, tr)
            else:
                row = [r for r in rows if r[0] == i][0]
                ns, hit = update_station(s, built[i], targets[i], adjust_sweep=adj_z,
                                         adjust_skew=adj_s, d_le_z_mm=row[2], d_skew_mm=row[3])
            if hit:
                last_hits[i] = hit
            new_st.append(ns)
        stations = new_st
        print(f"(sweep adj={adj_z}, skew adj={adj_s}; clamp hits so far: "
              f"{ {rr_list[i]: h for i, h in last_hits.items()} or 'none'})")

    final_rows = history[-1]["rows"]
    maxres = {k: max(abs(r[1][k]) for r in final_rows) for k in TOL}
    print(f"\nconverged={converged} iterations={len(history)} max |residual|: "
          + ", ".join(f"{k}={v:.4f}" for k, v in maxres.items()))
    print("clamp hits:", {rr_list[i]: h for i, h in last_hits.items()} or "none")

    body = [ln for ln in STOCK.read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]
    body = body[: body.index("stations:")]
    body = [ln for ln in body if not ln.startswith("section_wrap:")] + [f"section_wrap: {a.wrap}"]
    hdr = [
        f"# a12x25_reference_v3 ({a.wrap} sections) -- Stock recipe refitted so BUILT blade sections "
        "match the close-ref STL.",
        "# v2 (planar sections, 2026-10-08) is kept as config/problems/a12x25_reference_planar.yaml.",
        f"# Fit provenance: {dt.date.today().isoformat()}, scripts/fit_recipe_to_stl.py, "
        f"{len(history)} iteration(s) (last = measured, not updated), damping {DAMPING}, "
        f"converged={converged}.",
        f"# Source STL: validation/reference/a12x25_impeller.stl (start: {STOCK.name}, unmodified).",
        "# Final max |built - ref| at measured stations: "
        + ", ".join(f"{k} {v:.4f}" for k, v in maxres.items())
        + " (tol: stagger 1.5 deg, chord 3%, camber 0.005, t/c 10%).",
        "# Station radii r/R = " + ", ".join(f"{x:.3f}" for x in rr_list)
        + " (root = extrapolated, tip fitted at r/R 0.99).",
        "# Sweep/skew/lean/le_*, hub and tip fields are the Stock values (interpolated to the new "
        "stations) unless the LE-offset trigger fired; see the fit log.",
        "# Built-vs-reference table: docs/validation/recipe_fidelity/section_compare_v2.md",
    ]
    lines = hdr + body + ["stations:"]
    for s in stations:
        lines.append("  - {" + ", ".join(f"{k}: {round(s[k], 4)}" for k in YAML_KEYS) + "}")
    OUT.write_text("\n".join(lines) + "\n")
    print("wrote", OUT)
    return 0 if converged else 1


if __name__ == "__main__":
    raise SystemExit(main())
