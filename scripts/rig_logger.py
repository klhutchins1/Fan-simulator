#!/usr/bin/env python3
"""Append low-cost P–Q rig readings to a CSV matching validation.ingest schema.

Hardware (plenum, plates, SDP810, tach, MCU) is user-owned; this script is the software
logger that lands rows for ``validation.ingest.load_measurements``.

Examples:
  # Interactive / piped key=value lines
  echo "rpm=2000,dp=12.3,cfm=45,noise=38,restriction=plate3" | \\
    uv run python scripts/rig_logger.py --out runs/rig.csv --source sdp810

  # Serial (optional; needs pyserial). Falls back to stdin if --serial omitted.
  uv run python scripts/rig_logger.py --out runs/rig.csv --source sdp810 --serial COM3
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from validation.ingest import CSV_COLUMNS  # noqa: E402

# Short aliases accepted on stdin / serial lines → CSV column names.
_ALIASES = {
    "rpm": "rpm",
    "cfm": "cfm",
    "static": "static_pressure_pa",
    "static_pressure_pa": "static_pressure_pa",
    "static_pa": "static_pressure_pa",
    "noise": "noise_dba",
    "noise_dba": "noise_dba",
    "dba": "noise_dba",
    "source": "source",
    "notes": "notes",
    "restriction": "restriction_id",
    "restriction_id": "restriction_id",
    "dp": "dp_pa",
    "dp_pa": "dp_pa",
    "tach": "tach_rpm",
    "tach_rpm": "tach_rpm",
    "ambient": "ambient_c",
    "ambient_c": "ambient_c",
    "humidity": "humidity_pct",
    "humidity_pct": "humidity_pct",
}

def parse_line(line: str, *, default_source: str = "") -> dict[str, str] | None:
    """Parse ``rpm=2000,dp=12.3,cfm=45`` (or space-separated) into CSV field strings.

    Returns None for blank / comment lines. Raises ValueError if rpm is missing.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # Allow "rpm=2000 dp=12.3" as well as comma-separated
    parts = [p.strip() for p in line.replace(";", ",").split(",") if p.strip()]
    if len(parts) == 1 and " " in parts[0] and "=" in parts[0]:
        parts = [p.strip() for p in parts[0].split() if p.strip()]

    fields: dict[str, str] = {c: "" for c in CSV_COLUMNS}
    if default_source:
        fields["source"] = default_source

    for part in parts:
        if "=" not in part:
            raise ValueError(f"expected key=value token, got {part!r}")
        key, _, raw = part.partition("=")
        key = key.strip().lower()
        raw = raw.strip()
        col = _ALIASES.get(key)
        if col is None:
            raise ValueError(f"unknown field {key!r} (known: {', '.join(sorted(set(_ALIASES)))})")
        fields[col] = raw

    if not fields["rpm"]:
        raise ValueError("rpm is required")
    return fields


def append_row(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(CSV_COLUMNS), extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerow({c: row.get(c, "") for c in CSV_COLUMNS})


def _iter_stdin():
    for line in sys.stdin:
        yield line


def _iter_serial(port: str, baud: int):
    try:
        import serial  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SystemExit(
            "pyserial is not installed; omit --serial and use stdin, "
            "or: uv pip install pyserial"
        ) from exc
    with serial.Serial(port, baudrate=baud, timeout=1) as ser:
        print(f"Listening on {port} @ {baud}; Ctrl+C to stop.", file=sys.stderr)
        while True:
            raw = ser.readline()
            if not raw:
                continue
            yield raw.decode("utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Log P–Q rig readings to a CSV for validation.ingest.load_measurements")
    ap.add_argument("--out", type=Path, required=True, help="CSV path to append")
    ap.add_argument("--source", default="", help="default instrument / rig id")
    ap.add_argument("--serial", default=None, help="COM port (needs pyserial); else stdin")
    ap.add_argument("--baud", type=int, default=115200, help="serial baud (default 115200)")
    ap.add_argument("--once", action="store_true",
                    help="process one line then exit (useful for tests / one-shot pipes)")
    args = ap.parse_args()

    stream = _iter_serial(args.serial, args.baud) if args.serial else _iter_stdin()
    n = 0
    try:
        for line in stream:
            try:
                row = parse_line(line, default_source=args.source)
            except ValueError as exc:
                print(f"skip: {exc}", file=sys.stderr)
                continue
            if row is None:
                continue
            if args.source and not row["source"]:
                row["source"] = args.source
            append_row(args.out, row)
            n += 1
            print(f"wrote {n}: rpm={row['rpm']} dp_pa={row['dp_pa'] or '-'} "
                  f"cfm={row['cfm'] or '-'} restriction={row['restriction_id'] or '-'}",
                  file=sys.stderr)
            if args.once:
                break
    except KeyboardInterrupt:
        print(f"\nstopped after {n} row(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    code = main()
    if sys.platform == "win32":
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    raise SystemExit(code)
