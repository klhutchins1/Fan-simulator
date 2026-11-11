"""Export a frame-fitted, motor-cup-carved A12x25 Stock impeller (headless).

Prefer the cockpit for day-to-day use: Fan → Design → **Export print STL**
(with Fit hub + Fit frame on). This script is the same path for CI / batch.

Usage:
    uv run python scripts/export_a12x25_print_ready.py
    uv run python scripts/export_a12x25_print_ready.py --out exports/my_print
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cockpit.placement import fit_envelope, measure_flat, nominal_fits_spec  # noqa: E402
from fansim.fan_spec import get_fan_spec  # noqa: E402
from fansim.manufacturability.mount_gauge import write_print_fit_sidecars  # noqa: E402
from fansim.manufacturability.print_export import (  # noqa: E402
    balance_summary,
    export_print_ready,
    print_readme,
    recommend_print_settings,
)
from fansim.manufacturability.print_id import (  # noqa: E402
    export_stem,
    git_head,
    issue_print_id,
    recipe_hash,
    record_export,
)
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Headless print-ready A12x25 export (GUI: Design → Export print STL)"
    )
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
        changes = [f"{c.field}: {c.before} -> {c.after}" for c in placed.changes]

    params = blade_from_flat(flat)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    print_id = issue_print_id()
    base = "a12x25_stock_reference"
    out_dir = Path(args.out) if args.out else Path("exports") / f"print_a12x25_stock_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    stl = out_dir / f"{export_stem(print_id, base, stamp)}.stl"

    material = args.material or spec.material
    rep = export_print_ready(params, stl, mount=spec.motor_mount, print_id=print_id)
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
        print_id=print_id,
    )
    (out_dir / "print_sheet.md").write_text(sheet, encoding="utf-8")
    (stl.with_suffix(".md")).write_text(sheet, encoding="utf-8")

    gauge = write_print_fit_sidecars(
        stl,
        spec,
        report_mount_fits=rep.mount_fits,
        report_mount_msg=rep.mount_msg or "",
        params_summary={
            "n_blades": params.n_blades,
            "hub_radius": params.hub_radius,
            "tip_radius": params.tip_radius,
            "rpm": params.rpm,
            "fit_envelope": not args.no_fit,
            "fit_changes": changes,
            "nominal_fits_spec": nominal_fits_spec(flat, spec, measure_flat(flat)),
        },
        extra={
            "print_id": print_id,
            "design_id": base,
            "section_wrap": str(getattr(params, "section_wrap", "") or ""),
            "recipe_hash": recipe_hash(params),
            "git": git_head(),
            "material": material,
        },
    )
    record_export(
        print_id=print_id,
        design_id=base,
        recipe_hash=recipe_hash(params),
        section_wrap=str(getattr(params, "section_wrap", "") or ""),
        git=git_head(),
        material=material,
        stl=str(stl),
        session="print-session-1-article-B",
    )
    # Also keep the friendly names used by the north-star runbook.
    checklist = stl.with_name(stl.stem + "_mount_checklist.md")
    if checklist.is_file():
        (out_dir / "mount_checklist.md").write_text(checklist.read_text(encoding="utf-8"), encoding="utf-8")
    fit_json = stl.with_name(stl.stem + "_print_fit.json")
    if fit_json.is_file():
        (out_dir / "print_fit.json").write_text(fit_json.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"print_id: {print_id}")
    print(f"STL: {stl}")
    print(f"sheet: {out_dir / 'print_sheet.md'}")
    print(f"checklist: {out_dir / 'mount_checklist.md'}")
    print(f"mount_fits={rep.mount_fits}  gauge mount_ok={gauge.mount_ok} frame_ok={gauge.frame_ok}")
    print("(GUI equivalent: Fan -> Design -> Export print STL)")
    for n in gauge.notes:
        print(f"  note: {n}")
    if not (rep.mount_fits and gauge.frame_ok and rep.ok):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
