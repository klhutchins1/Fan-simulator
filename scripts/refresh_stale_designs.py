"""Bring Assess designs scored by an old solver up to the current one (CFD_VERSION).

For every ``runs/*/cockpit_assess/design_*/design.json`` whose score is stale:

  1. use a current full-Assess result that already exists (the 2026-10-07 screening audit re-ran
     most of them: ``runs/screen_rank_audit/t<trial>/full``), else
  2. with ``--rerun``, run the full Assess now (cockpit settings, "case" hose, parallel mesh) into
     ``runs/rescore_v5/<run>_t<trial>``, one at a time, resumable;

then rewrite design.json with the new score. The previous score is kept under
``extra.rescored.previous`` and the original file is backed up once as ``design.pre_refresh.json``.
``extra.case_dir`` points the cockpit at the new case (STL + airflow view). A design the current
solver rejects becomes infeasible (hidden from Results) with the reason recorded.

    uv run python scripts/refresh_stale_designs.py            # dry run: what would change
    uv run python scripts/refresh_stale_designs.py --apply    # import existing re-runs only
    uv run python scripts/refresh_stale_designs.py --rerun    # also run missing ones, then apply
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.metrics import CFD_VERSION  # noqa: E402
from fansim.cockpit.data import cfd_is_stale  # noqa: E402
from fansim.cockpit.score_caption import stamp_score_extra  # noqa: E402
from fansim.fan_spec import get_fan_spec  # noqa: E402
from fansim.geometry.features import features_from_flat  # noqa: E402
from fansim.optimize.isolated_eval import evaluate_candidate_isolated  # noqa: E402
from fansim.optimize.objectives import ObjectiveResult  # noqa: E402
from fansim.optimize.presets import assess_load  # noqa: E402

RUNS = ROOT / "runs"
AUDIT = RUNS / "screen_rank_audit"
RESCORE = RUNS / "rescore_v5"
PRESET = "case"
BACKUP = "design.pre_refresh.json"


def stale_designs() -> list[tuple[str, int, Path]]:
    out = []
    for jf in sorted(RUNS.glob("*/cockpit_assess/design_*/design.json")):
        try:
            d = json.loads(jf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("feasible", True) and cfd_is_stale((d.get("extra") or {}).get("cfd_version")):
            out.append((jf.parents[2].name, int(d["trial"]), jf))
    return out


def candidate_cases(run: str, trial: int) -> list[Path]:
    cases = [RESCORE / f"{run}_t{trial}"]
    if run == "opt_run1":
        cases.insert(0, AUDIT / f"t{trial}" / "full")
    return cases


def finished(case: Path) -> ObjectiveResult | None:
    try:
        return ObjectiveResult(**json.loads((case / "_eval_result.json").read_text()))
    except (OSError, ValueError, TypeError):
        return None


def rerun(run: str, trial: int, flat: dict) -> Path:
    case = RESCORE / f"{run}_t{trial}"
    load_pa, _ = assess_load(PRESET)
    t0 = time.time()
    try:
        evaluate_candidate_isolated(
            flat, features_from_flat(flat), case, spec=get_fan_spec("a12x25"), procs=8,
            base_cell=0.006, iters=500, load_pa=load_pa, refine_op=False, material="PETG",
            parallel_mesh=True)
        print(f"  re-ran {run} t{trial} in {(time.time() - t0) / 60:.0f} min", flush=True)
    except Exception as exc:  # noqa: BLE001 — leave it stale, report, move on
        print(f"  re-run FAILED {run} t{trial}: {type(exc).__name__}: {exc}", flush=True)
    return case


def apply(jf: Path, case: Path, res: ObjectiveResult) -> str:
    d = json.loads(jf.read_text(encoding="utf-8"))
    backup = jf.with_name(BACKUP)
    if not backup.exists():
        shutil.copyfile(jf, backup)
    extra = dict(d.get("extra") or {})
    extra["rescored"] = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "case": case.relative_to(RUNS).as_posix(),
        "previous": {"objectives": d.get("objectives"), "cfd_version": extra.get("cfd_version"),
                     "feasible": d.get("feasible", True), "reason": d.get("reason", "")},
    }
    extra["case_dir"] = case.relative_to(RUNS).as_posix()
    extra["cfd_version"] = CFD_VERSION
    extra["cfd_stale"] = False
    if res.feasible:
        load_pa, _ = assess_load(PRESET)
        stamp_score_extra(extra, res.raw, load_pa=load_pa, preset=PRESET, refine_op=False)
        extra["actual_rpm"] = round(res.actual_rpm)
        extra["over_spec"] = list(res.over_spec)
        d["objectives"] = {"cfm_free": res.cfm_free, "cfm_load": res.cfm_load,
                           "efficiency": res.efficiency}
        d["feasible"], d["reason"] = True, res.reason
        verdict = (f"free {res.cfm_free:.1f} load {res.cfm_load:.1f} eff {res.efficiency:.1f}"
                   f" (was free {d_prev(extra, 'cfm_free')} load {d_prev(extra, 'cfm_load')})")
    else:
        d["feasible"], d["reason"] = False, res.reason
        verdict = f"REJECTED by current solver: {res.reason}"
    d["extra"] = extra
    jf.write_text(json.dumps(d, indent=2), encoding="utf-8")
    return verdict


def d_prev(extra: dict, key: str) -> str:
    v = ((extra.get("rescored") or {}).get("previous") or {}).get("objectives", {}).get(key)
    return f"{v:.1f}" if isinstance(v, (int, float)) else "?"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="import existing current results")
    ap.add_argument("--rerun", action="store_true", help="run missing ones first, then apply")
    args = ap.parse_args()
    todo = stale_designs()
    print(f"{len(todo)} stale design(s)", flush=True)
    for run, trial, jf in todo:
        res, case = None, None
        for c in candidate_cases(run, trial):
            if (r := finished(c)) is not None:
                res, case = r, c
                break
        if res is None and args.rerun:
            flat = json.loads(jf.read_text(encoding="utf-8"))["params"]
            case = rerun(run, trial, flat)
            res = finished(case)
        if res is None:
            print(f"{run} t{trial}: no current result yet "
                  f"({'re-run failed' if args.rerun else 'use --rerun'})", flush=True)
            continue
        if not (args.apply or args.rerun):
            print(f"{run} t{trial}: would import {case.relative_to(RUNS)} "
                  f"(feasible={res.feasible})", flush=True)
            continue
        print(f"{run} t{trial}: {apply(jf, case, res)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
