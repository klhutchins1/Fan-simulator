"""Does a quick screening CFD rank designs the way the full Assess does?

Pre-registered criteria: docs/validation/audits/2026-10-07-screen-rank-audit.md (written before
any data). Two candidate quick tiers are judged against the full cockpit Assess:

  Q1  full Assess mesh, free-air only, 300 iters   (scored by replaying the full run's
      free-air history, which objectives.py now keeps; costs nothing extra)
  Q2  coarse mesh (8 mm background, surface level 3), free-air only, 300 iters
      (fansim.optimize.quick_screen; its own run)

Each design runs the full Assess first (cockpit settings, parallel mesh), then Q2, one at a time.
Finished results are skipped, so an interrupted overnight run resumes where it stopped.

    uv run python scripts/screen_rank_audit.py --pilot      # time one Q2 run, print the ETA
    uv run python scripts/screen_rank_audit.py              # run everything not yet done
    uv run python scripts/screen_rank_audit.py --analyze    # verdicts from what is on disk

Judge by the JSON (importing fansim.cfd can crash CPython at teardown on this box).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.metrics import CFM_PER_M3S, TAIL_FRAC  # noqa: E402
from fansim.fan_spec import fan_spec_to_dict, get_fan_spec  # noqa: E402
from fansim.geometry.features import features_from_flat  # noqa: E402
from fansim.isolated_job import run_watched, stall_timeout  # noqa: E402
from fansim.optimize.isolated_eval import evaluate_candidate_isolated  # noqa: E402
from fansim.optimize.objectives import FREE_HISTORY_DIR  # noqa: E402
from fansim.optimize.presets import assess_load  # noqa: E402
from fansim.optimize.quick_screen import QUICK_ITERS  # noqa: E402
from fansim.optimize.search_space import stock_blade_flat  # noqa: E402

OUT = ROOT / "runs" / "screen_rank_audit"
ASSESS_DIR = ROOT / "runs" / "opt_run1" / "cockpit_assess"
SPEC = "a12x25"
PRESET = "case"

# Pre-registered thresholds (see the audit doc; do not change after seeing data).
RHO_FREE_MIN = 0.90
RHO_LOAD_MIN = 0.80
TOP_K, WITHIN = 3, 5
N_MIN = 8


def _stock_variant(**changes) -> dict:
    flat = dict(stock_blade_flat(SPEC))
    for k, v in changes.items():
        flat[k] = v(flat[k]) if callable(v) else v
    return flat


def _saved(trial: int) -> dict:
    return json.loads((ASSESS_DIR / f"design_{trial}" / "design.json").read_text())["params"]


def designs() -> dict[str, dict]:
    """Varied on purpose: blade counts 7-10, bio features, thin walls, high-free/low-load designs."""
    thin = 0.7
    return {
        "stock": _stock_variant(),
        "stock_thin": _stock_variant(thickness_root=lambda t: t * thin,
                                     thickness_mid=lambda t: t * thin,
                                     thickness_tip=lambda t: t * thin),
        "stock_dimples": _stock_variant(dimple_amp=0.2),
        **{f"t{t}": _saved(t) for t in (9000, 9001, 9002, 9003, 9005, 9006, 9008, 9012,
                                        9015, 9016)},
    }


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run_full(name: str, flat: dict, sub: str = "full", **eval_kw) -> dict:
    out = OUT / name / sub / "result.json"
    # Resume: keep finished results (a gate rejection is a result); retry crashes/kills.
    if (done := _read(out)) is not None and not done.get("error"):
        return done
    load_pa, _ = assess_load(PRESET)
    t0 = time.time()
    row: dict = {"design": name}
    try:
        res = evaluate_candidate_isolated(
            flat, features_from_flat(flat), out.parent, spec=get_fan_spec(SPEC), procs=8,
            base_cell=0.006, iters=500, load_pa=load_pa, refine_op=False, material="PETG",
            parallel_mesh=True, **eval_kw)
        row.update(feasible=res.feasible, reason=res.reason, cfm_free=res.cfm_free,
                   cfm_load=res.cfm_load, efficiency=res.efficiency,
                   free_raw_cfm=res.raw.get("free", {}).get("cfm"),
                   load_raw_cfm=res.raw.get("load", {}).get("cfm"),
                   converged=res.raw.get("converged"),
                   vibration_warning=res.raw.get("vibration_warning", ""), **eval_kw)
    except Exception as exc:  # noqa: BLE001 — record, move on to the next design
        row.update(feasible=False, error=f"{type(exc).__name__}: {exc}")
    row["wall_s"] = round(time.time() - t0, 1)
    out.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return row


def run_quick(name: str, flat: dict, sub: str = "quick", load_pa: float | None = None) -> dict:
    wd = OUT / name / sub
    out = wd / "result.json"
    if (done := _read(out)) is not None and done.get("ok"):
        return done  # failed/killed quick runs are retried on resume
    wd.mkdir(parents=True, exist_ok=True)
    job = wd / "_job.json"
    job.write_text(json.dumps({"flat": flat, "workdir": str(wd), "out": str(out),
                               "spec": fan_spec_to_dict(get_fan_spec(SPEC)),
                               "load_pa": load_pa}), encoding="utf-8")
    t0 = time.time()
    try:
        code, _o, err = run_watched([sys.executable, "-m", "fansim.optimize.quick_screen",
                                     str(job)], watch_dir=wd, hard_timeout_s=3 * 3600,
                                    stall_s=stall_timeout(), label=f"quick {name}")
        if code != 0 or not out.exists():
            raise RuntimeError(f"exit {code}: {err.strip()[-300:]}")
    except Exception as exc:  # noqa: BLE001
        row = {"ok": False, "reason": f"{type(exc).__name__}: {exc}",
               "wall_s": round(time.time() - t0, 1)}
        out.write_text(json.dumps(row, indent=2), encoding="utf-8")
        return row
    return _read(out) or {"ok": False, "reason": "unreadable result"}


def q1_from_history(name: str, iters: int = QUICK_ITERS) -> float | None:
    """Free-air CFM a ``iters``-iteration run on the full mesh reports (same tail-mean rule).

    The solve is deterministic, so truncating the 500-iteration history at ``iters`` is the
    same trajectory a shorter run would have produced.
    """
    p = OUT / name / "full" / FREE_HISTORY_DIR / "outletFlow" / "surfaceFieldValue.dat"
    try:
        rows = []
        for line in p.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if parts and not line.startswith("#"):
                rows.append((float(parts[0]), float(parts[-1])))
    except (OSError, ValueError):
        return None
    vals = [v for t, v in rows if t <= iters]
    if len(vals) < 4:
        return None
    tail = vals[max(1, int(len(vals) * (1.0 - TAIL_FRAC))):]
    return sum(tail) / len(tail) * CFM_PER_M3S


def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0
        i = j + 1
    return r


def spearman(a: list[float], b: list[float]) -> float:
    ra, rb = _ranks(a), _ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** 0.5
    vb = sum((y - mb) ** 2 for y in rb) ** 0.5
    return cov / (va * vb) if va and vb else 0.0


def judge(tier: str, quick: dict[str, float], full: dict[str, dict]) -> dict:
    names = [n for n in quick if n in full and full[n].get("feasible")]
    out: dict = {"tier": tier, "n": len(names)}
    if len(names) < N_MIN:
        out["verdict"] = "INCONCLUSIVE"
        out["why"] = f"n={len(names)} < {N_MIN} designs with both results"
        return out
    q = [quick[n] for n in names]
    rho_free = spearman(q, [full[n]["cfm_free"] for n in names])
    rho_load = spearman(q, [full[n]["cfm_load"] for n in names])
    rho_eff = spearman(q, [full[n]["efficiency"] for n in names])
    top_full = sorted(names, key=lambda n: full[n]["cfm_load"], reverse=True)[:TOP_K]
    top_quick = sorted(names, key=lambda n: quick[n], reverse=True)[:WITHIN]
    recall_ok = all(n in top_quick for n in top_full)
    passed = rho_free >= RHO_FREE_MIN and rho_load >= RHO_LOAD_MIN and recall_ok
    out.update(rho_free=round(rho_free, 3), rho_load=round(rho_load, 3),
               rho_eff_report_only=round(rho_eff, 3), top_full_load=top_full,
               top_quick=top_quick, top_recall_ok=recall_ok,
               verdict="PASS" if passed else "FAIL",
               rows={n: {"quick": round(quick[n], 2), "full_free": round(full[n]["cfm_free"], 2),
                         "full_load": round(full[n]["cfm_load"], 2),
                         "full_eff": round(full[n]["efficiency"], 2)} for n in names})
    return out


def analyze() -> dict:
    full = {n: r for n in designs() if (r := _read(OUT / n / "full" / "result.json"))}
    q2 = {}
    q2_meta = {}
    for n in designs():
        r = _read(OUT / n / "quick" / "result.json")
        if r and r.get("ok"):
            q2[n] = float(r["cfm_free_raw"])
            q2_meta[n] = {"cells": r.get("cells"), "wall_s": r.get("wall_s")}
    q1 = {n: v for n in designs() if (v := q1_from_history(n)) is not None}
    report = {
        "Q1_full_mesh_300": judge("Q1", q1, full),
        "Q2_coarse_300": judge("Q2", q2, full),
        "full_wall_s": {n: r.get("wall_s") for n, r in full.items()},
        "q2_cost": q2_meta,
        "full_rejected": {n: r.get("reason") or r.get("error") for n, r in full.items()
                          if not r.get("feasible")},
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pilot", action="store_true", help="time one Q2 run on Stock, print ETA")
    ap.add_argument("--analyze", action="store_true", help="only score what is on disk")
    ap.add_argument("--only", default="", help="comma list of design names")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    todo = designs()
    if args.only:
        todo = {k: v for k, v in todo.items() if k in set(args.only.split(","))}
    if args.analyze:
        print(json.dumps(analyze(), indent=2))
        return 0
    if args.pilot:
        q = run_quick("stock", todo["stock"])
        full_est = 25 * 60  # 2026-10-07 Stock Assess: 21-24 min; padded for larger meshes
        per = (q.get("wall_s") or 0) + full_est
        eta = 1.2 * per * len(designs())
        pilot = {"quick_stock": q, "designs": len(designs()),
                 "eta_h": round(eta / 3600, 1)}
        (OUT / "pilot.json").write_text(json.dumps(pilot, indent=2), encoding="utf-8")
        print(json.dumps(pilot), flush=True)
        return 0
    for name, flat in todo.items():
        f = run_full(name, flat)
        print(json.dumps({"full": f}), flush=True)
        if f.get("feasible"):
            print(json.dumps({"quick": name, **run_quick(name, flat)}), flush=True)
    print(json.dumps(analyze(), indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
