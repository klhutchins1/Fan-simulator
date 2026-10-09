"""Export the current-solver CFD-scored axial designs as a CSV (geometry + CFD numbers).

For checks that compare a cheap model with CFD (BEM ranking audits, the QA bot's rule (c)). One row
per design, all on the same Assess setup (CFD_VERSION, mesh floor level 4, "case" hose):

  design_id, geometry ('stock' for the 7-station YAML recipe) or flat (inline JSON),
  cfd_free_cfm / cfd_load_cfm  raw CFD at 2000 rpm (before motor derate / print penalty),
  scored_free / scored_load / scored_eff  the Assess objectives, surf_level, source.

Sources: runs/screen_rank_audit/<name>/full (or full_floor4 when that level-4 re-run exists) and the
BEM-screen top 5 (runs/screen_rank_audit/bem_95xx/full). Infeasible runs and stock_dimples (no dimples,
2026-10-07 setup error) are left out.

    uv run python scripts/export_cfd_dataset.py --out handoff/<dir>/cfd_designs.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import screen_rank_audit as sra  # noqa: E402

EXCLUDE = {"stock_dimples"}
COLUMNS = ["design_id", "geometry", "flat", "rpm", "cfd_free_cfm", "cfd_load_cfm", "scored_free",
           "scored_load", "scored_eff", "surf_level", "source"]


def _level(flat: dict) -> int:
    from fansim.cfd.openfoam_case import surface_level_for_wall
    from fansim.geometry.blade import min_blade_wall_mm
    from fansim.optimize.search_space import blade_from_flat

    lvl = surface_level_for_wall(0.006, min_blade_wall_mm(blade_from_flat(flat)))
    return max(lvl, 3)  # the floor these runs were made with, unless re-run at 4 (full_floor4)


def rows() -> list[dict]:
    designs = {k: v for k, v in sra.designs().items() if k not in EXCLUDE}
    for jf in sorted((ROOT / "runs" / "bem_screen_top5" / "cockpit_assess").glob("design_*/design.json")):
        d = json.loads(jf.read_text(encoding="utf-8"))
        designs[f"bem_{d['trial']}"] = d["params"]
    out = []
    for name, flat in designs.items():
        floor4 = sra._read(sra.OUT / name / "full_floor4" / "result.json")
        r, lvl = (floor4, 4) if floor4 and floor4.get("feasible") else (
            sra._read(sra.OUT / name / "full" / "result.json"), None)
        if not (r and r.get("feasible") and r.get("free_raw_cfm") is not None):
            continue
        lvl = lvl or max(_level(flat), 3)
        if lvl < 4:
            continue  # coarse-mesh score: not comparable (§23.39)
        out.append({
            "design_id": name,
            "geometry": "stock" if name == "stock" else "",
            "flat": "" if name == "stock" else json.dumps(flat, sort_keys=True),
            "rpm": 2000,
            "cfd_free_cfm": round(float(r["free_raw_cfm"]), 3),
            "cfd_load_cfm": round(float(r["load_raw_cfm"]), 3) if r.get("load_raw_cfm") else "",
            "scored_free": round(float(r["cfm_free"]), 3),
            "scored_load": round(float(r["cfm_load"]), 3),
            "scored_eff": round(float(r["efficiency"]), 3),
            "surf_level": lvl,
            "source": str((sra.OUT / name / ("full_floor4" if floor4 else "full")).relative_to(ROOT)),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = rows()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(data)
    print(json.dumps({"rows": len(data), "out": str(out)}), flush=True)
    os._exit(0)  # skip the CPython/OCP teardown crash on this box


if __name__ == "__main__":
    main()
