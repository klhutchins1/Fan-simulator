"""Audit #7, proof 3: designed vs reversed rotation in CFD for mixed-flow and volute rotors.

One mesh per machine (the production CFD setup: mixed-flow flipped copy in the A12x25 duct; volute
in its sealed scroll), then free-air solves at spin -1 and +1 on that same mesh. Same geometry,
same mesh, only the rotation changes, so the comparison carries no mesh or domain bias.

Verdict (fixed before any run):
  PASS    designed CFM > 0, designed beats reversed by >= MIN_RATIO on CFM *and* on CFM per watt,
          both solves converged.
  FAIL    reversed beats designed on CFM (the convention is wrong).
  INCONCLUSIVE otherwise (small margin, unconverged, solve failed).

Usage:
    uv run python scripts/audit_archetype_direction_cfd.py --machine mixed --pilot
    uv run python scripts/audit_archetype_direction_cfd.py --machine volute
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, run_mesh, run_solve  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.cfd.sanity import overall as sanity_overall, run_sanity  # noqa: E402
from fansim.cfd.timing import mesh_cells, pilot_iters, write_pilot_json  # noqa: E402

MIN_RATIO = 1.10   # designed must beat reversed by >= 10% on CFM and on CFM/W
OUT_DIR = ROOT / "docs" / "validation" / "audits"


def _finite(v):
    return v if isinstance(v, (int, float)) and math.isfinite(v) else None


def verdict(designed: dict | None, reversed_: dict | None) -> dict:
    """Pure verdict from two result rows (see module docstring)."""
    if not designed or not reversed_:
        return {"verdict": "INCONCLUSIVE", "why": "a solve is missing"}
    d_cfm, r_cfm = designed.get("cfm"), reversed_.get("cfm")
    if d_cfm is None or r_cfm is None:
        return {"verdict": "INCONCLUSIVE", "why": "a solve has no CFM"}
    if abs(r_cfm) > abs(d_cfm) and r_cfm > 0:
        return {"verdict": "FAIL", "why": f"reversed {r_cfm:.1f} CFM beats designed {d_cfm:.1f}"}
    if d_cfm <= 0:
        return {"verdict": "FAIL", "why": f"designed rotation does not deliver ({d_cfm:.1f} CFM)"}
    if not (designed.get("converged") and reversed_.get("converged")):
        return {"verdict": "INCONCLUSIVE", "why": "a solve did not converge"}
    ratio = d_cfm / r_cfm if r_cfm > 0 else math.inf
    d_pw = d_cfm / designed["shaft_power_w"] if designed.get("shaft_power_w") else None
    r_pw = (r_cfm / reversed_["shaft_power_w"]
            if reversed_.get("shaft_power_w") and r_cfm > 0 else 0.0)
    out = {"cfm_ratio": ratio, "cfm_per_w_designed": d_pw, "cfm_per_w_reversed": r_pw}
    if ratio >= MIN_RATIO and d_pw is not None and d_pw >= MIN_RATIO * r_pw:
        return {"verdict": "PASS", **out}
    return {"verdict": "INCONCLUSIVE", "why": f"margin below {MIN_RATIO:.2f}x", **out}


# ----------------------------------------------------------------------------- machines
def setup_mixed(work: Path, base_cell: float):
    """Production mixed-flow CFD setup (matches evaluate_mixed_flow), returns a case adapter."""
    from fansim.centrifugal.evaluate import (
        _frame_blade_proxy,
        remaining_mixed_tip_gap_mm,
        rig_for_mixed_flow,
    )
    from fansim.centrifugal.geometry import MixedFlowParams, export_mixed_flow_stl
    from fansim.cfd.casing import export_casing_stl
    from fansim.cfd.frame import export_frame_stl
    from fansim.cfd.openfoam_case import build_case
    from fansim.cfd.orientation import prepare_axial_cfd
    from fansim.fan_spec import A12X25

    params = MixedFlowParams()
    casing_id = float(A12X25.tip_dia_mm[1])
    stl = export_mixed_flow_stl(params, work / "impeller.stl")
    rig = rig_for_mixed_flow(params, tip_gap_mm=remaining_mixed_tip_gap_mm(params, casing_id),
                             casing_id_mm=casing_id, rpm=A12X25.rpm,
                             inlet_diameters=2.0, outlet_diameters=4.0)
    stl, rig = prepare_axial_cfd(stl, rig, work, source="builder")
    frame = export_frame_stl(_frame_blade_proxy(params, A12X25.rpm), rig, work / "frame.stl")
    casing = export_casing_stl(rig, work / "casing.stl", stepped=False)
    mesh_res = MeshResolution(base_cell=base_cell)
    designed_spin = rig.spin

    def write(spin: int, iters: int, procs: int):
        r = replace(rig, spin=spin)
        build_case(work, stl, r, mesh=mesh_res, n_iters=iters, n_subdomains=procs,
                   back_pressure_pa=0.0, frame_stl_mm=frame, casing_stl_mm=casing)
        return r.omega_rad_s, r.omega_signed

    return {"params": asdict(params), "designed_spin": designed_spin, "write": write,
            "rpm": A12X25.rpm, "mesh": asdict(mesh_res)}


def setup_volute(work: Path, base_cell: float):
    """Production volute CFD setup (matches evaluate_volute), returns a case adapter."""
    from fansim.volute.case import build_volute_case
    from fansim.volute.domain import DEFAULT_VOLUTE_RPM, VOLUTE_SPIN, domain_for_volute
    from fansim.volute.geometry import VoluteParams, export_volute_stls

    params = VoluteParams()
    imp, cas = export_volute_stls(params, work)
    mesh_res = MeshResolution(base_cell=base_cell)

    def write(spin: int, iters: int, procs: int):
        dom = domain_for_volute(params, rpm=DEFAULT_VOLUTE_RPM, spin=spin)
        build_volute_case(work, imp, cas, dom, mesh=mesh_res, n_iters=iters,
                          n_subdomains=procs, back_pressure_pa=0.0)
        return dom.omega_rad_s, dom.omega_signed

    return {"params": asdict(params), "designed_spin": VOLUTE_SPIN, "write": write,
            "rpm": DEFAULT_VOLUTE_RPM, "mesh": asdict(mesh_res)}


MACHINES = {"mixed": (setup_mixed, 0.005), "volute": (setup_volute, 0.006)}


def solve_row(case: Path, runner, setup, spin: int, iters: int, procs: int) -> dict:
    omega, omega_signed = setup["write"](spin, iters, procs)
    t0 = time.time()
    run_solve(runner, n_procs=procs)
    wall = time.time() - t0
    m = parse_fan_metrics(case, omega_rad_s=omega)
    checks = run_sanity(case, metrics=m, omega_signed=omega_signed)
    return {
        "spin": spin, "designed": spin == setup["designed_spin"],
        "cfm": _finite(m.cfm), "converged": bool(m.converged),
        "flow_drift_pct": _finite(m.flow_drift_pct), "oscillation_pct": _finite(m.oscillation_pct),
        "shaft_power_w": _finite(m.shaft_power_w), "eta_total": _finite(m.eta_total),
        "moment_z_nm": _finite(m.moment_z_nm), "omega_signed": omega_signed,
        "sanity_status": sanity_overall(checks), "sanity": [asdict(c) for c in checks],
        "wall_s": wall, "sec_per_iter": wall / iters if iters else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--machine", choices=sorted(MACHINES), required=True)
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--base-cell", type=float, default=None)
    ap.add_argument("--out", default="runs/audit_archetype_direction")
    ap.add_argument("--pilot", action="store_true",
                    help="mesh once, solve the designed spin at max(50, iters//10) iterations, "
                         "write <out>/<machine>/pilot.json with the full-run estimate, then exit")
    a = ap.parse_args(argv)
    if not image_available():
        print("SKIPPED: OpenFOAM image not available")
        return 2
    setup_fn, default_cell = MACHINES[a.machine]
    case = Path(a.out) / a.machine
    case.mkdir(parents=True, exist_ok=True)
    setup = setup_fn(case, float(a.base_cell or default_cell))
    runner = OpenFOAMRunner(case)
    designed = setup["designed_spin"]

    n_first = pilot_iters(a.iters) if a.pilot else a.iters
    setup["write"](designed, n_first, a.procs)
    t0 = time.time()
    run_mesh(runner)
    mesh_s = time.time() - t0
    print(f"[{a.machine}] meshed in {mesh_s:.0f}s ({mesh_cells(case)} cells)", flush=True)

    if a.pilot:
        row = solve_row(case, runner, setup, designed, n_first, a.procs)
        payload = write_pilot_json(
            case / "pilot.json", cells=mesh_cells(case), mesh_s=mesh_s,
            sec_per_iter=row["sec_per_iter"] or 0.0, iters=a.iters, points=2,
            extra={"pilot_iters": n_first, "note": "1 mesh x 2 solves (designed, reversed)"})
        print(f"[pilot {a.machine}] sec/iter={row['sec_per_iter']:.3f} -> full run "
              f"~{payload['estimated_full_run_eta']}  (pilot CFM {row['cfm']})", flush=True)
        return 0

    rows, errors = [], []
    out = OUT_DIR / f"direction_cfd_{a.machine}.json"
    for spin in (designed, -designed):
        try:
            row = solve_row(case, runner, setup, spin, a.iters, a.procs)
            rows.append(row)
            print(f"[{a.machine} spin {spin:+d}{' designed' if row['designed'] else ' reversed'}] "
                  f"CFM {row['cfm']} conv={row['converged']} P={row['shaft_power_w']} W "
                  f"eta_total={row['eta_total']} sanity={row['sanity_status']}", flush=True)
        except Exception as exc:  # noqa: BLE001 - record and keep the other solve
            errors.append(f"spin {spin:+d}: {type(exc).__name__}: {exc}")
            print(errors[-1], flush=True)
        des = next((r for r in rows if r["designed"]), None)
        rev = next((r for r in rows if not r["designed"]), None)
        payload = {
            "machine": a.machine, "rpm": setup["rpm"], "iters": a.iters, "mesh": setup["mesh"],
            "cells": mesh_cells(case), "mesh_s": mesh_s, "designed_spin": designed,
            "min_ratio": MIN_RATIO, "rows": rows, "errors": errors,
            "verdict": verdict(des, rev), "params": setup["params"],
        }
        out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"\nVERDICT {payload['verdict']}\n-> {out}", flush=True)
    return 3 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
