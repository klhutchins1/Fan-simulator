"""What actually helps? — rank which design knobs drive airflow / efficiency / noise, from the data
you already have. No new CFD: it reads every design in the catalog and correlates each geometry
parameter against each objective, so you can see the levers at a glance.

    uv run python scripts/catalog.py build     # make sure the catalog is current, then:
    uv run python scripts/what_helps.py

Correlation is Spearman (rank-based, robust to nonlinearity). Read it as "across the designs the
optimizer has actually explored, raising this knob tends to raise (+) or lower (-) that objective."
It's observational, not causal, and mixes runs with different setups — a strong, consistent sign is a
real lever; a weak one is noise. This is the same signal the optimizer exploits, made legible.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fansim.catalog import load_catalog  # noqa: E402

# geometry knobs worth ranking (as stored in each design's params)
PARAMS = ["n_blades", "stagger_root", "stagger_mid", "stagger_tip", "chord_root", "chord_mid",
          "chord_tip", "sweep_mid", "sweep_tip", "lean_mid", "lean_tip", "max_camber", "hub_radius",
          "tip_radius", "camber_pos"]
# objective -> (catalog attr, "higher is better?")
OBJECTIVES = [("airflow (free)", "cfm_free", True), ("airflow (load)", "cfm_load", True),
              ("efficiency", "efficiency", True), ("noise", "noise", False)]


def _spearman(x, y) -> float | None:
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 8:
        return None
    a, b = zip(*pairs)
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    if np.std(ra) == 0 or np.std(rb) == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> int:
    designs = [e for e in load_catalog() if e.params]
    if len(designs) < 8:
        print("Not enough designs in the catalog. Run `catalog build` (and some optimizations) first.")
        return 1
    print(f"WHAT HELPS — Spearman correlation across {len(designs)} designs in the catalog.")
    print("(+ = raising this knob raises the objective; the sign that matters is a strong, consistent one.)\n")

    for label, attr, higher_better in OBJECTIVES:
        ys = [getattr(e, attr) for e in designs]
        rows = []
        for p in PARAMS:
            r = _spearman([e.params.get(p) for e in designs], ys)
            if r is not None:
                rows.append((p, r))
        if not rows:
            continue
        rows.sort(key=lambda t: -abs(t[1]))
        aim = "higher" if higher_better else "lower"
        print(f"● {label}  (want it {aim})")
        for p, r in rows[:6]:
            bar = ("+" if r > 0 else "-") * max(1, round(abs(r) * 12))
            helps = ("helps" if (r > 0) == higher_better else "hurts") if abs(r) > 0.2 else "weak"
            print(f"    {p:12s} {r:+.2f}  {bar:<13s} {helps}")
        print()

    print("Takeaway: the biggest consistent lever is usually mid-span stagger (win-win on flow + eff),")
    print("while high camber tends to hurt both — which is exactly what the --guided search space encodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
