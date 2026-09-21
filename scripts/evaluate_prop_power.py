"""CLI for prop hover power budget, catalog operating point, and propulsion quorum.

Usage:
    uv run python scripts/evaluate_prop_power.py --mode hover-budget --auw-n 19.6 --tip-radius-m 0.0635
    uv run --extra propulsion python scripts/evaluate_prop_power.py --mode catalog --dia-in 5 --pitch-in 4.5
    uv run --extra propulsion python scripts/evaluate_prop_power.py --mode quorum
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.propeller.power import (  # noqa: E402
    PropulsionExtraMissing,
    hover_power_budget,
    run_propulsion_quorum,
    solve_catalog_operating_point,
)


def build_parser() -> argparse.ArgumentParser:
    """CLI flags for prop power evaluate (tests parse this; main() runs it)."""
    ap = argparse.ArgumentParser(description="Prop hover power / catalog matching / quorum")
    ap.add_argument("--mode", choices=("hover-budget", "catalog", "quorum"), required=True)
    # hover-budget
    ap.add_argument("--auw-n", type=float, default=None)
    ap.add_argument("--n-rotors", type=int, default=4)
    ap.add_argument("--tip-radius-m", type=float, default=None)
    ap.add_argument("--fm", type=float, default=0.70)
    ap.add_argument("--eta-elec", type=float, default=0.70)
    ap.add_argument("--battery-wh", type=float, default=None)
    # catalog
    ap.add_argument("--prop-id", default=None)
    ap.add_argument("--dia-in", type=float, default=None)
    ap.add_argument("--pitch-in", type=float, default=None)
    ap.add_argument("--kv", type=float, default=1900.0)
    ap.add_argument("--ri", type=float, default=0.05)
    ap.add_argument("--i0", type=float, default=1.0)
    ap.add_argument("--imax", type=float, default=40.0)
    ap.add_argument("--vbat", type=float, default=22.2)
    ap.add_argument("--throttle", type=float, default=0.7)
    ap.add_argument("--rsys", type=float, default=0.02)
    return ap


def main() -> int:
    args = build_parser().parse_args()

    try:
        if args.mode == "hover-budget":
            if args.auw_n is None or args.tip_radius_m is None:
                print("ERROR: hover-budget requires --auw-n and --tip-radius-m", file=sys.stderr)
                return 1
            out = hover_power_budget(
                all_up_weight_n=float(args.auw_n),
                n_rotors=int(args.n_rotors),
                tip_radius_m=float(args.tip_radius_m),
                figure_of_merit=float(args.fm),
                eta_elec=float(args.eta_elec),
                battery_wh=args.battery_wh,
            )
        elif args.mode == "catalog":
            if not args.prop_id and (args.dia_in is None or args.pitch_in is None):
                print("ERROR: catalog requires --prop-id or --dia-in and --pitch-in", file=sys.stderr)
                return 1
            motor = {
                "kv_rpm_per_v": float(args.kv),
                "resistance_ohm": float(args.ri),
                "no_load_current_a": float(args.i0),
                "current_max_a": float(args.imax),
            }
            out = solve_catalog_operating_point(
                motor=motor,
                battery_voltage_v=float(args.vbat),
                prop_id=args.prop_id,
                diameter_in=args.dia_in,
                pitch_in=args.pitch_in,
                throttle=float(args.throttle),
                system_resistance_ohm=float(args.rsys),
            )
        else:
            out = run_propulsion_quorum()
    except PropulsionExtraMissing as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
