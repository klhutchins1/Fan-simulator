"""Two real designs on Stock's five 27.3b meshes: does the flow card separate design from mesh? (27.3d/27.3c)

Pre-register (written first): docs/validation/audits/2026-10-16-design-flow-mesh-repeats-prereg.md
Same setup as scripts/stock_flow_mesh_repeats.py; Stock's runs are reused from runs/stock_flow_mesh_repeats/.
Writes runs/design_flow_mesh_repeats/summary.json. Changes no thresholds.

    python scripts/design_flow_mesh_repeats.py
    python scripts/design_flow_mesh_repeats.py --analyze
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from stock_flow_mesh_repeats import BASE_CELLS, _run_one  # noqa: E402
from stock_flow_repeats import sample_std  # noqa: E402

DESIGNS = {
    "9604": ROOT / "runs/bem_screen_r3_top5/cockpit_assess/design_9604/design.json",
    "9610": ROOT / "runs/bem_screen_r3_reserve/cockpit_assess/design_9610/design.json",
}
STOCK = ROOT / "runs" / "stock_flow_mesh_repeats"
OUT = ROOT / "runs" / "design_flow_mesh_repeats"
# metric -> "rel" (fraction of Stock) or "abs" (plain difference)
METRICS = {"cfm_free": "rel", "cfm_load": "rel", "mean_dp0_pa": "rel", "backflow_frac": "abs",
           "swirl_frac": "abs", "dead_frac": "abs", "tip_band_uz_ratio": "rel", "noise_swl_db": "abs"}


def _value(rec: dict, key: str, band: int | None = None):
    if band is not None:
        return float(rec["metrics"]["band_dp0_pa"][band])
    v = rec.get(key) if key.startswith("cfm") else rec["metrics"].get(key)
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def paired(design: list[dict], stock: list[dict], key: str, kind: str, band: int | None = None) -> dict:
    """Same-mesh differences design − Stock; 'resolved' = all one sign and |mean| > 2·sd (prereg Q1)."""
    d = []
    for a, b in zip(design, stock):
        x, y = _value(a, key, band), _value(b, key, band)
        if x is None or y is None or (kind == "rel" and y == 0):
            return {"diffs": None, "resolved": None}
        d.append((x / y - 1.0) if kind == "rel" else (x - y))
    mean, sd = sum(d) / len(d), sample_std(d)
    one_sign = all(v > 0 for v in d) or all(v < 0 for v in d)
    return {"diffs": [round(v, 5) for v in d], "mean": round(mean, 5), "sd": round(sd, 5),
            "resolved": bool(one_sign and abs(mean) > 2.0 * sd)}


def _verdicts(design_rec: dict, stock_rec: dict) -> dict:
    from fansim.cfd.flow_report import FlowMetrics
    from fansim.cfd.flow_verdicts import judge
    rows = judge(FlowMetrics.from_dict(design_rec["metrics"]), FlowMetrics.from_dict(stock_rec["metrics"]))
    return {r.key: f"{r.status}{'+' if r.better else ''}" for r in rows}


def analyze_design(design: list[dict], stock: list[dict]) -> dict:
    out: dict = {"paired": {k: paired(design, stock, k, kind) for k, kind in METRICS.items()}}
    for b in range(5):
        out["paired"][f"bar{b}"] = paired(design, stock, "band", "rel", band=b)
    same = [_verdicts(a, b) for a, b in zip(design, stock)]                        # Q2
    out["same_mesh_verdicts"] = same
    out["same_mesh_stable_rows"] = {k: len({v[k] for v in same}) == 1 for k in same[0]}
    cross = [_verdicts(a, b) for i, a in enumerate(design) for j, b in enumerate(stock) if i != j]  # Q3
    agree = {}
    for k in same[0]:
        vals = [v[k] for v in same]
        majority = max(set(vals), key=vals.count)
        agree[k] = round(sum(v[k] == majority for v in cross) / len(cross), 3)
    out["cross_mesh_agreement"] = agree
    return out


def _summary(results: dict[str, list[dict]], stock: list[dict]) -> dict:
    s: dict = {"stock_n": len(stock), "designs": {}}
    for name, rows in results.items():
        ok = [r for r in rows if r.get("feasible") and r.get("metrics")]
        entry: dict = {"n_ok": len(ok), "n": len(rows), "runs": rows}
        if len(ok) == 5 and len(stock) == 5:
            entry.update(analyze_design(ok, stock))
        else:
            entry["verdict"] = "INCONCLUSIVE (fewer than 5 OK runs)"
        s["designs"][name] = entry
    return s


def _stock_runs() -> list[dict]:
    from fansim.cfd.flow_report_case import load_or_compute_metrics
    out = []
    for rid in BASE_CELLS:
        case = STOCK / rid
        raw = json.loads((case / "_eval_result.json").read_text(encoding="utf-8"))
        out.append({"id": rid, "metrics": load_or_compute_metrics(case).to_dict(),
                    "cfm_free": raw.get("cfm_free"), "cfm_load": raw.get("cfm_load"),
                    "feasible": raw.get("feasible")})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"design_flow_mesh_repeats pid={os.getpid()} analyze={args.analyze}", flush=True)
    stock = _stock_runs()
    results: dict[str, list[dict]] = {}
    for name, jf in DESIGNS.items():
        flat = json.loads(jf.read_text(encoding="utf-8"))["params"]
        results[name] = []
        for rid, cell in BASE_CELLS.items():
            case = OUT / name / rid
            if args.analyze and not (case / "_eval_result.json").is_file():
                print(f"{name}/{rid} missing", flush=True)
                continue
            print(f"{name}/{rid} base_cell={cell} ...", flush=True)
            try:
                rec = _run_one(flat, case, cell)
            except Exception as exc:  # noqa: BLE001 — recorded, not retried (prereg); next run continues
                rec = {"id": rid, "base_cell": cell, "error": f"{type(exc).__name__}: {exc}"[:400]}
                print(f"{name}/{rid} ERR {rec['error']}", flush=True)
            results[name].append(rec)
            if "metrics" in rec:
                print(f"{name}/{rid} OK cfm={rec['cfm_free']}/{rec['cfm_load']} "
                      f"mean_dp0={rec['metrics'].get('mean_dp0_pa')} surf_max={rec['surf_max']}", flush=True)
            (OUT / "summary.json").write_text(json.dumps(_summary(results, stock), indent=1), encoding="utf-8")
    s = _summary(results, stock)
    (OUT / "summary.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
    for name, e in s["designs"].items():
        print(name, e.get("verdict") or {k: v["resolved"] for k, v in e["paired"].items()},
              e.get("same_mesh_stable_rows"), e.get("cross_mesh_agreement"), flush=True)
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    os._exit(rc)
