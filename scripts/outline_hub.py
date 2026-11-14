"""One registered attempt to set the hub wall to the Noctua radius.

The blade stations stay on the outline candidate. Only hub_radius and root_embed change,
and their difference stays 19.5 mm so the sections do not move. The pass rule is
docs/validation/audits/2026-11-13-stock-hub-wall-prereg.md.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs" / "qa" / "stock_fit"))

from fansim.geometry.config import load_blade_params  # noqa: E402
from scripts.outline_match import _candidate  # noqa: E402
from surf_lib import build_full, official_distance, v2_check  # noqa: E402

# (hub_radius, root_embed). root_embed = hub_radius - 19.5, the v3 root radius.
TRIES = ((26.0, 6.5), (25.5, 6.0))
OUT = ROOT / "runs" / "outline_hub"


def with_hub(params, hub_radius: float, root_embed: float):
    return dataclasses.replace(params, hub_radius=hub_radius, root_embed=root_embed)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    v3 = load_blade_params(ROOT / "config/problems/a12x25_reference.yaml")
    base = _candidate(v3, 1.0)
    tried = []
    chosen = None
    for hub, embed in TRIES:
        params = with_hub(base, hub, embed)
        assert abs((params.hub_radius - params.root_embed) - 19.5) < 1e-9
        stl = OUT / f"hub_{hub:.1f}.stl"
        print(f"build hub {hub}", flush=True)
        mesh = build_full(params, stl)
        ok, rows = v2_check(stl)
        dist = official_distance(params, mesh)
        result = {"hub": hub, "v2_ok": ok, "v2": rows, "dist": dist}
        tried.append(result)
        hub_band = dist["by_r/R"].get("0.4-0.5")
        print(hub, "v2_ok", ok, "mean", dist["mean_mm"], "outer", dist["outer_0.8-1.0_mm"],
              "hubband", hub_band, flush=True)
        chosen = (params, stl, result)
        if ok and dist["outer_0.8-1.0_mm"] <= 0.26:
            break
    params, stl, result = chosen
    dist = result["dist"]
    band = dist["by_r/R"].get("0.4-0.5")
    passed = bool(
        result["v2_ok"]
        and dist["mean_mm"] <= 0.41
        and dist["outer_0.8-1.0_mm"] <= 0.26
        and band is not None
        and band <= 0.70
    )
    (OUT / "result.json").write_text(json.dumps({"passed": passed, "tried": tried, "stl": str(stl)}, indent=1))
    print("PASSED" if passed else "FAILED", result["hub"], flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as exc:  # noqa: BLE001
        print("ERROR", exc, flush=True)
        rc = 2
    raise SystemExit(rc)
