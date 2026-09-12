"""Export one mixed-flow impeller STL for the A12x25 envelope.

Usage:
    uv run python scripts/export_mixed_flow.py [--out exports/mixed_flow.stl]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.centrifugal.geometry import MixedFlowParams, export_mixed_flow_stl  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Export a mixed-flow impeller STL (A12x25 cup + 110 mm frame)")
    ap.add_argument("--out", default="exports/mixed_flow.stl",
                    help="destination STL path")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    path = export_mixed_flow_stl(MixedFlowParams(), args.out)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
