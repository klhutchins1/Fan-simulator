"""Pre-registered checks F1-F4 of the 27.3e plane fix (audit 2026-10-17-push-row-planes) on the existing cases.

Recomputes FLOW_REPORT_VERSION 4 metrics (no CFD). Writes runs/push_planes_checks.json.

    python scripts/push_planes_checks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from fansim.cfd.cockpit_viz import load_case_mesh  # noqa: E402
from fansim.cfd.flow_report import FLOW_REPORT_VERSION, slab_centres, slab_half_width  # noqa: E402
from fansim.cfd.flow_report_case import blade_z_extent, case_geometry, load_or_compute_metrics  # noqa: E402
from stock_flow_repeats import proposed_tolerances  # noqa: E402

MESHES = ("m1", "m2", "m3", "m4", "m5")
GROUPS = {
    "stock_mesh": [ROOT / "runs/stock_flow_mesh_repeats" / m for m in MESHES],
    "stock_same_mesh": [ROOT / "runs/stock_flow_repeats" / f"r{i}" for i in range(1, 6)],
    "9604": [ROOT / "runs/design_flow_mesh_repeats/9604" / m for m in MESHES],
    "9610": [ROOT / "runs/design_flow_mesh_repeats/9610" / m for m in MESHES],
}


def _case(case: Path) -> dict:
    mesh = load_case_mesh(case)
    hub, tip, zf = case_geometry(case, mesh)
    bz = blade_z_extent(case, hub_r=hub)
    m = load_or_compute_metrics(case, mesh=mesh)
    raw = json.loads((case / "_eval_result.json").read_text(encoding="utf-8"))
    zi, ze = slab_centres(tip_r=tip, z_fan=zf, blade_z=bz)
    h = slab_half_width(tip)
    disjoint = bz is not None and zi + h < min(bz) and ze - h > max(bz)
    return {"case": str(case.relative_to(ROOT)), "metrics": m.to_dict(), "blade_z": bz,
            "slabs": [zi, ze], "f2_disjoint": disjoint, "cfm_load": raw.get("cfm_load")}


def main() -> int:
    out: dict = {"version": FLOW_REPORT_VERSION, "groups": {}}
    for g, cases in GROUPS.items():
        out["groups"][g] = []
        for c in cases:
            rec = _case(c)
            out["groups"][g].append(rec)
            print(g, c.name, "push", round(rec["metrics"]["mean_dp0_pa"], 2), "cfm", round(rec["cfm_load"], 2),
                  "F2", rec["f2_disjoint"], flush=True)
    G = out["groups"]
    st = G["stock_mesh"]
    f1 = []
    for a, b in zip(G["9604"], st):
        dp = a["metrics"]["mean_dp0_pa"] / b["metrics"]["mean_dp0_pa"] - 1
        dq = a["cfm_load"] / b["cfm_load"] - 1
        f1.append({"push": round(dp, 4), "cfm": round(dq, 4), "same_sign": (dp > 0) == (dq > 0)})
    out["F1"] = {"pairs": f1, "pass": all(p["same_sign"] for p in f1)}
    out["F2"] = {"pass": all(r["f2_disjoint"] for rows in G.values() for r in rows)}
    f3 = {}
    for g in ("stock_mesh", "stock_same_mesh"):
        rows = G[g]
        noise = [r["metrics"].get("noise_swl_db") for r in rows]
        bt, nd = proposed_tolerances([r["metrics"]["mean_dp0_pa"] for r in rows],
                                     [r["metrics"]["band_dp0_pa"] for r in rows],
                                     None if any(v is None for v in noise) else noise)
        f3[g] = {"proposed_BAND_TOL": bt, "proposed_NOISE_MARGIN_DB": nd,
                 "mean_dp0": [round(r["metrics"]["mean_dp0_pa"], 3) for r in rows]}
    out["F3"] = f3
    (ROOT / "runs" / "push_planes_checks.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("F1", "F2", "F3")}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
