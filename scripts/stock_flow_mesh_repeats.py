"""Stock v3 Assess on five varied meshes for the flow-card thresholds (roadmap 27.3b).

Pre-register (written first): docs/validation/audits/2026-10-15-stock-flow-mesh-repeats-prereg.md
Same setup and 2σ rule as scripts/stock_flow_repeats.py; only base_cell varies. Writes
runs/stock_flow_mesh_repeats/summary.json. Does not edit fansim/cfd/flow_verdicts.py.

    python scripts/stock_flow_mesh_repeats.py
    python scripts/stock_flow_mesh_repeats.py --analyze
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from stock_flow_repeats import proposed_tolerances  # noqa: E402

BASE_CELLS = {"m1": 0.0056, "m2": 0.0058, "m3": 0.0062, "m4": 0.0064, "m5": 0.0066}
CURRENT_BAND_TOL, CURRENT_NOISE_DB = 0.03, 0.5
STOP_BAND_TOL, STOP_NOISE_DB = 0.15, 3.0
OUT = ROOT / "runs" / "stock_flow_mesh_repeats"


def _run_one(flat: dict, case: Path, base_cell: float) -> dict:
    from fansim.cfd.flow_report_case import load_or_compute_metrics
    from fansim.fan_spec import get_fan_spec
    from fansim.geometry.features import features_from_flat
    from fansim.optimize.isolated_eval import evaluate_candidate_isolated
    from fansim.optimize.presets import assess_load

    wall_s = None
    if not (case / "_eval_result.json").is_file():
        case.mkdir(parents=True, exist_ok=True)
        load_pa, _ = assess_load("case")
        t0 = time.monotonic()
        evaluate_candidate_isolated(
            flat, features_from_flat(flat), case, spec=get_fan_spec("a12x25"), procs=8,
            base_cell=base_cell, iters=500, load_pa=load_pa, refine_op=False, material="PETG",
            parallel_mesh=True)
        wall_s = round(time.monotonic() - t0, 1)
    raw = json.loads((case / "_eval_result.json").read_text(encoding="utf-8"))
    m = load_or_compute_metrics(case)
    return {"id": case.name, "base_cell": base_cell, "metrics": m.to_dict(), "wall_s": wall_s,
            "cfm_free": raw.get("cfm_free"), "cfm_load": raw.get("cfm_load"),
            "surf_max": (raw.get("raw") or {}).get("surf_max"), "feasible": raw.get("feasible")}


def _summary(rows: list[dict]) -> dict:
    ok = [r for r in rows if r.get("feasible") and r.get("metrics")]
    out: dict = {"n_ok": len(ok), "n": len(rows), "runs": rows}
    if len(ok) < 5:
        return out
    mean_dp0 = [float(r["metrics"]["mean_dp0_pa"]) for r in ok]
    bands = [list(r["metrics"]["band_dp0_pa"]) for r in ok]
    noise_raw = [r["metrics"].get("noise_swl_db") for r in ok]
    noise = None if any(v is None for v in noise_raw) else [float(v) for v in noise_raw]
    band_tol, noise_db = proposed_tolerances(mean_dp0, bands, noise)
    out.update(proposed_BAND_TOL=band_tol, proposed_NOISE_MARGIN_DB=noise_db,
               new_BAND_TOL=max(CURRENT_BAND_TOL, band_tol),
               new_NOISE_MARGIN_DB=max(CURRENT_NOISE_DB, noise_db or 0.0),
               stop_and_ask=bool(band_tol > STOP_BAND_TOL
                                 or (noise_db is not None and noise_db > STOP_NOISE_DB)),
               mean_dp0_pa=mean_dp0, noise_swl_db=noise_raw,
               cfm_free=[r["cfm_free"] for r in ok], cfm_load=[r["cfm_load"] for r in ok])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"stock_flow_mesh_repeats pid={os.getpid()} analyze={args.analyze}", flush=True)
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25")
    rows: list[dict] = []
    for rid, cell in BASE_CELLS.items():
        case = OUT / rid
        if args.analyze and not (case / "_eval_result.json").is_file():
            print(f"{rid} missing", flush=True)
            continue
        print(f"{rid} base_cell={cell} ...", flush=True)
        try:
            rec = _run_one(flat, case, cell)
        except Exception as exc:  # noqa: BLE001 — a failed eval stops the campaign (prereg)
            rec = {"id": rid, "base_cell": cell, "error": f"{type(exc).__name__}: {exc}"[:400]}
            (OUT / "summary.json").write_text(json.dumps({"stopped": rec, "runs": rows}, indent=1),
                                              encoding="utf-8")
            print(f"{rid} ERR {rec['error']}", flush=True)
            return 1
        rows.append(rec)
        print(f"{rid} OK mean_dp0={rec['metrics'].get('mean_dp0_pa')} "
              f"noise={rec['metrics'].get('noise_swl_db')} cfm={rec['cfm_free']}/{rec['cfm_load']} "
              f"surf_max={rec['surf_max']}", flush=True)
        (OUT / "summary.json").write_text(json.dumps(_summary(rows), indent=1), encoding="utf-8")
    s = _summary(rows)
    (OUT / "summary.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in s.items() if k != "runs"}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    os._exit(rc)
