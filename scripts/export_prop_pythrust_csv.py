"""Export BEMT CT/CP tables as a PyThrust catalog entry (JSON + CSV).

Usage:
    uv run python scripts/export_prop_pythrust_csv.py --spec cine_3inch
    uv run python scripts/export_prop_pythrust_csv.py --spec cine_3inch --rpm 3000,7000 --j 0,0.2,0.4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.prop_spec import get_prop_spec  # noqa: E402
from fansim.propeller.geometry import prop_blade_params  # noqa: E402
from fansim.propeller.polar import parse_float_list  # noqa: E402
from fansim.propeller.pythrust_export import (  # noqa: E402
    export_bemt_pythrust_catalog,
    prop_id_for_export,
)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Export BEMT polar as PyThrust JSON+CSV")
    ap.add_argument("--spec", required=True, help="PropSpec key (e.g. cine_3inch)")
    ap.add_argument("--out", type=Path, default=Path("exports/pythrust"))
    ap.add_argument("--prop-id", default=None, help="override catalog id")
    ap.add_argument("--rpm", default=None, help="comma RPM list")
    ap.add_argument("--j", default=None, help="comma advance-ratio list")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    spec = get_prop_spec(args.spec)
    prop_id = args.prop_id or prop_id_for_export(args.spec)
    rpm_list = None if args.rpm is None else parse_float_list(args.rpm)
    j_list = None if args.j is None else parse_float_list(args.j)
    out = export_bemt_pythrust_catalog(
        prop_blade_params(spec),
        prop_id=prop_id,
        diameter_in=spec.diameter_in,
        pitch_in=spec.pitch_in,
        blade_count=spec.n_blades,
        out_dir=args.out,
        rpm_list=rpm_list,
        j_list=j_list,
        geometry_match="design_blade",
        model=spec.name,
    )
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
