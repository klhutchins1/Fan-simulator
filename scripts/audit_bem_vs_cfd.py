"""Audit #4 helper: BEM pre-screen free-air CFM vs validated CFD (Stock v1, Stock v2, re-scored designs).

Reads docs/validation/rescore_19_8.json and the catalog DB READ-ONLY. Writes
docs/validation/audits/bem_vs_cfd_audit4.json. Note: re-scored designs use the optimizer's default mesh
settings, not the complete ring+frame+layers setup used for the Stock points.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from fansim.fan_bem import pq_curve  # noqa: E402
from fansim.geometry.config import load_blade_params  # noqa: E402

# Validated CFD v5, complete setup (ring + frame + layers); docs/validation/a12x25_pq_report.md
CFD_STOCK = {
    "stock_v2": {"cfg": "a12x25_reference.yaml", "cfm": {0: 56.5, 5: 49.8, 10: 40.2}},
    "stock_v1": {"cfg": "a12x25_reference_v1.yaml", "cfm": {0: 77.4}},
}


def flow_at_dp(curve, dp):
    """Flow (CFM) where the static rise falls through dp (linear between sweep points)."""
    pts = curve.points
    for a, b in zip(pts, pts[1:]):
        if a.dp_static_pa >= dp > b.dp_static_pa:
            t = (a.dp_static_pa - dp) / (a.dp_static_pa - b.dp_static_pa)
            return a.flow_cfm + t * (b.flow_cfm - a.flow_cfm)
    return None


def spearman(x, y):
    from scipy.stats import spearmanr
    return float(spearmanr(x, y).statistic)


def rescored_params(rescore: Path, catalog: Path):
    import rescore_designs as R
    data = json.loads(rescore.read_text(encoding="utf-8"))
    ids = [k for k, v in data["designs"].items() if v.get("status") == "ok"]
    con = sqlite3.connect(f"file:{catalog.as_posix()}?mode=ro", uri=True)
    out = []
    for k in ids:
        row = con.execute("SELECT params FROM designs WHERE design_id=?", (k,)).fetchone()
        if not row:
            continue
        bp, _ = R.reconstruct(json.loads(row[0]))
        v = data["designs"][k]
        out.append((k, bp, v["new"]["cfm_free"], v["new"]["actual_rpm"], v.get("converged")))
    con.close()
    return out


def main():
    data_root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT   # checkout holding rescore json + catalog
    rows = []
    for name, spec in CFD_STOCK.items():
        bp = load_blade_params(ROOT / "config/problems" / spec["cfg"])
        c = pq_curve(bp, bp.rpm)
        rows.append({"id": name, "cfd_cfm": spec["cfm"][0], "bem_cfm": c.free_delivery_cfm,
                     "bem_shutoff_pa": c.shutoff_dp_pa, "converged": c.converged,
                     "bem_cfm_at_dp": {str(d): flow_at_dp(c, d) for d in (0, 5, 10)},
                     "cfd_cfm_at_dp": spec["cfm"], "mesh": "complete setup"})
    for k, bp, cfd, rpm, conv in rescored_params(data_root / "docs/validation/rescore_19_8.json",
                                                 data_root / "catalog/catalog.db"):
        c = pq_curve(bp, rpm or bp.rpm)
        rows.append({"id": k, "cfd_cfm": cfd, "bem_cfm": c.free_delivery_cfm,
                     "bem_shutoff_pa": c.shutoff_dp_pa, "converged": c.converged,
                     "mesh": "optimizer default mesh", "cfd_converged": conv})
    for r in rows:
        r["err_pct"] = 100.0 * (r["bem_cfm"] - r["cfd_cfm"]) / r["cfd_cfm"]
    n = len(rows)
    res = {"n_designs": n, "rows": rows}
    if n >= 3:
        res["spearman"] = spearman([r["bem_cfm"] for r in rows], [r["cfd_cfm"] for r in rows])
    out = ROOT / "docs/validation/audits/bem_vs_cfd_audit4.json"
    out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
