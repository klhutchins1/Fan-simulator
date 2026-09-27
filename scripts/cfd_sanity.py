"""Print cheap sanity checks for a finished CFD case.

Report only: this is a flag, not a gate. Exit code is always 0.

Usage:
    uv run python scripts/cfd_sanity.py <case_dir>
    uv run python scripts/cfd_sanity.py <case_dir> --json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.sanity import overall, run_sanity  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cheap CFD sanity checks (report-only, never a gate)")
    ap.add_argument("case_dir", help="Finished CFD case directory")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    args = ap.parse_args(argv)

    checks = run_sanity(args.case_dir)
    status = overall(checks)

    if args.json:
        payload = {"overall": status, "checks": [asdict(c) for c in checks]}
        print(json.dumps(payload, indent=2))
        return 0

    name_w = max(len(c.name) for c in checks) if checks else 4
    header = f"{'name':<{name_w}}  {'status':<6}  {'value':>12}  {'limit':<20}  note"
    print(header)
    print("-" * len(header))
    for c in checks:
        value_s = f"{c.value:.4g}" if c.value is not None else "-"
        print(f"{c.name:<{name_w}}  {c.status:<6}  {value_s:>12}  {c.limit:<20}  {c.note}")
    print(f"\noverall: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
