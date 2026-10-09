"""Screen r3 under CFD: Q3 quick screen on the QA bot's 30 axial-BEM picks, full Assess on the top 4.

Pre-registered: docs/validation/audits/2026-10-09-screen-r3-cfd.md (questions A, B, C). Resumable:
finished runs are skipped. Report: runs/screen_rank_audit/screen_r3.json.

    uv run python scripts/screen_r3_cfd.py              # Q3 on all 30, full Assess on the Q3 top 4
    uv run python scripts/screen_r3_cfd.py --analyze    # verdicts from what is on disk
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import refresh_stale_designs as rsd  # noqa: E402
import screen_rank_audit as sra  # noqa: E402

LOAD_PA = 8.0
FULL_TOP = 4
TOP5 = {9601, 9602, 9603, 9604, 9605}
REPORT = sra.OUT / "screen_r3.json"
SOURCES = [ROOT / "runs" / d / "cockpit_assess" for d in ("bem_screen_r3_top5", "bem_screen_r3_reserve")]


def designs() -> dict[int, tuple[Path, dict]]:
    out = {}
    for src in SOURCES:
        for jf in sorted(src.glob("design_*/design.json")):
            d = json.loads(jf.read_text(encoding="utf-8"))
            out[int(d["trial"])] = (jf, d)
    return out


def q3(trial: int) -> dict | None:
    r = sra._read(sra.OUT / f"r3_{trial}" / "quick_load" / "result.json")
    return r if r and r.get("ok") else None


def run(ds: dict) -> None:
    for trial, (_jf, d) in ds.items():
        r = sra.run_quick(f"r3_{trial}", d["params"], sub="quick_load", load_pa=LOAD_PA)
        print(json.dumps({"Q3": trial, **{k: r.get(k) for k in ("ok", "cfm_free_raw", "cfm_load_raw",
                                                                 "wall_s")}}), flush=True)
    ranked = sorted((t for t in ds if q3(t)), key=lambda t: q3(t)["cfm_load_raw"], reverse=True)
    for trial in ranked[:FULL_TOP]:
        jf, d = ds[trial]
        name = f"r3_{trial}"
        r = sra.run_full(name, d["params"])
        res = rsd.finished(sra.OUT / name / "full")
        if res is not None and not (d.get("extra") or {}).get("rescored"):
            r["applied"] = rsd.apply(jf, sra.OUT / name / "full", res)
        print(json.dumps({"full": trial, **{k: r.get(k) for k in ("feasible", "cfm_free", "cfm_load",
                                                                   "efficiency", "wall_s")}}), flush=True)


def analyze(ds: dict) -> dict:
    stock_q3 = sra._read(sra.OUT / "stock" / "quick_load" / "result.json")
    stock_load = float(stock_q3["cfm_load_raw"])
    rows = {}
    for trial, (_jf, d) in ds.items():
        q = q3(trial)
        ex = d.get("extra") or {}
        score = ((ex.get("rescored") or {}).get("previous") or {}).get("bem_score_vs_stock") \
            or ex.get("bem_score_vs_stock")
        full = sra._read(sra.OUT / f"r3_{trial}" / "full" / "result.json")
        rows[trial] = {"axial_score": score, "q3_free": q and round(q["cfm_free_raw"], 2),
                       "q3_load": q and round(q["cfm_load_raw"], 2),
                       "full": full and {k: full.get(k) for k in ("feasible", "cfm_free", "cfm_load",
                                                                    "efficiency", "reason")}}
    have = [t for t in rows if rows[t]["q3_load"] is not None and rows[t]["axial_score"] is not None]
    beat = [t for t in TOP5 if rows.get(t, {}).get("q3_load") is not None
            and rows[t]["q3_load"] > stock_load]
    n_top5 = sum(1 for t in TOP5 if rows.get(t, {}).get("q3_load") is not None)
    a = ("SUPPORTED" if len(beat) >= 4 else "REFUTED" if len(beat) <= 1 else "MIXED") \
        if n_top5 == 5 else f"INCOMPLETE ({n_top5}/5 run)"
    rho = sra.spearman([rows[t]["axial_score"] for t in have], [rows[t]["q3_load"] for t in have]) \
        if len(have) >= 3 else None
    b = (None if rho is None else "USABLE" if rho >= 0.5 else "NOT USABLE" if rho < 0.3
         else "INCONCLUSIVE")
    report = {"stock_q3_load": round(stock_load, 2),
              "A_top5_beat_stock_q3": {"beat": sorted(beat), "n": len(beat), "verdict": a},
              "B_rank": {"n": len(have), "rho": rho and round(rho, 3), "verdict": b},
              "rows": rows}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args()
    ds = designs()
    if not args.analyze:
        run(ds)
    print(json.dumps(analyze(ds), indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
