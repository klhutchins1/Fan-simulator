"""Export a frame-fitted, motor-cup-carved A12x25 Stock impeller for print trials.

Usage:
    uv run python scripts/export_a12x25_print_ready.py
    uv run python scripts/export_a12x25_print_ready.py --out exports/my_print
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cockpit.placement import fit_envelope, measure_flat, nominal_fits_spec  # noqa: E402
from fansim.fan_spec import get_fan_spec  # noqa: E402
from fansim.manufacturability.mount_gauge import (  # noqa: E402
    gauge_print_stl,
    mount_checklist_md,
)
from fansim.manufacturability.print_export import (  # noqa: E402
    balance_summary,
    export_print_ready,
    print_readme,
    recommend_print_settings,
)
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Export print-ready A12x25 Stock with mount gauge")
    ap.add_argument("--fan", default="a12x25", help="FanSpec key (default a12x25)")
    ap.add_argument("--material", default=None, help="override material (default from FanSpec)")
    ap.add_argument("--out", default=None, help="output directory (default exports/…)")
    ap.add_argument("--no-fit", action="store_true",
                    help="skip fit_envelope (export raw Stock tip/hub — may not fit frame)")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    spec = get_fan_spec(args.fan)
    if spec.motor_mount is None:
        print(f"ERROR: fan {args.fan!r} has no MotorMount — cannot export mountable print.")
        return 2

    flat = dict(stock_blade_flat("a12x25" if args.fan == "a12x25" else args.fan))
    changes = []
    if not args.no_fit:
        placed = fit_envelope(flat, spec)
        flat = placed.flat
        changes = [f"{c.field}: {c.before} → {c.after}" for c in placed.changes]

    params = blade_from_flat(flat)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out) if args.out else Path("exports") / f"print_a12x25_stock_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    stl = out_dir / "impeller_print.stl"

    material = args.material or spec.material
    rep = export_print_ready(params, stl, mount=spec.motor_mount)
    bal = balance_summary(params, float(params.rpm or spec.rpm))
    settings = recommend_print_settings(material)
    sheet = print_readme(
        f"{spec.name} Stock (print-ready)",
        params,
        material,
        rep,
        bal,
        settings,
        bore=None,
        objectives=None,
    )
    (out_dir / "print_sheet.md").write_text(sheet, encoding="utf-8")

    gauge = gauge_print_stl(str(stl), spec)
    checklist = mount_checklist_md(gauge, spec, stl_name=stl.name)
    (out_dir / "mount_checklist.md").write_text(checklist, encoding="utf-8")

    measured = measure_flat(flat)
    payload = {
        "fan": args.fan,
        "spec": spec.name,
        "stl": str(stl.as_posix()),
        "fit_envelope": not args.no_fit,
        "fit_changes": changes,
        "params": {
            "n_blades": params.n_blades,
            "hub_radius": params.hub_radius,
            "tip_radius": params.tip_radius,
            "rpm": params.rpm,
        },
        "measured_flat": None if measured is None else {
            "tip_dia_mm": measured[0],
            "depth_mm": measured[1],
            "hub_radius_mm": measured[2],
        },
        "nominal_fits_spec": nominal_fits_spec(flat, spec, measured),
        "mount_fits": rep.mount_fits,
        "mount_msg": rep.mount_msg,
        "watertight": rep.ok,
        "gauge": {
            "tip_od_mm": gauge.tip_od_mm,
            "hub_od_mm": gauge.hub_od_mm,
            "axial_depth_mm": gauge.axial_depth_mm,
            "cavity_dia_mm": gauge.cavity_dia_mm,
            "cavity_depth_mm": gauge.cavity_depth_mm,
            "rear_bore_dia_mm": gauge.rear_bore_dia_mm,
            "mount_ok": gauge.mount_ok,
            "frame_ok": gauge.frame_ok,
            "notes": list(gauge.notes),
        },
        "motor_mount": {
            "cavity_dia_mm": spec.motor_mount.cavity_dia_mm,
            "cavity_depth_mm": spec.motor_mount.cavity_depth_mm,
            "rear_bore_dia_mm": spec.motor_mount.rear_bore_dia_mm,
            "shaft_dia_mm": spec.motor_mount.shaft_dia_mm,
            "min_wall_mm": spec.motor_mount.min_wall_mm,
            "min_hub_height_mm": spec.motor_mount.min_hub_height_mm,
            "provenance": "measured cup 2026-08-31 (semi-official); confirm when commercial hub arrives",
        },
    }
    (out_dir / "print_fit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"STL: {stl}")
    print(f"sheet: {out_dir / 'print_sheet.md'}")
    print(f"checklist: {out_dir / 'mount_checklist.md'}")
    print(f"mount_fits={rep.mount_fits}  gauge mount_ok={gauge.mount_ok} frame_ok={gauge.frame_ok}")
    print(f"nominal_fits_spec={payload['nominal_fits_spec']}")
    for n in gauge.notes:
        print(f"  note: {n}")
    if not (rep.mount_fits and gauge.frame_ok and rep.ok):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
