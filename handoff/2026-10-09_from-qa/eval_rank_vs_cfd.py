"""Rule (c) of notes/axial-force-retune-criteria.md (pre-registered 2026-10-09): does the BEM rank
CFD-scored designs the same way CFD does?

Usage (from a checkout with axial-force-pressure.diff applied, project venv):
    uv run python /workspace/fansim/research/proto/eval_rank_vs_cfd.py designs.csv [--out result.json]

CSV columns (header required):
    design_id     any label, e.g. stock_v2, opt_run1_t9012
    geometry      path to a .flat.json (blade_from_flat), a .yaml blade/problem file (load_blade_params),
                  or the word "stock" for config/problems/a12x25_reference.yaml
      OR flat     the cockpit/Optuna flat dict as an inline JSON string (blade_from_flat)
      OR flat-param columns: n_blades, stagger_root, ..., tip_radius, chord_basis (bare or "flat."-prefixed)
    Stock MUST be geometry=stock (the 7-station YAML); a flat dict truncates it to 3 stations (QA bug #1).
    cfd_free_cfm  CFD free-air CFM (the Audit #4 metric; higher = better)
optional:
    rpm           default 2000
    tip_gap_mm    default: the model's default (0.5 mm open tip, 0 for a full shroud)

--cfd-col NAME picks another CFD column (e.g. a scored or load-point CFM) for a SECONDARY report;
the pre-registered verdict always uses cfd_free_cfm (raw free-air CFM, the Audit #4 metric).

PASS rule (pre-registered): n >= 5 AND rho_new >= 0.6 AND rho_new >= rho_base - 0.10;
alternative PASS if 0.5 <= rho_new < 0.6 and top-3 overlap >= 2 (and the rho_base condition); n < 5 -> INCONCLUSIVE.
"""
from __future__ import annotations
import argparse, csv, json, os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
from scipy.stats import spearmanr
from fansim import fan_bem as FB
from fansim.geometry.config import load_blade_params
from fansim.optimize.search_space import blade_from_flat


_STR_KEYS = {"chord_basis", "thick_mode", "section_family"}


def load_row_geom(r: dict):
    g = (r.get("geometry") or "").strip()
    if g.lower() == "stock":             # always the 7-station YAML (a flat dict would cut it to 3 stations)
        return load_geom(g)
    if (r.get("flat") or "").strip():
        return blade_from_flat(json.loads(r["flat"]))
    if g:
        return load_geom(g)
    # flat params as separate columns (bare keys like n_blades, stagger_mid, ... or prefixed "flat.")
    flat = {}
    for k, v in r.items():
        key = k[5:] if k.startswith("flat.") else k
        if v in (None, "") or key in ("design_id", "geometry", "flat", "rpm", "tip_gap_mm") or key.startswith("cfd"):
            continue
        if key in _STR_KEYS:
            flat[key] = v
        elif key == "n_blades":
            flat[key] = int(float(v))
        else:
            try:
                flat[key] = float(v)
            except ValueError:
                continue
    if "n_blades" not in flat:
        sys.exit(f"row {r.get('design_id')}: no geometry, flat, or flat-param columns")
    return blade_from_flat(flat)


def load_geom(g: str):
    if g.strip().lower() == "stock":
        return load_blade_params("config/problems/a12x25_reference.yaml")
    p = Path(g).expanduser()
    if p.suffix == ".json":
        return blade_from_flat(json.loads(p.read_text()))
    return load_blade_params(str(p))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("csv"); ap.add_argument("--out")
    ap.add_argument("--cfd-col", default="cfd_free_cfm")
    a = ap.parse_args()
    if "axial_force" not in getattr(FB, "PRESSURE_MODELS", ()):
        sys.exit("fan_bem has no axial_force mode: apply patches/axial-force-pressure.diff first")
    rows = list(csv.DictReader(open(a.csv, newline="")))
    cols = set(rows[0]) if rows else set()
    if not rows or not {"design_id", a.cfd_col, "cfd_free_cfm"} <= cols or not ({"geometry", "flat", "n_blades", "flat.n_blades"} & cols):
        sys.exit("CSV needs design_id, cfd_free_cfm, and geometry / flat / flat-param columns (optional rpm, tip_gap_mm)")
    ids, cfd, base, new, sec = [], [], [], [], []
    for r in rows:
        p = load_row_geom(r); rpm = float(r.get("rpm") or 2000.0)
        gap = float(r["tip_gap_mm"]) if r.get("tip_gap_mm") not in (None, "") else None
        ids.append(r["design_id"]); cfd.append(float(r["cfd_free_cfm"])); sec.append(float(r[a.cfd_col]))
        base.append(FB.pq_curve(p, rpm, tip_gap_mm=gap).free_delivery_cfm)
        new.append(FB.pq_curve(p, rpm, tip_gap_mm=gap, pressure_model="axial_force").free_delivery_cfm)
    n = len(ids)
    rb = float(spearmanr(base, cfd).correlation) if n >= 3 else float("nan")
    rn = float(spearmanr(new, cfd).correlation) if n >= 3 else float("nan")
    top = lambda v: {ids[i] for i in sorted(range(n), key=lambda i: -v[i])[:3]}
    ov_new, ov_base = len(top(new) & top(cfd)), len(top(base) & top(cfd))
    if n < 5:
        verdict = "INCONCLUSIVE (n < 5)"
    elif rn >= rb - 0.10 and (rn >= 0.6 or (rn >= 0.5 and ov_new >= 2)):
        verdict = "PASS"
    else:
        verdict = "FAIL"
    res = dict(n=n, rho_base=rb, rho_new=rn, top3_overlap_new=ov_new, top3_overlap_base=ov_base, verdict=verdict,
               rows=[dict(design_id=i, cfd=c, bem_base=b, bem_new=x) for i, c, b, x in zip(ids, cfd, base, new)])
    for r in res["rows"]:
        print(f"{r['design_id']:24s} CFD {r['cfd']:6.1f}  BEM euler {r['bem_base']:6.1f}  BEM axial {r['bem_new']:6.1f}")
    print(f"n={n} rho_base={rb:.3f} rho_new={rn:.3f} top3 overlap new/base={ov_new}/{ov_base} -> RULE (c) {verdict}")
    if a.cfd_col != "cfd_free_cfm" and n >= 3:
        print(f"secondary ({a.cfd_col}, not the verdict): rho_base={spearmanr(base, sec).correlation:.3f} "
              f"rho_new={spearmanr(new, sec).correlation:.3f}")
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
