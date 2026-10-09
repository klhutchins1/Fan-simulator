"""Export one counter-rotating stacked-rotor STL (geometry scaffold).

Usage:
    uv run python scripts/export_cror.py [--out exports/cror.stl]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cror.geometry import CrorParams, export_cror_stl  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Export a counter-rotating (CROR) stacked-rotor STL")
    ap.add_argument("--out", default="exports/cror.stl", help="destination STL path")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    path = export_cror_stl(CrorParams(), args.out)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
