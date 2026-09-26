"""Smoke / CLI for prop compressible open-air CFD evaluate.

Default spec is fpv_5inch (5-inch FPV freestyle). RPM defaults to 0.7 × rpm_max
(~70% throttle — tip Mach > 0.3, compressible regime).

Usage:
    uv run python scripts/evaluate_prop_cfd.py [--out runs/prop_cfd_smoke] [--dry-run]
    uv run python scripts/evaluate_prop_cfd.py --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cfd.runner import image_available  # noqa: E402
from fansim.prop_spec import get_prop_spec  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """CLI flags for prop CFD evaluate (tests parse this; main() runs it)."""
    ap = argparse.ArgumentParser(description="Prop compressible open-air CFD evaluate (stage 1)")
    ap.add_argument("--out", type=Path, default=Path("runs/prop_cfd_smoke"))
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--iters", type=int, default=400)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument(
        "--bemt-floor",
        type=float,
        default=0.0,
        help="skip CFD if BEMT thrust_g < this floor (default 0 = off; ignored with --stl)",
    )
    ap.add_argument("--spec", default="fpv_5inch", help="prop spec key (default fpv_5inch)")
    ap.add_argument("--rpm", type=float, default=None, help="RPM (default 0.7 * rpm_max)")
    ap.add_argument(
        "--stl",
        type=Path,
        default=None,
        help="external millimeter STL (centered/normal-fixed unless --no-prepare-stl)",
    )
    ap.add_argument(
        "--no-prepare-stl",
        action="store_true",
        help="use --stl as-is (must already be Z-up, XY-centered, positive volume)",
    )
    ap.add_argument(
        "--spin",
        type=int,
        default=None,
        choices=(-1, 1),
        help="MRF rotation sign about +z (default: -1; ignored when --direction=auto, which "
             "derives it from the mesh-only geometry proof)",
    )
    ap.add_argument(
        "--direction",
        default="auto",
        choices=("auto", "manual"),
        help="'auto' (default) derives orientation/spin from the mesh-only geometry proof; "
             "'manual' keeps --spin/orientation as given (use for parts the proof calls "
             "INCONCLUSIVE)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="write compressible prop case only (no Docker solve)",
    )
    return ap


def _resolve_spin(args) -> int | None:
    """Return the user's explicit --spin, or None to let direction="auto" derive it.

    Must NOT default to -1 here: evaluate_prop_cfd() raises if an explicit (non-None) spin is
    passed together with direction="auto", since auto mode derives spin from geometry. Only
    direction="manual" falls back to -1 when spin is None (inside evaluate_prop_cfd itself).
    """
    return None if args.spin is None else int(args.spin)


def main() -> int:
    args = build_parser().parse_args()

    spec = get_prop_spec(args.spec)
    rpm = float(0.7 * spec.rpm_max if args.rpm is None else args.rpm)
    spin = _resolve_spin(args)
    args.out.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        from fansim.cfd.openfoam_case import MeshResolution
        from fansim.cfd.orientation import orient_impeller_for_cfd
        from fansim.geometry import watertight_report
        from fansim.propeller.cfd import build_prop_case, prop_open_air
        from fansim.propeller.direction import prop_direction
        from fansim.propeller.geometry import build_prop
        from fansim.propeller.stl_import import measure_prop_stl, prepare_prop_stl

        if args.direction not in ("auto", "manual"):
            print(f"ERROR: direction must be 'auto' or 'manual', got {args.direction!r}",
                  file=sys.stderr)
            return 2
        if args.direction == "auto" and spin is not None:
            print(
                "ERROR: spin is derived from geometry in auto mode; pass --direction manual "
                "to set --spin yourself",
                file=sys.stderr,
            )
            return 2

        stl = args.out / "prop.stl"
        if args.stl is not None:
            src = Path(args.stl)
            if not src.is_file():
                print(f"ERROR: --stl not found: {src}", file=sys.stderr)
                return 2
            if args.no_prepare_stl:
                import shutil

                shutil.copy2(src, stl)
            else:
                prepare_prop_stl(src, stl)
            metrics = measure_prop_stl(stl)
            tip_radius_m = metrics.tip_radius_m
            import math

            tip_mach = (math.pi * 2.0 * tip_radius_m * rpm / 60.0) / 343.0
        else:
            build_prop(spec, stl)
            tip_radius_m = float(spec.diameter_mm) / 2000.0
            tip_mach = float(spec.tip_mach(rpm))
            metrics = None

        # Apply the same mesh-only direction proof (and CFD-copy orientation) as a real run, so
        # --dry-run builds exactly the case a real solve would.
        orientation_used = None
        if args.direction == "auto":
            d = prop_direction(stl, name_hint=Path(args.stl).name if args.stl is not None else None)
            if d.orientation == "flipped":
                orient_impeller_for_cfd(stl, stl, "flipped")
            spin_used = d.spin
            direction_source = d.source
            orientation_used = d.orientation
        else:
            spin_used = -1 if spin is None else int(spin)
            direction_source = "manual"

        # 180° rotation about X (proper rotation; z-range reverses), so bounds must be
        # re-measured after orientation.
        rep = watertight_report(stl)
        (_, _, z0), (_, _, z1) = rep.bounds_mm
        dom = prop_open_air(tip_radius_m, z0 / 1000.0, z1 / 1000.0, rpm=rpm, spin=spin_used)

        case_dir = args.out / "case"
        build_prop_case(
            case_dir,
            stl,
            dom,
            mesh=MeshResolution(base_cell=args.base_cell),
            n_iters=args.iters,
            n_subdomains=args.procs,
        )

        payload = {
            "dry_run": True,
            "spec": args.spec,
            "rpm": rpm,
            "spin": spin_used,
            "direction_source": direction_source,
            "orientation": orientation_used,
            "tip_mach": tip_mach,
            "tip_radius_mm": tip_radius_m * 1000.0,
            "stl": str(args.stl) if args.stl is not None else None,
            "stl_metrics": None if metrics is None else asdict(metrics),
            "case": str(case_dir),
            "domain_extents": asdict(dom),
            "solver": "rhoSimpleFoam",
            "domain": "open_air",
            "regime": "compressible-MRF",
        }
        (args.out / "dry_run.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(payload, indent=2))
        return 0

    if not image_available():
        # If the BEMT floor would skip, still return 0 and write result.json.
        if args.stl is None and float(args.bemt_floor) > 0.0:
            from fansim.propeller.geometry import prop_blade_params
            from fansim.propeller.optimize import bemt_thrust_g

            bemt_g = float(bemt_thrust_g(prop_blade_params(spec), spec, rpm=rpm))
            if bemt_g < float(args.bemt_floor):
                from fansim.propeller.cfd import evaluate_prop_cfd

                out = evaluate_prop_cfd(
                    spec,
                    args.out,
                    rpm=rpm,
                    iters=args.iters,
                    procs=args.procs,
                    base_cell=args.base_cell,
                    spec_key=args.spec,
                    bemt_floor_g=args.bemt_floor,
                    spin=spin,
                    direction=args.direction,
                )
                (args.out / "result.json").write_text(
                    json.dumps(out, indent=2) + "\n", encoding="utf-8"
                )
                print(json.dumps(out, indent=2))
                return 0

        print("ERROR: OpenFOAM Docker image not available", file=sys.stderr)
        return 2

    from fansim.propeller.cfd import evaluate_prop_cfd

    out = evaluate_prop_cfd(
        spec,
        args.out,
        rpm=rpm,
        iters=args.iters,
        procs=args.procs,
        base_cell=args.base_cell,
        spec_key=args.spec,
        bemt_floor_g=args.bemt_floor,
        spin=spin,
        stl_mm=args.stl,
        prepare_stl=not args.no_prepare_stl,
        direction=args.direction,
    )
    (args.out / "result.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
