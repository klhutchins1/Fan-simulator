"""Audit #8: prop CFD direction + validation on the UIUC APC Slow Flyer 9x4.7 static point.

The prop is built from the UIUC measured geometry (r/R, c/R, beta; generic 6 % section, camber
0.04 -- the same approximation the BEMT audit uses), solved open-air at the UIUC static RPM with
the production path (``evaluate_prop_cfd``, builder direction). The same flipped STL is then
solved with the spin reversed.

Rules, fixed before any run:
  direction PASS  designed thrust points the designed way (thrust_sign_ok), both solves converged,
                  and designed beats reversed by >= 1.10x on |thrust| per watt.
  validation PASS designed C_T within +-15 % and C_P within +-20 % of UIUC (the BEMT audit's
                  pre-registered static tolerances). Geometry is approximate, so a miss may be
                  section shape, not solver.

Usage:
    uv run python scripts/audit_prop_cfd.py --pilot
    uv run python scripts/audit_prop_cfd.py
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.openfoam_case import MeshResolution  # noqa: E402
from fansim.cfd.runner import image_available  # noqa: E402
from fansim.cfd.timing import mesh_cells, pilot_iters, write_pilot_json  # noqa: E402
from fansim.prop_spec import PropShaftMount, PropSpec  # noqa: E402
from fansim.propeller.bemt_catalog import (  # noqa: E402
    UIUC_DIR,
    load_uiuc_geometry_blade,
    load_uiuc_static_fixture,
)
from fansim.propeller.cfd import P_INF, T_INF, evaluate_prop_cfd  # noqa: E402
from fansim.physics.air import R_AIR  # noqa: E402

CT_TOL, CP_TOL = 0.15, 0.20      # pre-registered (tests/audit/test_prop_bemt_audit.py)
MIN_RATIO = 1.10
MAX_SURF_LEVEL = 5                # cap snappy surface level (base 8 mm -> 0.25 mm at the blade)
OUT = ROOT / "docs" / "validation" / "audits" / "prop_cfd_apcsf_9x4.7.json"


def apc_setup():
    fx = load_uiuc_static_fixture()
    dia_in = float(fx["diameter_in"])
    blade = load_uiuc_geometry_blade(UIUC_DIR / "apcsf_9x4.7_geom.txt", dia_in)
    hub_dia = 2.0 * float(blade.hub_radius)
    spec = PropSpec(name="apcsf_9x4.7", diameter_in=dia_in, pitch_in=float(fx["pitch_in"]),
                    n_blades=2, shaft=PropShaftMount(shaft_dia_mm=0.0, hub_bore_dia_mm=0.0,
                                                     hub_dia_mm=hub_dia),
                    rpm_max=10000.0)
    return fx, blade, spec


def mesh_for(blade, base_cell: float) -> MeshResolution:
    from fansim.geometry.blade import min_blade_wall_mm

    m = MeshResolution.for_blade(base_cell, float(min_blade_wall_mm(blade)))
    lvl = min(m.surf_max, MAX_SURF_LEVEL)
    return MeshResolution(base_cell=base_cell, surf_min=max(1, lvl - 1), surf_max=lvl,
                          feature_level=lvl)


def coeffs(res: dict, fx: dict) -> dict:
    """C_T, C_P from a CFD result in the UIUC normalisation (rho = CFD freestream density)."""
    rho = P_INF / (R_AIR * T_INF)
    n = float(fx["rpm"]) / 60.0
    d = float(fx["diameter_in"]) * 0.0254
    ct = float(res["thrust_n"]) / (rho * n * n * d ** 4)
    cp = float(res["shaft_power_w"]) / (rho * n ** 3 * d ** 5)
    return {"ct": ct, "cp": cp, "e_ct": ct / fx["ct"] - 1.0, "e_cp": cp / fx["cp"] - 1.0,
            "rho": rho}


def direction_verdict(des: dict | None, rev: dict | None) -> dict:
    if not des or not rev:
        return {"verdict": "INCONCLUSIVE", "why": "a solve is missing"}
    if not des.get("thrust_sign_ok"):
        return {"verdict": "FAIL", "why": "designed rotation pushes air the wrong way"}
    if not (des.get("converged") and rev.get("converged")):
        return {"verdict": "INCONCLUSIVE", "why": "a solve did not converge"}
    d_tpw = abs(des["thrust_n"]) / des["shaft_power_w"]
    r_tpw = abs(rev["thrust_n"]) / rev["shaft_power_w"] if rev["shaft_power_w"] > 0 else 0.0
    out = {"thrust_per_w_designed": d_tpw, "thrust_per_w_reversed": r_tpw}
    if d_tpw >= MIN_RATIO * r_tpw:
        return {"verdict": "PASS", **out}
    return {"verdict": "FAIL" if r_tpw > d_tpw else "INCONCLUSIVE", **out}


def validation_verdict(c: dict | None, converged: bool) -> dict:
    if c is None:
        return {"verdict": "INCONCLUSIVE", "why": "no designed result"}
    if not converged:
        return {"verdict": "INCONCLUSIVE", "why": "designed solve did not converge", **c}
    ok = abs(c["e_ct"]) <= CT_TOL and abs(c["e_cp"]) <= CP_TOL
    return {"verdict": "PASS" if ok else "FAIL", "ct_tol": CT_TOL, "cp_tol": CP_TOL, **c}


def _solver_clock_s(case: Path) -> float | None:
    """Solver wall time from the last 'ClockTime = N s' in the solve log."""
    for log in sorted((case / "logs").glob("*.log")):
        text = log.read_text(encoding="utf-8", errors="replace")
        if "rhoSimpleFoam" in text or "ClockTime" in text:
            hits = re.findall(r"ClockTime = ([\d.]+) s", text)
            if hits:
                return float(hits[-1])
    return None


def _slim(res: dict) -> dict:
    keep = ("thrust_n", "thrust_g", "thrust_n_raw", "thrust_sign_ok", "torque_nm", "moment_z_nm",
            "shaft_power_w", "converged", "thrust_shift_pct", "torque_shift_pct",
            "thrust_oscillation_pct", "torque_oscillation_pct", "spin", "orientation",
            "direction_source", "direction_crosscheck", "tip_mach", "rpm", "u_freestream",
            "sanity", "sanity_status", "bemt_thrust_g", "wall_s", "cells")
    return {k: res.get(k) for k in keep if k in res}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--base-cell", type=float, default=0.008)
    ap.add_argument("--out", default="runs/audit_prop_cfd")
    ap.add_argument("--pilot", action="store_true")
    a = ap.parse_args(argv)
    if not image_available():
        print("SKIPPED: OpenFOAM image not available")
        return 2
    fx, blade, spec = apc_setup()
    mesh = mesh_for(blade, float(a.base_cell))
    base = Path(a.out)
    rpm = float(fx["rpm"])

    if a.pilot:
        case = base / "pilot"
        n = pilot_iters(a.iters)
        t0 = time.time()
        res = evaluate_prop_cfd(spec, case, rpm=rpm, params=blade, iters=n, procs=a.procs,
                                mesh=mesh)
        total = time.time() - t0
        solve = _solver_clock_s(case) or total * 0.7
        payload = write_pilot_json(
            case / "pilot.json", cells=mesh_cells(case), mesh_s=2 * (total - solve),
            sec_per_iter=solve / n, iters=a.iters, points=2,
            extra={"pilot_iters": n, "mesh": vars(mesh),
                   "note": "2 meshes (designed, reversed) x 1 solve each"})
        print(f"[pilot] cells={mesh_cells(case)} mesh+setup={total - solve:.0f}s "
              f"sec/iter={solve / n:.2f} -> full ~{payload['estimated_full_run_eta']} "
              f"(pilot thrust {res.get('thrust_g'):.0f} g, P {res.get('shaft_power_w'):.1f} W)")
        return 0

    rows, errors = {}, []
    t0 = time.time()
    try:
        des = evaluate_prop_cfd(spec, base / "designed", rpm=rpm, params=blade, iters=a.iters,
                                procs=a.procs, mesh=mesh)
        des["wall_s"], des["cells"] = time.time() - t0, mesh_cells(base / "designed")
        rows["designed"] = des
        print(f"[designed] {des['thrust_g']:.0f} g  {des['shaft_power_w']:.1f} W  "
              f"conv={des['converged']} sanity={des['sanity_status']}", flush=True)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"designed: {type(exc).__name__}: {exc}")
        print(errors[-1], flush=True)
    if "designed" in rows:
        t1 = time.time()
        try:
            rev = evaluate_prop_cfd(spec, base / "reversed", rpm=rpm,
                                    stl_mm=base / "designed" / "prop_cfd.stl", prepare_stl=False,
                                    direction="manual", spin=-int(rows["designed"]["spin"]),
                                    iters=a.iters, procs=a.procs, mesh=mesh)
            rev["wall_s"], rev["cells"] = time.time() - t1, mesh_cells(base / "reversed")
            rows["reversed"] = rev
            print(f"[reversed] {rev['thrust_g']:.0f} g  {rev['shaft_power_w']:.1f} W  "
                  f"conv={rev['converged']}", flush=True)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"reversed: {type(exc).__name__}: {exc}")
            print(errors[-1], flush=True)

    des, rev = rows.get("designed"), rows.get("reversed")
    c = coeffs(des, fx) if des else None
    payload = {
        "prop": "APC SF 9x4.7 (UIUC geometry, approximate section)", "uiuc": fx,
        "rpm": rpm, "iters": a.iters, "mesh": vars(mesh),
        "rows": {k: _slim(v) for k, v in rows.items()}, "errors": errors,
        "direction": direction_verdict(des, rev),
        "validation": validation_verdict(c, bool(des and des.get("converged"))),
    }
    OUT.write_text(json.dumps(payload, indent=2, default=str, allow_nan=False) + "\n",
                   encoding="utf-8")
    print(f"\nDIRECTION {payload['direction']}\nVALIDATION {payload['validation']}\n-> {OUT}")
    return 3 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
