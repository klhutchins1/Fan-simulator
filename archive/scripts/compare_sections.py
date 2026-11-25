"""Blade-section comparison CLI: Stock recipe (built) vs the close-reference STL.

  uv run python scripts/compare_sections.py --params config/problems/a12x25_reference.yaml \
      --ref validation/reference/a12x25_impeller.stl
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.validation.section_compare import compare

COLS = [("n_blades", "N", "{:.0f}"), ("chord_mm", "chord mm", "{:.1f}"),
        ("stagger_deg", "stagger deg", "{:.1f}"), ("camber_ratio", "camber/c", "{:.3f}"),
        ("camber_pos", "camber pos", "{:.2f}"), ("max_thickness_mm", "t max mm", "{:.2f}"),
        ("thickness_ratio", "t/c", "{:.3f}"), ("axial_extent_mm", "axial mm", "{:.1f}"),
        ("le_theta_deg", "LE theta deg", "{:.1f}"), ("le_z_mm", "LE z mm", "{:.1f}"),
        ("solidity", "solidity", "{:.2f}")]


def _table(rows, title):
    head = "| r/R | " + " | ".join(c[1] for c in COLS) + " |"
    sep = "|" + "---|" * (len(COLS) + 1)
    lines = [f"### {title}", "", head, sep]
    for r in rows:
        cells = [c[2].format(r[c[0]]) if c[0] in r else "-" for c in COLS]
        lines.append(f"| {r['r_frac']:.2f} | " + " | ".join(cells) + " |")
    return lines + [""]


def recipe_at(params, radii_mm):
    from fansim.geometry.blade import _interp_stations
    it = _interp_stations(params, 400)
    r0 = params.hub_radius - params.root_embed
    rf = (np.asarray(radii_mm) - r0) / (params.tip_radius - r0)
    return [{k: float(np.interp(f, it["r_frac"], it[k])) for k in
             ("chord", "stagger_deg", "thickness", "max_camber", "camber_pos", "sweep", "skew",
              "lean_deg")} | {"span_frac": float(f)} for f in rf]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", help="recipe yaml; the Stock STL is built from it")
    ap.add_argument("--stock-stl", help="use an existing Stock STL instead of building")
    ap.add_argument("--ref", default=str(ROOT / "validation/reference/a12x25_impeller.stl"))
    ap.add_argument("--out", default=str(ROOT / "docs/validation/recipe_fidelity"))
    ap.add_argument("--suffix", default=None,
                    help="output stem suffix (default: '_v2' when --params ends in _v2.yaml)")
    a = ap.parse_args()
    tmp = tempfile.TemporaryDirectory()
    params = None
    stock = a.stock_stl
    if a.params:
        from fansim.geometry import build_impeller, export_stl
        from fansim.geometry.config import load_blade_params
        params = load_blade_params(a.params)
        if not stock:
            stock = str(Path(tmp.name) / "stock_impeller.stl")
            export_stl(build_impeller(params), stock)
    if not stock:
        ap.error("need --params or --stock-stl")
    res = compare(stock, a.ref, labels=("stock", "reference"))
    if params is not None:
        res["recipe"] = recipe_at(params, [r["r_mm"] for r in res["stock"]])
        res["recipe_stations"] = [dict(r_frac=s.r_frac, chord=s.chord, stagger_deg=s.stagger_deg,
                                       max_camber=s.max_camber, camber_pos=s.camber_pos,
                                       thickness=s.thickness, sweep=s.sweep, skew=s.skew,
                                       lean_deg=s.lean_deg) for s in params.stations]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    suffix = a.suffix if a.suffix is not None else (
        "_v2" if a.params and Path(a.params).stem.endswith("_v2") else "")
    stem = f"section_compare{suffix}"
    (out / f"{stem}.json").write_text(json.dumps(res, indent=2))
    md = ["# Blade-section comparison: Stock recipe vs close-reference STL", "",
          "Cylinder cuts at r = frac x tip, unrolled to (s = r*theta, z); median over blades. "
          "Stagger is measured from the circumferential (s) direction (0 = in the rotation plane, "
          "90 = axial). camber/c = max midline deviation from the chord line over chord; "
          "camber pos from the LE. LE theta is modulo blade pitch (phase is arbitrary); "
          "compare its change with radius, not its value.", ""]
    md += _table(res["stock"], "Stock (built from recipe)")
    md += _table(res["reference"], "Reference STL")
    md += ["### Difference (stock - reference)", ""]
    dc = [c for c in COLS if c[0] != "n_blades"]
    md += ["| r/R | " + " | ".join(c[1] for c in dc) + " |", "|" + "---|" * (len(dc) + 1)]
    for d in res["diff"]:
        md.append(f"| {d['r_frac']:.2f} | " + " | ".join(
            (f"{d[c[0]]:+.3g}" if c[0] in d else "-") for c in dc) + " |")
    md.append("")
    if params is not None:
        md += ["### Recipe (interpolated at the measured radii) vs built Stock", "",
               "Convention (fansim/geometry/blade.py `_section_loop`): stagger is measured from the "
               "circumferential (tangent-plane) direction; chord coordinate `a` maps to "
               "t = a cos(stagger), axial = a sin(stagger), so recipe chord is the true chord "
               "length. `thickness` and `max_camber` are fractions of chord (plate family: "
               "constant thickness t*c, NACA meanline camber bowing the plate). Sections are "
               "planar in the tangent plane, not wrapped on the cylinder.", "",
               "| r/R | chord recipe | chord built | stagger recipe | stagger built | "
               "camber recipe | camber built | camber pos recipe | built | t/c recipe | "
               "t/c built |", "|" + "---|" * 11]
        for rc, st in zip(res["recipe"], res["stock"]):
            md.append(f"| {st['r_frac']:.2f} | {rc['chord']:.1f} | {st['chord_mm']:.1f} | "
                      f"{rc['stagger_deg']:.1f} | {st['stagger_deg']:.1f} | "
                      f"{rc['max_camber']:.3f} | {st['camber_ratio']:.3f} | "
                      f"{rc['camber_pos']:.2f} | {st['camber_pos']:.2f} | "
                      f"{rc['thickness']:.3f} | {st['thickness_ratio']:.3f} |")
        md += ["", "Recipe stations: `r_frac, chord, stagger_deg, max_camber, camber_pos, "
               "thickness, sweep, skew, lean_deg`", ""]
        for s in res["recipe_stations"]:
            md.append("- " + ", ".join(f"{k}={v}" for k, v in s.items()))
        md.append("")
    (out / f"{stem}.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
