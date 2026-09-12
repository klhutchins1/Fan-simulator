# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Export a run's Pareto finalists as print-ready deliverables (plan Phase 5).

For each finalist in runs/<dir>/pareto.json this writes runs/<dir>/print/trial_XXXX/:
  * impeller.stl  — fine-tessellation, optionally with a parameterized motor-shaft bore
  * print_sheet.md — material/temps, orientation, supports, balance, bore caveat
plus a print/index.md table. Non-watertight builds are flagged and NOT written as printable.

Usage:
    uv run python scripts/export_finalists.py --run runs/opt_extended2 [--material PETG]
        [--bore-dia 5.0 | --no-bore] [--set-screw 3.0] [--rpm 2000]

BORE CAVEAT: --bore-dia is a PLACEHOLDER until you measure your motor's shaft/boss; re-export after.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.geometry.features import Features  # noqa: E402
from fansim.manufacturability.print_export import (  # noqa: E402
    BoreSpec,
    balance_summary,
    export_print_ready,
    print_readme,
    recommend_print_settings,
)
from fansim.manufacturability.printability_score import grade_printability  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402
from fansim.fan_spec import get_fan_spec  # noqa: E402

OBJ_KEYS = ("cfm_free", "cfm_load", "efficiency", "noise_swl")


def _load_finalists(run_dir: Path) -> list[dict]:
    pj = run_dir / "pareto.json"
    if not pj.exists():
        raise SystemExit(f"No pareto.json in {run_dir} (run an optimization first).")
    data = json.loads(pj.read_text())
    rows = data if isinstance(data, list) else (data.get("designs") or data.get("pareto") or [])
    if not rows:
        raise SystemExit(f"pareto.json in {run_dir} has no finalists.")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="export Pareto finalists as print-ready STLs")
    ap.add_argument("--run", required=True, help="optimization run directory (with pareto.json)")
    ap.add_argument("--material", default="PETG")
    ap.add_argument("--bore-dia", type=float, default=5.0,
                    help="center shaft-bore diameter mm (PLACEHOLDER — measure your motor)")
    ap.add_argument("--no-bore", action="store_true", help="export a solid hub (no bore)")
    ap.add_argument("--set-screw", type=float, default=0.0, help="radial set-screw hole dia mm")
    ap.add_argument("--rpm", type=float, default=2000.0, help="RPM for the balance force estimate")
    ap.add_argument("--fan-model", default="a12x25", help="fan model whose motor mount to carve")
    ap.add_argument("--no-mount", action="store_true", help="skip the motor-mount cavity (use --bore)")
    args = ap.parse_args()

    run_dir = Path(args.run)
    finalists = _load_finalists(run_dir)
    out_root = run_dir / "print"
    out_root.mkdir(parents=True, exist_ok=True)
    settings = recommend_print_settings(args.material)
    mount = None if args.no_mount else get_fan_spec(args.fan_model).motor_mount
    bore = None if (args.no_bore or mount is not None) else BoreSpec(
        bore_dia_mm=args.bore_dia, set_screw_dia_mm=args.set_screw, placeholder=True)

    if mount is not None:
        mount_hdr = (f"motor cup {mount.cavity_dia_mm:.0f} mm × {mount.cavity_depth_mm:.0f} mm "
                     f"({args.fan_model}) — needs hub radius ≥ {mount.cavity_dia_mm/2+mount.min_wall_mm:.0f} mm")
    else:
        mount_hdr = "solid hub (no bore)" if bore is None else \
            f"bore {bore.bore_dia_mm:.2f} mm (PLACEHOLDER — measure your motor)"
    index = ["# Print-ready finalists — " + run_dir.name, "",
             f"Material **{settings['material']}** · " + mount_hdr, "",
             "| trial | blades | dia×depth mm | CFM free/load | eff % | noise | print difficulty | mountable | watertight |",
             "|---|---|---|---|---|---|---|---|---|"]
    ok_count = 0
    mountable_count = 0
    for row in finalists:
        flat = row.get("params", row)
        trial = row.get("trial", "?")
        params = blade_from_flat(flat, Features(**{k: flat[k] for k in flat
                                                   if k.startswith(("tubercle", "serration", "dimple"))}))
        d = out_root / f"trial_{trial:04d}" if isinstance(trial, int) else out_root / f"trial_{trial}"
        d.mkdir(parents=True, exist_ok=True)
        stl = d / "impeller.stl"
        try:
            report = export_print_ready(params, stl, mount=mount, bore=bore)
        except Exception as exc:  # noqa: BLE001 - one bad finalist shouldn't stop the batch
            index.append(f"| {trial} | — | — | — | — | — | — | BUILD FAILED: {type(exc).__name__} |")
            print(f"  trial {trial}: BUILD FAILED — {exc}")
            continue
        balance = balance_summary(params, rpm=args.rpm)
        objs = {k: row[k] for k in OBJ_KEYS if k in row}
        (d / "print_sheet.md").write_text(
            print_readme(f"{run_dir.name} · trial {trial}", params, args.material,
                         report, balance, settings, bore, objs), encoding="utf-8")
        (lo, hi) = report.bounds_mm
        dia = 2.0 * max(abs(lo[0]), abs(hi[0]), abs(lo[1]), abs(hi[1]))
        depth = hi[2] - lo[2]
        wt = "YES" if report.ok else "NO — non-manifold"
        ok_count += report.ok
        grade = grade_printability(params)
        pc = grade.printer_class.split(" (")[0].split(" —")[0]
        mnt = ("YES" if report.mount_fits else "NO — hub too small") if report.mount_fits is not None else "—"
        mountable_count += 1 if report.mount_fits else 0
        index.append(
            f"| {trial} | {params.n_blades} | {dia:.0f}×{depth:.0f} | "
            f"{row.get('cfm_free', float('nan')):.0f}/{row.get('cfm_load', float('nan')):.0f} | "
            f"{row.get('efficiency', float('nan')):.0f} | {row.get('noise_swl', float('nan')):.0f} | "
            f"{grade.difficulty:.0f}/100 {pc} | {mnt} | {wt} |")
        print(f"  trial {trial}: {stl}  ({wt}, mount={mnt})")

    (out_root / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"\n{ok_count}/{len(finalists)} printable → {out_root}\\index.md")
    if mount is not None:
        print(f"MOUNTABLE on {args.fan_model}: {mountable_count}/{len(finalists)} — the rest have hubs "
              f"too small to house the {mount.cavity_dia_mm:.0f} mm motor (aero wants a small hub; the "
              "real mount needs a bigger one — a genuine tradeoff).")
    if bore is not None:
        print("NOTE: bore diameter is a PLACEHOLDER — measure your motor's shaft and re-export.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
