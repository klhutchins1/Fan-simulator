"""Five Stock v3 Assess repeats for flow-card 2σ (roadmap 27.3).

Pre-register (written first): docs/validation/audits/2026-10-13-stock-flow-repeats-prereg.md
Writes proposed BAND_TOL / NOISE_MARGIN_DB to runs/stock_flow_repeats/summary.json.
Bake (2026-10-14): fansim/cfd/flow_verdicts.py is 0.03 / 0.5 dB. This runner does not edit it.

    uv run python scripts/stock_flow_repeats.py
    uv run python scripts/stock_flow_repeats.py --analyze
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

N_REPEATS = 5
BAND_FLOOR = 0.02
NOISE_FLOOR_DB = 0.5
BAND_MEAN_MIN_PA = 1.0
OUT = ROOT / "runs" / "stock_flow_repeats"


def ceil_2dp(x: float) -> float:
    return math.ceil(x * 100.0 - 1e-12) / 100.0


def ceil_1dp(x: float) -> float:
    return math.ceil(x * 10.0 - 1e-12) / 10.0


def sample_std(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        raise ValueError("need at least two values for sample σ")
    mu = sum(xs) / n
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))


def _two_sigma_rel(xs: list[float]) -> float | None:
    mu = sum(xs) / len(xs)
    if abs(mu) <= BAND_MEAN_MIN_PA:
        return None
    return 2.0 * sample_std(xs) / abs(mu)


def proposed_tolerances(
    mean_dp0: list[float],
    bands: list[list[float]],
    noise_db: list[float] | None,
) -> tuple[float, float | None]:
    """BAND_TOL and NOISE_MARGIN_DB from the pre-registered 2σ rule. noise_db None → skip noise."""
    if len(mean_dp0) < 2:
        raise ValueError("need at least two repeats")
    rels = [_two_sigma_rel(mean_dp0)]
    n_bands = len(bands[0]) if bands else 0
    for k in range(n_bands):
        rels.append(_two_sigma_rel([row[k] for row in bands]))
    kept = [r for r in rels if r is not None]
    band_tol = max(BAND_FLOOR, ceil_2dp(max(kept))) if kept else BAND_FLOOR
    noise = None
    if noise_db is not None:
        if len(noise_db) != len(mean_dp0) or any(v is None for v in noise_db):
            raise ValueError("noise_db must match the repeats and have no missing values")
        noise = max(NOISE_FLOOR_DB, ceil_1dp(2.0 * sample_std([float(v) for v in noise_db])))
    return band_tol, noise


def _run_one(flat: dict, case: Path) -> dict:
    from fansim.fan_spec import get_fan_spec
    from fansim.geometry.features import features_from_flat
    from fansim.optimize.isolated_eval import evaluate_candidate_isolated
    from fansim.optimize.presets import assess_load

    if not (case / "_eval_result.json").is_file():
        case.mkdir(parents=True, exist_ok=True)
        load_pa, _ = assess_load("case")
        t0 = time.monotonic()
        evaluate_candidate_isolated(
            flat, features_from_flat(flat), case, spec=get_fan_spec("a12x25"), procs=8,
            base_cell=0.006, iters=500, load_pa=load_pa, refine_op=False, material="PETG",
            parallel_mesh=True)
        wall_s = round(time.monotonic() - t0, 1)
    else:
        wall_s = None
    from fansim.cfd.flow_report_case import load_or_compute_metrics

    m = load_or_compute_metrics(case)
    rec = {"id": case.name, "metrics": m.to_dict(), "wall_s": wall_s}
    raw = json.loads((case / "_eval_result.json").read_text(encoding="utf-8"))
    rec["cfm_free"] = raw.get("cfm_free")
    rec["cfm_load"] = raw.get("cfm_load")
    rec["feasible"] = raw.get("feasible")
    return rec


def _summary(rows: list[dict]) -> dict:
    ok = [r for r in rows if r.get("feasible") and r.get("metrics")]
    out: dict = {"n_ok": len(ok), "n": len(rows), "repeats": rows}
    if len(ok) < 2:
        return out
    mean_dp0 = [float(r["metrics"]["mean_dp0_pa"]) for r in ok]
    bands = [list(r["metrics"]["band_dp0_pa"]) for r in ok]
    noise_raw = [r["metrics"].get("noise_swl_db") for r in ok]
    noise = None if any(v is None for v in noise_raw) else [float(v) for v in noise_raw]
    band_tol, noise_db = proposed_tolerances(mean_dp0, bands, noise)
    out["proposed_BAND_TOL"] = band_tol
    out["proposed_NOISE_MARGIN_DB"] = noise_db
    out["mean_dp0_pa"] = mean_dp0
    out["noise_swl_db"] = noise_raw
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze", action="store_true", help="tolerances from cases already on disk")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    summary_path = OUT / "summary.json"
    print(f"stock_flow_repeats pid={os.getpid()} analyze={args.analyze}", flush=True)
    from fansim.optimize.search_space import stock_blade_flat

    flat = stock_blade_flat("a12x25")
    rows = []
    for i in range(1, N_REPEATS + 1):
        case = OUT / f"r{i}"
        if args.analyze and not (case / "_eval_result.json").is_file():
            print(f"r{i} missing", flush=True)
            continue
        print(f"r{i} ...", flush=True)
        try:
            rec = _run_one(flat, case)
        except Exception as exc:  # noqa: BLE001
            rec = {"id": f"r{i}", "error": f"{type(exc).__name__}: {exc}"[:400]}
            (OUT / "summary.json").write_text(
                json.dumps({"stopped": rec, "repeats": rows}, indent=1), encoding="utf-8")
            print(f"r{i} ERR {rec['error']}", flush=True)
            return 1
        rows.append(rec)
        print(
            f"r{i} OK mean_dp0={rec['metrics'].get('mean_dp0_pa')} "
            f"noise={rec['metrics'].get('noise_swl_db')} "
            f"cfm={rec.get('cfm_free')}/{rec.get('cfm_load')}",
            flush=True)
        summary_path.write_text(json.dumps(_summary(rows), indent=1), encoding="utf-8")
    summary = _summary(rows)
    summary_path.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(
        f"DONE n_ok={summary.get('n_ok')} "
        f"BAND_TOL={summary.get('proposed_BAND_TOL')} "
        f"NOISE_MARGIN_DB={summary.get('proposed_NOISE_MARGIN_DB')}",
        flush=True)
    return 0 if summary.get("n_ok") == N_REPEATS else 2


if __name__ == "__main__":
    raise SystemExit(main())
