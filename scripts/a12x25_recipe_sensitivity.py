"""One-factor BEM sensitivity for the A12x25 reference-parametric Stock recipe.

Loads cockpit Stock (a12x25_reference.yaml), perturbs mid/tip stagger, mid/tip chord,
global max_camber, and tip lean within GUIDED-ish bands, and writes a markdown report.

Usage:
    uv run python scripts/a12x25_recipe_sensitivity.py
    uv run python scripts/a12x25_recipe_sensitivity.py --out docs/validation/a12x25_recipe_sensitivity.md
"""

from __future__ import annotations

import argparse
import copy
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.fan_bem import pq_curve  # noqa: E402
from fansim.geometry.blade import BladeParams, RadialStation  # noqa: E402
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat  # noqa: E402

PUB_FREE_AIR = 60.1
TIP_GAP_MM = 0.5


def _stations(params: BladeParams) -> tuple[RadialStation, RadialStation, RadialStation]:
    root, mid, tip = params.stations[0], params.stations[1], params.stations[2]
    return root, mid, tip


def _with_stations(params: BladeParams, root: RadialStation, mid: RadialStation,
                   tip: RadialStation) -> BladeParams:
    out = copy.deepcopy(params)
    out.stations = [root, mid, tip]
    return out


def _bem(params: BladeParams) -> dict[str, float]:
    curve = pq_curve(params, float(params.rpm), tip_gap_mm=TIP_GAP_MM)
    return {
        "free_cfm": float(curve.free_delivery_cfm),
        "shutoff_pa": float(curve.shutoff_dp_pa),
    }


def _cases(baseline: BladeParams) -> list[tuple[str, BladeParams]]:
    root, mid, tip = _stations(baseline)
    cases: list[tuple[str, BladeParams]] = [("baseline", baseline)]

    def add(label: str, r: RadialStation, m: RadialStation, t: RadialStation) -> None:
        cases.append((label, _with_stations(baseline, r, m, t)))

    # Mid stagger: Stock is 26°; GUIDED mid is 32–48 — raise toward data-driven band.
    add("stagger_mid=32", root, replace(mid, stagger_deg=32.0), tip)
    add("stagger_mid=38", root, replace(mid, stagger_deg=38.0), tip)
    add("stagger_mid=44", root, replace(mid, stagger_deg=44.0), tip)

    # Tip stagger: Stock 22°; GUIDED tip 18–38.
    add("stagger_tip=18", root, mid, replace(tip, stagger_deg=18.0))
    add("stagger_tip=28", root, mid, replace(tip, stagger_deg=28.0))
    add("stagger_tip=34", root, mid, replace(tip, stagger_deg=34.0))

    # Mid chord: Stock already 44 mm (above MAX_CHORD 40); probe ± around Stock.
    add("chord_mid=36", root, replace(mid, chord=36.0), tip)
    add("chord_mid=40", root, replace(mid, chord=40.0), tip)
    add("chord_mid=48", root, replace(mid, chord=48.0), tip)

    # Tip chord: Stock 38; GUIDED tip up to 40.
    add("chord_tip=30", root, mid, replace(tip, chord=30.0))
    add("chord_tip=40", root, mid, replace(tip, chord=40.0))

    # Camber: apply same max_camber on all stations (Stock mid/tip already 0.06).
    for cam in (0.02, 0.04, 0.06):
        add(
            f"max_camber={cam:g}",
            replace(root, max_camber=cam),
            replace(mid, max_camber=cam),
            replace(tip, max_camber=cam),
        )

    # Tip lean: Stock 26°; GUIDED lean_tip 0–45.
    add("lean_tip=10", root, mid, replace(tip, lean_deg=10.0))
    add("lean_tip=35", root, mid, replace(tip, lean_deg=35.0))
    add("lean_tip=45", root, mid, replace(tip, lean_deg=45.0))

    return cases


