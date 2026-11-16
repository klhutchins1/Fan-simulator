"""One registered attempt to line the wrapped Stock blade up with the Noctua STL.

The pass/fail rule is docs/validation/audits/2026-11-13-stock-outline-prereg.md, written
before this run. This script does not modify config/problems/a12x25_reference.yaml.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs" / "qa" / "stock_fit"))

from fansim.geometry.config import load_blade_params  # noqa: E402
from surf_lib import build_full, official_distance, v2_check  # noqa: E402

# fit_log_v3_cylinder.txt iteration 3, built minus reference, r/R 0.50 .. 0.99.
LE_DELTA = (
    (1.46, -0.13),
    (0.94, -0.36),
    (0.23, -0.28),
    (-0.24, -0.12),
    (-0.39, 0.35),
    (0.19, 0.99),
)
OUT = ROOT / "runs" / "outline_match"


def _extrap_root(stations):
    a, b = stations[1], stations[2]
    f = (stations[0].r_frac - a.r_frac) / (b.r_frac - a.r_frac)
    root = stations[0]
    return dataclasses.replace(
        root,
        stagger_deg=a.stagger_deg + f * (b.stagger_deg - a.stagger_deg),
        sweep=a.sweep + f * (b.sweep - a.sweep),
        skew=a.skew + f * (b.skew - a.skew),
    )


def _candidate(base, scale: float):
    moved = []
    for i, s in enumerate(base.stations):
        if i == 0:
            moved.append(s)
            continue
        dz, ds = LE_DELTA[i - 1]
        moved.append(dataclasses.replace(s, sweep=s.sweep - scale * dz, skew=s.skew - scale * ds))
    moved[0] = _extrap_root(moved)
    return dataclasses.replace(base, stations=moved)


def _dump(params, path: Path) -> None:
    raw = yaml.safe_load((ROOT / "config/problems/a12x25_reference.yaml").read_text())
    keys = ("r_frac", "chord", "stagger_deg", "thickness", "max_camber", "camber_pos",
            "sweep", "skew", "lean_deg", "le_sweep", "le_skew")
    raw["stations"] = [{k: round(float(getattr(s, k)), 4) for k in keys} for s in params.stations]
    path.write_text(
        "# Outline candidate from scripts/outline_match.py. Not Stock until the 2026-11-13 "
        "pre-registration passes and Kimball accepts the overlay.\n"
        + yaml.safe_dump(raw, sort_keys=False, width=200)
    )


def _judge(params, stl: Path) -> dict:
    mesh = build_full(params, stl)
    ok, rows = v2_check(stl)
    dist = official_distance(params, mesh)
    return {"v2_ok": ok, "v2": rows, "dist": dist}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    v3 = load_blade_params(ROOT / "config/problems/a12x25_reference.yaml")
    planar = load_blade_params(ROOT / "config/problems/a12x25_reference_planar.yaml")
    print("export planar v2 (comparison only, not judged)", flush=True)
    build_full(planar, OUT / "planar_v2.stl")

    tried = []
    chosen = None
    for scale, tag in ((1.0, "full"), (0.5, "half")):
        params = _candidate(v3, scale)
        stl = OUT / f"candidate_{tag}.stl"
        print(f"build {tag}", flush=True)
        result = _judge(params, stl)
        tried.append({"scale": scale, **result})
        print(tag, "v2_ok", result["v2_ok"], "mean", result["dist"]["mean_mm"],
              "outer", result["dist"]["outer_0.8-1.0_mm"],
              "hub", result["dist"]["by_r/R"].get("0.4-0.5"), flush=True)
        chosen = (params, stl, result, tag)
        if result["v2_ok"]:
            break

    params, stl, result, tag = chosen
    dist = result["dist"]
    hub = dist["by_r/R"].get("0.4-0.5")
    passed = bool(
        result["v2_ok"]
        and dist["mean_mm"] <= 0.41
        and dist["outer_0.8-1.0_mm"] <= 0.26
        and hub is not None
        and hub <= 0.70
    )
    _dump(params, OUT / "candidate.yaml")
    summary = {"passed": passed, "used": tag, "tried": tried, "stl": str(stl)}
    (OUT / "result.json").write_text(json.dumps(summary, indent=1))
    print("PASSED" if passed else "FAILED", tag, flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as exc:  # noqa: BLE001
        print("ERROR", exc, flush=True)
        rc = 2
    raise SystemExit(rc)
