"""LBM geometry A/B campaign: default vs sickle / notched-tips + casing STLs.

Builds variant impeller STLs from a base trial JSON, exports plain and stepped
``casing.stl`` for the ducted path, then optionally runs FluidX3D shut-off on
each *impeller*. ``--dry-run`` only exports geometry + a campaign plan (no GPU).

Stepped inlet is casing-only: LBM ``mode=shutoff`` does not ingest casing STLs;
the pair is recorded with honesty notes for OpenFOAM / future ducted LBM.

Usage:
  uv run python scripts/run_lbm_geometry_ab.py --base-json runs/.../base.json --dry-run
  uv run python scripts/run_lbm_geometry_ab.py --base-json ... --out runs/campaign_lbm_geom
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cfd.casing import export_casing_stl  # noqa: E402
from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM, rig_for_impeller  # noqa: E402
from fansim.cfd.lbm_geometry_ab import (  # noqa: E402
    CASING_VARIANTS,
    HONESTY,
    IMPORTER_VARIANTS,
    blade_params_for_variant,
    compare_shutoff_deltas,
    load_base_params,
    stepped_inlet_row,
    summary_markdown,
)
from fansim.geometry.export import export_stl  # noqa: E402


def _build_impeller_stl(flat: dict, name: str, dest: Path):
    from fansim.geometry import build_impeller

    params = blade_params_for_variant(flat, name)
    solid = build_impeller(params)
    export_stl(solid, dest, tolerance=0.02, angular_tolerance=0.1)
    return params


def _export_casings(flat: dict, out: Path) -> dict[str, str]:
    """Export plain + stepped circular casing STLs sized to the baseline blade."""
    params = blade_params_for_variant(flat, "default")
    tip_mm = float(flat.get("tip_gap_mm") or OPTIMIZER_TIP_GAP_MM)
    rig = rig_for_impeller(params, tip_gap_mm=tip_mm)
    paths: dict[str, str] = {}
    for slug, stepped, _label in CASING_VARIANTS:
        path = out / f"{slug}.stl"
        export_casing_stl(rig, path, stepped=stepped)
        paths[slug] = str(path)
    return paths


def main() -> int:
    ap = argparse.ArgumentParser(
        description="LBM geometry A/B (sickle / notched / stepped casing) campaign"
    )
    ap.add_argument("--base-json", type=Path, required=True)
    ap.add_argument("--trial", type=int, default=None)
    ap.add_argument("--out", type=Path, default=Path("runs/campaign_lbm_geometry_ab"))
    ap.add_argument("--dry-run", action="store_true", help="export STLs only (no FluidX3D)")
    ap.add_argument("--skip-casing", action="store_true", help="skip plain/stepped casing export")
    ap.add_argument("--steps", type=int, default=48000)
    ap.add_argument("--re", type=float, default=8000.0)
    ap.add_argument("--tip-clear-mm", type=float, default=2.7)
    args = ap.parse_args()

    flat = load_base_params(args.base_json, args.trial)
    args.out.mkdir(parents=True, exist_ok=True)
    results = []

    for slug, label in IMPORTER_VARIANTS:
        stl = args.out / f"{slug}.stl"
        params = _build_impeller_stl(flat, slug, stl)
        row = {
            "variant": slug,
            "label": label,
            "stl": str(stl),
            "n_blades": params.n_blades,
            "tip_notch_count": int(params.tip_notch_count),
            "sickle": slug == "sickle",
        }
        if args.dry_run:
            row["shutoff"] = None
            row["skipped"] = "dry-run"
        else:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "evaluate_shutoff", PROJECT / "scripts" / "evaluate_shutoff.py"
            )
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            row["shutoff"] = mod.evaluate_shutoff(
                stl,
                label=slug,
                steps=args.steps,
                re=args.re,
                tip_clear_mm=args.tip_clear_mm,
                out_dir=args.out,
            )
        results.append(row)

    casing_paths: dict[str, str] = {}
    if not args.skip_casing:
        casing_paths = _export_casings(flat, args.out)

    results.append(
        stepped_inlet_row(
            casing_plain=casing_paths.get("casing_plain"),
            casing_stepped=casing_paths.get("casing_stepped"),
        )
    )

    deltas = compare_shutoff_deltas(results)
    payload = {
        "date": str(date.today()),
        "base_json": str(args.base_json),
        "base_trial": args.trial,
        "dry_run": bool(args.dry_run),
        "honesty": HONESTY,
        "casing_stls": casing_paths,
        "results": results,
        "deltas": deltas,
    }
    (args.out / "summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "summary.md").write_text(summary_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
