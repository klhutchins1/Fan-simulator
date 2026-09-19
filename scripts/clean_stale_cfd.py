"""Audit (and optionally mark) catalog results scored by an outdated CFD solver.

Every scored trial is now stamped with ``cfd_version`` (fansim.cfd.metrics.CFD_VERSION). Trials
without the current version predate the 2026-09-18 tail-mean-metrics + adaptive-blade-mesh fixes,
so their stored CFM / efficiency are systematically wrong (free-air under-read) and must not be
trusted. The cockpit already flags these as ``cfd_stale`` on load; this script gives an explicit
audit across run directories and can persist a ``cfd_stale`` marker.

Usage:
    uv run python scripts/clean_stale_cfd.py                 # audit every runs/*/study.db
    uv run python scripts/clean_stale_cfd.py --run runs/opt_run1
    uv run python scripts/clean_stale_cfd.py --mark          # persist cfd_stale=True on stale trials

Read-only by default; ``--mark`` only ADDS a user_attr (never deletes a trial or a design).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.metrics import CFD_VERSION  # noqa: E402
from fansim.cockpit.data import cfd_is_stale  # noqa: E402


def _audit_study(db_dir: Path, mark: bool) -> dict:
    import optuna

    storage = f"sqlite:///{(db_dir / 'study.db').as_posix()}"
    try:
        names = optuna.get_all_study_names(storage=storage)
    except Exception as exc:  # noqa: BLE001
        return {"dir": str(db_dir), "error": f"{type(exc).__name__}: {exc}"}
    total = feasible = stale = stale_feasible = marked = 0
    free_stale: list[float] = []
    for name in names:
        study = optuna.load_study(study_name=name, storage=storage)
        for t in study.trials:
            if t.state != optuna.trial.TrialState.COMPLETE:
                continue
            total += 1
            feas = bool(t.user_attrs.get("feasible", False))
            feasible += int(feas)
            if cfd_is_stale(t.user_attrs.get("cfd_version")):
                stale += 1
                stale_feasible += int(feas)
                if feas and t.values:
                    free_stale.append(float(t.values[0]))
                if mark and not t.user_attrs.get("cfd_stale"):
                    try:
                        study._storage.set_trial_user_attr(t._trial_id, "cfd_stale", True)
                        marked += 1
                    except Exception:  # noqa: BLE001 - best-effort; audit still valid
                        pass
    out = {
        "dir": str(db_dir), "studies": names, "trials": total, "feasible": feasible,
        "stale": stale, "stale_feasible": stale_feasible,
    }
    if free_stale:
        out["stale_free_cfm_range"] = [round(min(free_stale), 1), round(max(free_stale), 1)]
    if mark:
        out["marked"] = marked
    return out


def _audit_assess(assess_dir: Path) -> dict:
    """Assessed-design JSONs (cockpit_assess) — report only; the cockpit re-derives staleness."""
    n = stale = 0
    for jf in assess_dir.glob("design_*/design.json"):
        try:
            extra = json.loads(jf.read_text()).get("extra", {})
        except Exception:  # noqa: BLE001
            continue
        n += 1
        stale += int(cfd_is_stale(extra.get("cfd_version")))
    return {"dir": str(assess_dir), "assessed": n, "stale": stale}


def main() -> int:
    ap = argparse.ArgumentParser(description="audit/mark stale (outdated-CFD) catalog results")
    ap.add_argument("--run", default=None, help="a single run dir (default: scan runs/*)")
    ap.add_argument("--mark", action="store_true", help="persist cfd_stale=True on stale trials")
    args = ap.parse_args()

    if args.run:
        dbdirs = [Path(args.run)]
    else:
        dbdirs = sorted(p.parent for p in ROOT.glob("runs/*/study.db"))
    print(f"current CFD_VERSION = {CFD_VERSION}\n")
    grand_stale = 0
    for d in dbdirs:
        rep = _audit_study(d, args.mark)
        grand_stale += int(rep.get("stale", 0))
        print(json.dumps(rep))
        assess = d / "cockpit_assess"
        if assess.is_dir():
            print(json.dumps(_audit_assess(assess)))
    print(f"\nTOTAL stale trials: {grand_stale}"
          + ("  (marked cfd_stale=True)" if args.mark else "  (run --mark to persist a flag)"))
    print("Note: the cockpit already treats unstamped/old-version scores as stale on load.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
