"""Freeze a prop CFD result.json into validation/reference/drone_radial/cfd/."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.propeller.cfd_fixture import (  # noqa: E402
    build_prop_cfd_fixture,
    force_z_tail_drift_pct,
    prop_cfd_smoke_gate,
    write_prop_cfd_fixture,
)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Freeze prop CFD smoke fixture JSON")
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--stl", required=True)
    ap.add_argument(
        "--spin", type=int, default=None,
        help="stamped MRF spin (default: taken from --result's own \"spin\" field, which is "
             "what the run actually solved with; pass this only to override that)",
    )
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--iters", type=int, default=400)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--case-dir", type=Path, default=None)
    ap.add_argument("--allow-no-case", action="store_true")
    ap.add_argument("--require-gate", action="store_true")
    ap.add_argument(
        "--drift-tol",
        type=float,
        default=25.0,
        help="force-tail drift %% gate when --require-gate (default 25 smoke)",
    )
    ap.add_argument(
        "--tail-frac",
        type=float,
        default=0.25,
        help="fraction of force.dat for drift (default 0.25; refine late-window 0.10)",
    )
    ap.add_argument("--date", default=None)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    spin = int(result["spin"]) if args.spin is None else int(args.spin)
    case_dir = args.case_dir
    if case_dir is None:
        parent = Path(args.result).resolve().parent
        if (parent / "postProcessing").is_dir():
            case_dir = parent
    drift = None
    if case_dir is not None:
        drift = force_z_tail_drift_pct(case_dir, tail_frac=float(args.tail_frac))
    elif not args.allow_no_case:
        print(
            "ERROR: no case-dir / postProcessing; pass --case-dir or --allow-no-case",
            file=sys.stderr,
        )
        return 2
    if args.require_gate:
        ok, reasons = prop_cfd_smoke_gate(
            result,
            case_dir=case_dir,
            drift_tol_pct=float(args.drift_tol),
            tail_frac=float(args.tail_frac),
        )
        if not ok:
            print("GATE FAIL:\n" + "\n".join(reasons), file=sys.stderr)
            return 2
    fixture = build_prop_cfd_fixture(
        result=result,
        fixture_id=args.id,
        stl=args.stl,
        spin=spin,
        mesh={
            "base_cell_m": args.base_cell,
            "iters": args.iters,
            "procs": args.procs,
        },
        force_tail_drift_pct=drift,
        date=args.date,
    )
    path = write_prop_cfd_fixture(fixture, args.out)
    print(json.dumps({"wrote": str(path), "id": fixture["id"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
