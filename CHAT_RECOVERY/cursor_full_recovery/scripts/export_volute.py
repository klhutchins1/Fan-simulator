"""Export radial impeller + volute casing STLs (geometry scaffold).

Usage:
    uv run python scripts/export_volute.py [--out-dir exports/volute]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.volute.geometry import VoluteParams, export_volute_stls  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Export radial impeller + volute casing STLs (no CFD)")
    ap.add_argument("--out-dir", default="exports/volute",
                    help="directory for impeller.stl and casing.stl")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    imp, cas = export_volute_stls(VoluteParams(), args.out_dir)
    print(f"wrote {imp}")
    print(f"wrote {cas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
