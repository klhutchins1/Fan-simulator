"""Check or rewrite the physics snapshot (RV-1).

    python scripts/physics_snapshot.py                         # compare; exit 1 on any moved number
    python scripts/physics_snapshot.py --write --reason docs/validation/audits/<file>.md

Rules: docs/validation/audits/2026-11-24-physics-snapshot-prereg.md. Write only with an audit file that
explains why the numbers moved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.validation import physics_snapshot as ps


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--reason", help="audit file explaining the change (required with --write)")
    args = ap.parse_args(argv)
    if args.write:
        if not args.reason:
            ap.error("--write needs --reason docs/validation/audits/<file>.md")
        data = ps.write(args.reason)
        print(f"wrote {ps.SNAPSHOT_PATH.relative_to(ps.ROOT)}: {len(data['cases'])} cases, reason {args.reason}")
        return 0
    diffs = ps.compare(ps.load(), ps.compute())
    for d in diffs:
        print(d)
    print(f"{len(diffs)} difference(s)" if diffs else "physics snapshot: no change")
    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())