def _fmt_row(label: str, row: dict[str, float], base: dict[str, float]) -> str:
    d_cfm = row["free_cfm"] - base["free_cfm"]
    d_pa = row["shutoff_pa"] - base["shutoff_pa"]
    return (
        f"| `{label}` | {row['free_cfm']:.1f} | {d_cfm:+.1f} | "
        f"{row['shutoff_pa']:.1f} | {d_pa:+.1f} |"
    )


def run(out_path: Path) -> dict[str, Any]:
    flat = stock_blade_flat("a12x25")
    baseline = blade_from_flat(flat)
    assert 55.0 <= baseline.tip_radius <= 57.0
    assert 20.0 <= baseline.hub_radius <= 23.0
    assert baseline.n_blades == 9

    rows: list[tuple[str, dict[str, float]]] = []
    for label, params in _cases(baseline):
        rows.append((label, _bem(params)))

    base = rows[0][1]
    lines = [
        "# A12x25 Stock recipe — BEM one-factor sensitivity",
        "",
        "**Purpose:** Rank parametric knobs that move free-air / shut-off for the cockpit Stock "
        "recipe (`a12x25_reference.yaml`) before any experimental CFD candidate.",
        "",
        "**Method:** `pq_curve(..., tip_gap_mm=0.5)` at Stock RPM. One factor at a time; "
        "envelope radii and blade count unchanged.",
        "",
        f"**Published free-air:** {PUB_FREE_AIR} CFM. "
        f"**BEM Stock baseline:** **{base['free_cfm']:.1f} CFM** free-air, "
        f"**{base['shutoff_pa']:.1f} Pa** shut-off.",
        "",
        "| Case | Free-air [CFM] | Δ CFM | Shut-off [Pa] | Δ Pa |",
        "|------|----------------|-------|---------------|------|",
    ]
    for label, row in rows:
        lines.append(_fmt_row(label, row, base))

    # Rank non-baseline by free-air gain.
    ranked = sorted(
        ((lab, r) for lab, r in rows if lab != "baseline"),
        key=lambda x: x[1]["free_cfm"],
        reverse=True,
    )
    lines.extend([
        "",
        "## Ranking (highest BEM free-air first)",
        "",
    ])
    for i, (lab, r) in enumerate(ranked[:8], 1):
        lines.append(
            f"{i}. `{lab}` → {r['free_cfm']:.1f} CFM "
            f"({r['free_cfm'] - base['free_cfm']:+.1f} vs baseline)"
        )

    lines.extend([
        "",
        "## Honesty",
        "",
        "- BEM is a **screening** model; grid-converged CFD free-air for Stock is ~48–51 CFM at "
        "tip_gap 0.5 mm (surf3 + tail-mean; Richardson ≈50.8, GCI 6.2% — the earlier ~44.6 was an "
        "under-resolved thin-wall measurement). Use this table only to pick an experimental sibling.",
        "- Do **not** promote a datasheet-tuned recipe to Stock without a trusted STL or Phase 5 "
        "measurement.",
        "",
        f"*Generated by `scripts/a12x25_recipe_sensitivity.py`.*",
        "",
    ])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return {"baseline": base, "ranked": [(lab, r["free_cfm"]) for lab, r in ranked]}


def main() -> int:
    ap = argparse.ArgumentParser(description="A12x25 Stock BEM recipe sensitivity")
    ap.add_argument(
        "--out",
        default="docs/validation/a12x25_recipe_sensitivity.md",
        help="markdown report path",
    )
    args = ap.parse_args()
    summary = run(Path(args.out))
    base = summary["baseline"]
    print(
        f"baseline BEM free-air={base['free_cfm']:.1f} CFM "
        f"shutoff={base['shutoff_pa']:.1f} Pa -> {args.out}"
    )
    for lab, cfm in summary["ranked"][:5]:
        print(f"  top {lab}: {cfm:.1f} CFM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
