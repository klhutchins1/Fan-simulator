"""A/B a CFD speed change on Stock through the real cockpit Assess path.

Runs ``evaluate_candidate_isolated`` on the a12x25 Stock recipe with the cockpit's Assess
settings (procs 8, base_cell 0.006, 500 iters, "case" hose, PETG, no refine-op), once per
variant, sequentially (concurrent CFD on this box distorts both runs). Each variant writes
``<out>/<variant>/ab_result.json`` with wall time, cell count and the objectives, so a change
is only adopted when its objectives match the baseline within the stated tolerance.

    uv run python scripts/ab_assess_speed.py --variants serial,parallel_mesh

Judge by the JSON (importing fansim.cfd can crash CPython at teardown on this box).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.timing import mesh_cells  # noqa: E402
from fansim.fan_spec import get_fan_spec  # noqa: E402
from fansim.geometry.features import features_from_flat  # noqa: E402
from fansim.optimize.isolated_eval import evaluate_candidate_isolated  # noqa: E402
from fansim.optimize.presets import assess_load  # noqa: E402
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat  # noqa: E402

VARIANTS = {
    "serial": {"parallel_mesh": False},
    "parallel_mesh": {"parallel_mesh": True},
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variants", default="serial,parallel_mesh")
    ap.add_argument("--out", default="runs/assess_speed_ab")
    ap.add_argument("--preset", default="case")
    args = ap.parse_args()

    flat = stock_blade_flat("a12x25")
    features = features_from_flat(flat)
    blade_from_flat(flat, features)  # fail fast on a bad recipe before any CFD
    load_pa, _ = assess_load(args.preset)
    for name in [v.strip() for v in args.variants.split(",") if v.strip()]:
        kw = VARIANTS[name]
        wd = Path(args.out) / name
        t0 = time.time()
        row: dict = {"variant": name, **kw, "load_pa": load_pa, "preset": args.preset}
        try:
            res = evaluate_candidate_isolated(
                flat, features, wd, spec=get_fan_spec("a12x25"), procs=8, base_cell=0.006,
                iters=500, load_pa=load_pa, refine_op=False, material="PETG", **kw)
            row.update(feasible=res.feasible, reason=res.reason, cfm_free=res.cfm_free,
                       cfm_load=res.cfm_load, efficiency=res.efficiency,
                       free_raw_cfm=res.raw.get("free", {}).get("cfm"),
                       load_raw_cfm=res.raw.get("load", {}).get("cfm"),
                       converged=res.raw.get("converged"))
        except Exception as exc:  # noqa: BLE001 — record and continue to the next variant
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["wall_s"] = round(time.time() - t0, 1)
        row["cells"] = mesh_cells(wd)
        wd.mkdir(parents=True, exist_ok=True)
        (wd / "ab_result.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
        print(json.dumps(row), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
