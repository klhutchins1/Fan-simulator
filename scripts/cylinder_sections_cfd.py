"""V5 and V6 of the cylinder-sections spec (roadmap 27.4): full Assess CFD on wrapped blades.

Spec: docs/superpowers/specs/2026-10-12-cylinder-sections-design.md (checks fixed before any build).
Same settings as the Stock reference run (`scripts/screen_rank_audit.py` run_full: a12x25, hose "case",
8 procs, base cell 6 mm, 500 iters, PETG, parallel mesh) so the comparison is like for like.

- V5  refit Stock (wrapped) vs `runs/screen_rank_audit/stock_hubclip/full` (planar v2 Stock):
      raw free-air CFM within +-3 %, raw loaded CFM within +-5 %.
- V6  t9005 wrapped vs `runs/screen_rank_audit/t9005/full` (planar), with BEM on the same sliders:
      report only (does BEM's over-rating of leaned blades shrink?).

    python scripts/cylinder_sections_cfd.py --runs "T:/Projects/Fan Simulator/runs"
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.fan_spec import get_fan_spec
from fansim.geometry.features import features_from_flat
from fansim.optimize.isolated_eval import evaluate_candidate_isolated
from fansim.optimize.presets import assess_load
from fansim.optimize.search_space import stock_blade_flat

FREE_TOL, LOAD_TOL = 0.03, 0.05


def _raw(case: Path) -> dict:
    r = json.loads((case / "_eval_result.json").read_text(encoding="utf-8"))
    raw = r.get("raw", {})
    return {"free_raw": raw.get("free", {}).get("cfm"), "load_raw": raw.get("load", {}).get("cfm"),
            "cfm_free": r.get("cfm_free"), "cfm_load": r.get("cfm_load"),
            "efficiency": r.get("efficiency"), "actual_rpm": r.get("actual_rpm")}


def run_full(flat: dict, case: Path) -> dict:
    if (case / "_eval_result.json").is_file():
        return _raw(case)
    case.mkdir(parents=True, exist_ok=True)
    load_pa, _ = assess_load("case")
    t0 = time.monotonic()
    evaluate_candidate_isolated(
        flat, features_from_flat(flat), case, spec=get_fan_spec("a12x25"), procs=8,
        base_cell=0.006, iters=500, load_pa=load_pa, refine_op=False, material="PETG",
        parallel_mesh=True)
    out = _raw(case)
    out["wall_s"] = round(time.monotonic() - t0, 1)
    return out


def _t9005_flat(main: Path) -> dict:
    with open(main / "handoff/2026-10-09_to-qa-2/cfd_designs.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["design_id"] == "t9005":
                return json.loads(row["flat"])
    raise KeyError("t9005")


def _bem(flat: dict) -> dict:
    """BEM on the sliders (both models). It never sees the built blade, so it is the same for both."""
    from fansim.fan_bem import pq_curve
    from fansim.optimize.search_space import blade_from_flat
    from fansim.optimize.system_curve import bem_screen_cfm

    bp = blade_from_flat(flat)
    load_pa, _ = assess_load("case")
    free, load = bem_screen_cfm(bp, 2000.0, load_pa, 0.5)
    af = pq_curve(bp, 2000.0, tip_gap_mm=0.5, pressure_model="axial_force")
    return {"euler_free": free, "euler_load": load, "axial_force_free": float(af.free_delivery_cfm)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--main", type=Path, default=None, help="checkout holding handoff/ (default: runs/..)")
    a = ap.parse_args(argv)
    main_dir = a.main or a.runs.parent
    out_dir = a.runs / "cyl_sections"
    res_path = out_dir / "v5_v6.json"
    res = json.loads(res_path.read_text()) if res_path.is_file() else {}

    stock = dict(stock_blade_flat("a12x25"))
    assert stock.get("section_wrap") == "cylinder", "Stock recipe is not the wrapped refit"
    new = run_full(stock, out_dir / "stock_wrap" / "full")
    ref = _raw(a.runs / "screen_rank_audit" / "stock_hubclip" / "full")
    d_free = new["free_raw"] / ref["free_raw"] - 1.0
    d_load = new["load_raw"] / ref["load_raw"] - 1.0
    res["V5"] = {"wrapped": new, "reference_planar": ref, "d_free": round(d_free, 4),
                 "d_load": round(d_load, 4),
                 "pass": bool(abs(d_free) <= FREE_TOL and abs(d_load) <= LOAD_TOL)}
    out_dir.mkdir(parents=True, exist_ok=True)
    res_path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("V5", res["V5"], flush=True)

    flat = {**_t9005_flat(main_dir), "section_wrap": "cylinder"}
    wrapped = run_full(flat, out_dir / "t9005_wrap" / "full")
    planar = _raw(a.runs / "screen_rank_audit" / "t9005" / "full")
    res["V6"] = {"cfd_wrapped": wrapped, "cfd_planar": planar, "bem_sliders": _bem(flat),
                 "note": "CFD at 2000 rpm raw; BEM at 2000 rpm, 0.5 mm tip gap, hose 'case'"}
    res_path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("V6", res["V6"], flush=True)
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    os._exit(rc)
