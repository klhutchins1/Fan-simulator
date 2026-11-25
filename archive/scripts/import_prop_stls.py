"""Prepare external drone / radial-impeller STLs for prop open-air CFD.

Usage:
    uv run python scripts/import_prop_stls.py \\
        --src path/to/downloaded_stls \\
        --dst validation/reference/drone_radial
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.propeller.stl_import import DEFAULT_IMPORT_DIR, import_prop_stl_dir  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Import + prepare prop/impeller STLs for CFD")
    ap.add_argument("--src", type=Path, required=True, help="directory of raw millimeter STLs")
    ap.add_argument("--dst", type=Path, default=DEFAULT_IMPORT_DIR)
    args = ap.parse_args()

    if not args.src.is_dir():
        print(f"ERROR: --src is not a directory: {args.src}", file=sys.stderr)
        return 2

    rows = import_prop_stl_dir(args.src, args.dst)
    print(json.dumps({"dst": str(args.dst), "n": len(rows), "items": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
