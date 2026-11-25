#!/usr/bin/env python3
"""Print sim→reality calibration factors from validation/measurements/ as JSON.

Thin CLI over ``validation.store.calibration_from_store``.

  uv run python scripts/calibrate_from_store.py
  uv run python scripts/calibrate_from_store.py --store validation/measurements
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from validation.store import STORE_DIR, calibration_from_store  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Aggregate measurement store into sim→reality calibration JSON")
    ap.add_argument("--store", type=Path, default=STORE_DIR,
                    help=f"measurement store dir (default: {STORE_DIR})")
    args = ap.parse_args()

    cal = calibration_from_store(args.store)
    payload = asdict(cal)
    # details can be large; keep a compact summary by default
    print(json.dumps({
        "cfm": payload["cfm"],
        "static_pressure": payload["static_pressure"],
        "noise_dba_offset": payload["noise_dba_offset"],
        "n_points": payload["n_points"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    code = main()
    if sys.platform == "win32":
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    raise SystemExit(code)
