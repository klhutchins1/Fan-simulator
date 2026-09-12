# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Reclaim disk by pruning finished OpenFOAM case internals (mesh + processor copies + logs).

Safe: the results (study.db / result.json / catalog) and the STLs are KEPT; only regenerable case
internals are removed, and cases can be re-meshed + re-run any time. DRY-RUN by default — nothing is
deleted unless you pass --apply.

    uv run python scripts/prune_runs.py                 # show what could be reclaimed (no deletion)
    uv run python scripts/prune_runs.py --run opt_v2    # just one run
    uv run python scripts/prune_runs.py --apply         # actually delete (after reviewing the dry-run)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.maintenance import human, prune, scan_all  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="prune regenerable OpenFOAM case internals")
    ap.add_argument("--run", default=None, help="only this run (default: all runs)")
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--apply", action="store_true", help="actually delete (default is a dry run)")
    args = ap.parse_args()

    runs = scan_all(args.runs_dir, only=args.run)
    if not runs:
        print("No solved cases found to prune.")
        return 0

    total_bytes, total_cases = 0, 0
    print(f"{'run':22s} {'cases':>6s} {'reclaimable':>12s}")
    print("-" * 44)
    for r in sorted(runs, key=lambda x: -x["bytes"]):
        print(f"{r['run']:22s} {r['cases']:>6d} {human(r['bytes']):>12s}")
        total_bytes += r["bytes"]
        total_cases += r["cases"]
    print("-" * 44)
    print(f"{'TOTAL':22s} {total_cases:>6d} {human(total_bytes):>12s}")

    all_targets = [t for r in runs for t in r["targets"]]
    if not args.apply:
        print(f"\nDRY RUN — nothing deleted. Re-run with --apply to free {human(total_bytes)} "
              f"across {total_cases} cases.\n(Kept: STLs, result.json, study.db, catalog, case dicts. "
              "Cases can be re-meshed + re-run any time.)")
        return 0

    freed = prune(all_targets, apply=True)
    print(f"\n✓ Pruned {total_cases} cases — freed {human(freed)}. Results + STLs preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
