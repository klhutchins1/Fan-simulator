"""Overnight checks 2026-10-08: re-Assess, quick screen with a load point, mesh fairness.

Pre-registered criteria: docs/validation/audits/2026-10-08-overnight-checks.md. Reuses the
screening-audit runner (``scripts/screen_rank_audit.py``): its design set, resumable full Assess
runs and rank statistics. Every step skips work that is already on disk, so an interrupted night
resumes. Judge by ``runs/screen_rank_audit/overnight_20261008.json``.

    uv run python scripts/overnight_checks.py              # A, B, C, then apply A to design.json
    uv run python scripts/overnight_checks.py --analyze    # verdicts from what is on disk
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import screen_rank_audit as sra  # noqa: E402

REPORT = sra.OUT / "overnight_20261008.json"
LOAD_PA = 8.0                                 # "case" hose, same as the full Assess
REASSESS = ["stock", "stock_thin", "t9001", "t9002", "t9003", "t9005"]
THICK = ["t9006", "t9008", "t9015"]
EXCLUDE_FROM_RANKING = {"stock_dimples"}      # had no dimples (2026-10-07 setup error)
TOL_PCT = 3.0


def prepare() -> None:
    """Move aside results that no longer describe the current code (kept for comparison)."""
    old_stock = sra.OUT / "stock"
    keep = sra.OUT / "stock_3station_20261007"
    if old_stock.is_dir() and not keep.exists() and not (old_stock / "full" / ".v7").exists():
        shutil.move(str(old_stock), str(keep))
    for name in REASSESS:
        res = sra.OUT / name / "full" / "result.json"
        r = sra._read(res)
        if r and not r.get("feasible") and "vibration" in str(r.get("reason", "")).lower():
            res.rename(res.with_name("result.vibration_rejected.json"))


def part_a(designs: dict) -> dict:
    out = {}
    for name in REASSESS:
        out[name] = sra.run_full(name, designs[name])
        if name == "stock":
            (sra.OUT / "stock" / "full" / ".v7").write_text("7-station tapered recipe\n")
        print(json.dumps({"A": name, **{k: out[name].get(k) for k in
                          ("feasible", "cfm_free", "cfm_load", "efficiency", "wall_s")}}), flush=True)
    return out


def part_b(designs: dict) -> None:
    for name, flat in designs.items():
        if name in EXCLUDE_FROM_RANKING:
            continue
        full = sra._read(sra.OUT / name / "full" / "result.json")
        if not (full and full.get("feasible")):
            continue
        r = sra.run_quick(name, flat, sub="quick_load", load_pa=LOAD_PA)
        print(json.dumps({"B": name, **{k: r.get(k) for k in
                          ("ok", "cfm_free_raw", "cfm_load_raw", "wall_s")}}), flush=True)


def part_c(designs: dict) -> None:
    for name in THICK:
        r = sra.run_full(name, designs[name], sub="full_floor4", surf_max_floor=4)
        print(json.dumps({"C": name, **{k: r.get(k) for k in
                          ("feasible", "cfm_free", "cfm_load", "wall_s")}}), flush=True)


def apply_reassess() -> list[str]:
    """Write the new scores of the formerly vibration-rejected saved designs into design.json."""
    import refresh_stale_designs as rsd

    notes = []
    for name in REASSESS:
        if not name.startswith("t9"):
            continue
        case = sra.OUT / name / "full"
        res = rsd.finished(case)
        jf = rsd.RUNS / "opt_run1" / "cockpit_assess" / f"design_{name[1:]}" / "design.json"
        if res is None or not jf.exists():
            notes.append(f"{name}: no result yet")
            continue
        notes.append(f"{name}: {rsd.apply(jf, case, res)}")
    return notes


def judge_b(designs: dict) -> dict:
    q_load, q_free, full = {}, {}, {}
    for name in designs:
        if name in EXCLUDE_FROM_RANKING:
            continue
        f = sra._read(sra.OUT / name / "full" / "result.json")
        q = sra._read(sra.OUT / name / "quick_load" / "result.json")
        if f and f.get("feasible") and q and q.get("ok") and q.get("cfm_load_raw") is not None:
            full[name], q_load[name], q_free[name] = f, float(q["cfm_load_raw"]), float(q["cfm_free_raw"])
    names = sorted(full)
    out: dict = {"n": len(names)}
    if len(names) < sra.N_MIN:
        return {**out, "verdict": "INCONCLUSIVE", "why": f"n={len(names)} < {sra.N_MIN}"}
    rho_load = sra.spearman([q_load[n] for n in names], [full[n]["cfm_load"] for n in names])
    rho_free = sra.spearman([q_free[n] for n in names], [full[n]["cfm_free"] for n in names])
    top_full = sorted(names, key=lambda n: full[n]["cfm_load"], reverse=True)[:sra.TOP_K]
    top_q = sorted(names, key=lambda n: q_load[n], reverse=True)[:sra.WITHIN]
    recall = all(n in top_q for n in top_full)
    ok = rho_load >= sra.RHO_LOAD_MIN and rho_free >= sra.RHO_FREE_MIN and recall
    return {**out, "rho_load": round(rho_load, 3), "rho_free": round(rho_free, 3),
            "top_full_load": top_full, "top_q3_load": top_q, "top_recall_ok": recall,
            "verdict": "PASS" if ok else "FAIL",
            "rows": {n: {"q3_free": round(q_free[n], 2), "q3_load": round(q_load[n], 2),
                         "full_free": round(full[n]["cfm_free"], 2),
                         "full_load": round(full[n]["cfm_load"], 2)} for n in names}}


def judge_c() -> dict:
    rows, deltas_ok = {}, True
    for name in THICK:
        a = sra._read(sra.OUT / name / "full" / "result.json")
        b = sra._read(sra.OUT / name / "full_floor4" / "result.json")
        if not (a and b and a.get("feasible") and b.get("feasible")):
            return {"verdict": "INCONCLUSIVE", "why": f"{name}: missing or infeasible result"}
        d_free = 100.0 * (b["cfm_free"] / a["cfm_free"] - 1.0)
        d_load = 100.0 * (b["cfm_load"] / a["cfm_load"] - 1.0)
        deltas_ok &= abs(d_free) <= TOL_PCT and abs(d_load) <= TOL_PCT
        rows[name] = {"l3_free": round(a["cfm_free"], 2), "l4_free": round(b["cfm_free"], 2),
                      "d_free_pct": round(d_free, 2), "l3_load": round(a["cfm_load"], 2),
                      "l4_load": round(b["cfm_load"], 2), "d_load_pct": round(d_load, 2)}
    order_l3 = sorted(THICK, key=lambda n: rows[n]["l3_load"], reverse=True)
    order_l4 = sorted(THICK, key=lambda n: rows[n]["l4_load"], reverse=True)
    ok = deltas_ok and order_l3 == order_l4
    return {"verdict": "PASS" if ok else "FAIL", "deltas_within_3pct": deltas_ok,
            "order_unchanged": order_l3 == order_l4, "rows": rows}


def analyze(designs: dict, apply_notes: list[str] | None = None) -> dict:
    a = {n: sra._read(sra.OUT / n / "full" / "result.json") for n in REASSESS}
    old = sra._read(sra.OUT / "stock_3station_20261007" / "full" / "result.json")
    report = {"A_reassess": a, "A_stock_3station_previous": old,
              "B_quick_with_load": judge_b(designs), "C_mesh_floor": judge_c()}
    if apply_notes is not None:
        report["A_applied"] = apply_notes
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args()
    designs = sra.designs()
    if args.analyze:
        print(json.dumps(analyze(designs), indent=2))
        return 0
    prepare()
    part_a(designs)
    part_b(designs)
    part_c(designs)
    notes = apply_reassess()
    print(json.dumps(analyze(designs, notes), indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
