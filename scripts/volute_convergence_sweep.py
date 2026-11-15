"""R2.5a volute convergence sweep: SIMPLE relaxation variants on the existing volute case.

Pre-registered in docs/validation/audits/2026-11-13-volute-convergence-sweep-prereg.md. Judged only on the
step-1 convergence gate of 2026-10-18-cror-centrifugal-validation-prereg.md, never against the paper.

Units = mesh (coarse 0.006 m / fine 0.004 m) x variant (V0/V1/V2) x point (free 0 Pa, load 50 Pa), each solved
with the default VoluteParams at DEFAULT_VOLUTE_RPM. One mesh per base cell, reused for every solve on it.
Writes <out>/progress.json after every unit and <out>/summary.json; resumable (solved units are skipped);
never starts a unit at or after 15:30 local.

Usage (night queue):
    python -u scripts/volute_convergence_sweep.py --out runs/volute_conv_r25a
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, run_mesh, run_solve  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.cfd.sanity import run_sanity  # noqa: E402

VARIANTS = {
    "V0": {"p": 0.3, "U": 0.7, "turb": 0.7},    # today's shared defaults, only more iterations
    "V1": {"p": 0.2, "U": 0.5, "turb": 0.5},
    "V2": {"p": 0.15, "U": 0.3, "turb": 0.3},
}
MESHES = {"coarse": 0.006, "fine": 0.004}
POINTS = {"free": 0.0, "load50": 50.0}
OSC_MAX_PCT = 5.0       # step 1: peak-to-peak over the last 20 % of iterations
MASS_MAX_FRAC = 0.01    # step 1: mass imbalance <= 1 %
CUTOFF = (15, 30)


def _finite(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def past_cutoff(now: datetime | None = None) -> bool:
    t = now or datetime.now()
    return (t.hour, t.minute) >= CUTOFF


def gate(row: dict) -> str:
    """Step-1 verdict for one unit: PASS / INCONCLUSIVE."""
    osc, mass = row.get("oscillation_pct"), row.get("mass_imbalance")
    if osc is None or mass is None:
        return "INCONCLUSIVE"
    return "PASS" if (osc <= OSC_MAX_PCT and abs(mass) <= MASS_MAX_FRAC) else "INCONCLUSIVE"


def choose(units: dict) -> dict:
    """Pre-registered choice: the least-damped variant (V0 < V1 < V2) that passes every unit on a mesh."""
    out = {}
    for mesh in MESHES:
        pick = None
        for v in VARIANTS:
            rows = [units.get(f"{mesh}_{v}_{pt}") for pt in POINTS]
            if all(r and r.get("gate") == "PASS" for r in rows):
                pick = v
                break
        complete = all(units.get(f"{mesh}_{v}_{pt}") for v in VARIANTS for pt in POINTS)
        out[mesh] = pick or ("none" if complete else "incomplete")
    return out


def _mass_imbalance(checks) -> float | None:
    for c in checks:
        if c.name == "mass_balance":
            return _finite(c.value)
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "runs" / "volute_conv_r25a")
    ap.add_argument("--iters", type=int, default=3000)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--meshes", nargs="+", default=list(MESHES), choices=list(MESHES))
    ap.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=list(VARIANTS))
    a = ap.parse_args(argv)

    from fansim.volute.case import build_volute_case
    from fansim.volute.domain import DEFAULT_VOLUTE_RPM, domain_for_volute
    from fansim.volute.geometry import VoluteParams, export_volute_stls

    out = a.out if a.out.is_absolute() else ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    summ_path = out / "summary.json"
    summary = json.loads(summ_path.read_text(encoding="utf-8")) if summ_path.is_file() else {}
    summary.update({"prereg": "docs/validation/audits/2026-11-13-volute-convergence-sweep-prereg.md",
                    "rpm": DEFAULT_VOLUTE_RPM, "iters": a.iters, "variants": VARIANTS,
                    "meshes": MESHES, "points": POINTS})
    units = summary.setdefault("units", {})

    def save(progress: dict) -> None:
        summary["choice"] = choose(units)
        summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (out / "progress.json").write_text(json.dumps(progress, indent=2), encoding="utf-8")

    if not image_available():
        print("OpenFOAM image not available; nothing solved.", flush=True)
        save({"stopped": "no OpenFOAM image"})
        return 2

    params = VoluteParams()
    domain = domain_for_volute(params, rpm=DEFAULT_VOLUTE_RPM)
    for mesh_name in a.meshes:
        base_cell = MESHES[mesh_name]
        todo = [(v, pt) for v in a.variants for pt in POINTS if f"{mesh_name}_{v}_{pt}" not in units]
        if not todo:
            continue
        case = out / f"case_{mesh_name}"
        mesh_res = MeshResolution(base_cell=base_cell)
        runner = OpenFOAMRunner(case)
        if not (case / "constant" / "polyMesh" / "owner").is_file():
            if past_cutoff():
                save({"stopped": "cutoff", "next": f"mesh {mesh_name}"})
                return 0
            save({"current": f"mesh {mesh_name}", "start": time.time()})
            imp, cas = export_volute_stls(params, case)
            build_volute_case(case, imp, cas, domain, mesh=mesh_res, n_iters=a.iters,
                              n_subdomains=a.procs, back_pressure_pa=0.0)
            t0 = time.time()
            run_mesh(runner)
            summary.setdefault("mesh_s", {})[mesh_name] = time.time() - t0
        imp, cas = case / "impeller.stl", case / "casing.stl"
        for v, pt in todo:
            tag = f"{mesh_name}_{v}_{pt}"
            if past_cutoff():
                save({"stopped": "cutoff", "next": tag})
                print("stopped before 15:30 local; remaining units left for another run", flush=True)
                return 0
            save({"current": tag, "start": time.time()})
            build_volute_case(case, imp, cas, domain, mesh=mesh_res, n_iters=a.iters,
                              n_subdomains=a.procs, back_pressure_pa=POINTS[pt], relax=VARIANTS[v])
            t0 = time.time()
            row: dict = {"mesh": mesh_name, "variant": v, "point": pt, "back_pressure_pa": POINTS[pt]}
            try:
                run_solve(runner, n_procs=a.procs)
                m = parse_fan_metrics(case, omega_rad_s=domain.omega_rad_s)
                checks = run_sanity(case, metrics=m, omega_signed=domain.omega_signed)
                row.update({
                    "cfm": _finite(m.cfm), "oscillation_pct": _finite(m.oscillation_pct),
                    "flow_drift_pct": _finite(m.flow_drift_pct), "converged": bool(m.converged),
                    "static_pressure_rise_pa": _finite(m.static_pressure_rise_pa),
                    "torque_nm": _finite(m.torque_nm), "mass_imbalance": _mass_imbalance(checks),
                    "sanity": [asdict(c) for c in checks],
                })
            except Exception as exc:  # noqa: BLE001  (a failed solve is recorded, not fatal)
                row["error"] = f"{type(exc).__name__}: {exc}"
            row["wall_s"] = time.time() - t0
            row["gate"] = gate(row)
            pp = case / "postProcessing"
            if pp.is_dir():
                shutil.copytree(pp, out / "postProcessing" / tag, dirs_exist_ok=True)
            units[tag] = row
            print(f"[{tag}] osc {row.get('oscillation_pct')} % mass {row.get('mass_imbalance')} "
                  f"-> {row['gate']} ({row['wall_s']:.0f} s)", flush=True)
            save({"done": tag})
    save({"finished": True})
    print(f"choice: {summary['choice']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
