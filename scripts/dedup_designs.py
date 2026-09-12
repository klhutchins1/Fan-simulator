# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Thin out near-duplicate designs — safely.

Optimization across many runs piles up designs that sit almost on top of each other in the
airflow/efficiency space. This finds those clusters, keeps the BEST of each (pareto first, then
highest efficiency), and hides the rest from the catalog + cockpit.

SAFE BY DEFAULT: a dry run shows what it would drop and deletes nothing. `--apply` only writes a
REVERSIBLE exclusion list (catalog/removed.json) — the source files stay on disk and `--restore`
brings everything back. Add `--delete-files` to also remove the dropped designs' directories (this is
destructive; after the earlier case-prune those dirs are small, so it's for tidiness, not disk).

    uv run python scripts/dedup_designs.py                 # dry run (shows clusters, deletes nothing)
    uv run python scripts/dedup_designs.py --apply         # hide near-duplicates (reversible)
    uv run python scripts/dedup_designs.py --apply --delete-files   # also delete their dirs
    uv run python scripts/dedup_designs.py --restore       # un-hide everything
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.catalog import build_catalog, load_catalog, load_removed, save_removed  # noqa: E402


def _cluster(designs, cell: float):
    """Group designs by ~cell-CFM buckets in (free, load); return (keepers, dropped)."""
    buckets: dict[tuple, list] = {}
    for e in designs:
        if e.cfm_free is None or e.cfm_load is None:
            continue
        key = (round(e.cfm_free / cell), round(e.cfm_load / cell))
        buckets.setdefault(key, []).append(e)
    keep, drop = [], []
    for group in buckets.values():
        group.sort(key=lambda e: (e.is_pareto, e.efficiency or 0, e.has_measurement), reverse=True)
        keep.append(group[0])
        drop.extend(group[1:])
    return keep, drop


def _dir_for(e) -> Path | None:
    """The design's own directory (already case-pruned = small), if we can locate it."""
    if e.stl_path:
        return Path(e.stl_path).parent
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="hide/remove near-duplicate designs")
    ap.add_argument("--cell", type=float, default=2.5, help="CFM bucket size (bigger = more aggressive)")
    ap.add_argument("--apply", action="store_true", help="hide the duplicates (reversible)")
    ap.add_argument("--delete-files", action="store_true", help="also delete their dirs (destructive)")
    ap.add_argument("--restore", action="store_true", help="un-hide everything and rebuild")
    args = ap.parse_args()

    if args.restore:
        save_removed([])
        build_catalog()
        print("Restored — all designs un-hidden. Catalog rebuilt.")
        return 0

    designs = load_catalog()
    if not designs:
        print("Empty catalog — run `catalog build` first.")
        return 1
    keep, drop = _cluster(designs, args.cell)
    if not drop:
        print(f"No near-duplicates at cell={args.cell} CFM. {len(keep)} designs, all distinct.")
        return 0

    print(f"{len(designs)} designs → keep {len(keep)}, hide {len(drop)} near-duplicates "
          f"(cell {args.cell} CFM):\n")
    for e in sorted(drop, key=lambda x: -(x.cfm_free or 0)):
        print(f"   drop {e.design_id:22s} {e.cfm_free:.0f}/{e.cfm_load:.0f} CFM  eff {e.efficiency or 0:.0f}%"
              + (" ★" if e.is_pareto else "") + ("  ✓meas" if e.has_measurement else ""))

    if not args.apply:
        print(f"\nDRY RUN — nothing changed. `--apply` hides these {len(drop)} (reversible via --restore); "
              "add --delete-files to also remove their dirs.")
        return 0

    removed = load_removed() | {e.design_id for e in drop}
    save_removed(removed)
    freed = 0
    if args.delete_files:
        for e in drop:
            d = _dir_for(e)
            if d and d.exists() and "runs" in d.parts:
                try:
                    freed += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                    shutil.rmtree(d, ignore_errors=True)
                except OSError:
                    pass
    build_catalog()
    msg = f"✓ Hid {len(drop)} near-duplicates (now {len(keep)} in the catalog). Reversible with --restore."
    if args.delete_files:
        msg += f"  Deleted their dirs (~{freed/1024/1024:.0f} MB)."
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
