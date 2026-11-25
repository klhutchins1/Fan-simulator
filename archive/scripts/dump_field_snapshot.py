"""CLI: ingest OpenFOAM case fields into runs/field_snapshots/<label>/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.surrogate.fields import ingest_case_fields, list_snapshots  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Dump OF fields for future FNO")
    ap.add_argument("--case", type=Path, required=True, help="OpenFOAM case directory")
    ap.add_argument("--out", type=Path, default=Path("runs/field_snapshots"))
    ap.add_argument("--label", default=None)
    ap.add_argument("--list", action="store_true", help="list snapshots under --out")
    args = ap.parse_args()

    if args.list:
        print(json.dumps(list_snapshots(args.out), indent=2))
        return 0

    label = args.label or args.case.name
    dest = args.out / label
    man = ingest_case_fields(args.case, dest, label=label)
    print(json.dumps(man, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
