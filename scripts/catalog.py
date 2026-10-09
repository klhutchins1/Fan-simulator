"""Build and browse the unified design catalog — every design, in one place.

    uv run python scripts/catalog.py build        # (re)scan all runs + measurements -> catalog/catalog.db
    uv run python scripts/catalog.py list          # one line per design (add --measured / --pareto)
    uv run python scripts/catalog.py show <id>     # full record for one design
    uv run python scripts/catalog.py stats         # counts

The catalog is a read-only index over the existing per-run stores + validation/measurements/; rebuild
it whenever you add designs or record measurements.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.catalog import build_catalog, catalog_stats, get_entry, load_catalog  # noqa: E402


def _fmt(v, w=6, d=1):
    return f"{v:{w}.{d}f}" if isinstance(v, (int, float)) else " " * (w - 1) + "-"


def cmd_build(_a):
    n = build_catalog()
    s = catalog_stats()
    print(f"Catalog built: {n} designs from {s['runs']} runs "
          f"({s['pareto']} pareto, {s['user_assessed']} assessed, {s['measured']} measured) "
          f"-> catalog/catalog.db")


def cmd_stats(_a):
    for k, v in catalog_stats().items():
        print(f"  {k:16s} {v}")


def cmd_list(a):
    rows = load_catalog()
    if a.pareto:
        rows = [r for r in rows if r.is_pareto]
    if a.measured:
        rows = [r for r in rows if r.has_measurement]
    if not rows:
        print("(empty — run `catalog build` first, or loosen the filter)")
        return
    print(f"{'design_id':22s} {'src':9s} {'nB':>2s} {'free':>6s} {'load':>6s} {'eff':>5s} "
          f"{'noise':>5s} {'measured':>8s} {'sim err':>7s}  files")
    print("-" * 104)
    for r in rows:
        meas = _fmt(r.measured_cfm, 8) if r.has_measurement else " " * 8
        err = (f"{r.cfm_error_pct:+.0f}%" if r.cfm_error_pct is not None else "").rjust(7)
        files = "STL" if r.stl_path else ""
        files += " print" if r.print_dir else ""
        files += " ★" if r.is_pareto else ""
        print(f"{r.design_id:22s} {r.source:9s} {str(r.n_blades or '-'):>2s} "
              f"{_fmt(r.cfm_free)} {_fmt(r.cfm_load)} {_fmt(r.efficiency,5)} {_fmt(r.noise,5,0)} "
              f"{meas} {err}  {files}")


def cmd_show(a):
    e = get_entry(a.design_id)
    if e is None:
        print(f"No design '{a.design_id}' in the catalog. Try `catalog list`.")
        return
    print(f"# {e.design_id}   ({e.source}{', ★ pareto' if e.is_pareto else ''})")
    print(f"  run/trial : {e.run} / {e.trial}")
    print(f"  sim       : {e.n_blades} blades  free {e.cfm_free} / load {e.cfm_load} CFM  "
          f"eff {e.efficiency}%  noise {e.noise}")
    print(f"  files     : STL={e.stl_path or '-'}\n              print={e.print_dir or '-'}")
    if e.has_measurement:
        print(f"  MEASURED  : {len(e.measured)} point(s)")
        for m in e.measured:
            print(f"    - {m}")
        if e.cfm_error_pct is not None:
            print(f"  sim vs real: measured {e.measured_cfm} CFM, sim over/under-reads {e.cfm_error_pct:+.0f}%")
    else:
        print("  MEASURED  : none yet")
    print(f"  params    : {json.dumps(e.params)[:300]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="unified design catalog")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("build").set_defaults(fn=cmd_build)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    pl = sub.add_parser("list"); pl.add_argument("--pareto", action="store_true")
    pl.add_argument("--measured", action="store_true"); pl.set_defaults(fn=cmd_list)
    ps = sub.add_parser("show"); ps.add_argument("design_id"); ps.set_defaults(fn=cmd_show)
    a = ap.parse_args()
    if not getattr(a, "fn", None):
        ap.print_help()
        return 1
    a.fn(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
