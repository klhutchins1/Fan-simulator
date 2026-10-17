# Too close to call (roadmap R0.3 / 27.3d) — pre-registration

Written 2026-10-17 on branch `too-close-r03`, **before** baking constants. No CFD.
Uses the existing v4 `flow_report.json` on Stock's five meshes (`runs/stock_flow_mesh_repeats/m1`–`m5`).

## Rule (fixed now)

A compared row whose design-vs-Stock difference sits inside the **two-run mesh scatter** is
`too close to call` (status `na`, icon `–`), not ✓ or ⚠.

Two-run scatter on each metric is `√2 × 2σ` of Stock on those five v4 meshes (sample σ, n−1).
Round **up** to display precision (`ceil_2dp` for fractions, same helper as 27.3).

Never tighten an already-baked "don't warn" region:

```
CLOSE = max(existing_margin, ceil(√2 × 2σ))
```

| row | existing margin | 2σ on v4 Stock meshes | CLOSE |
|---|---|---|---|
| push (mean, relative) | `BAND_TOL` 0.06 | 5.65 % | **0.08** |
| direction (backflow, abs) | 0.02 | 0.0082 | **0.02** |
| spin (swirl, relative) | 0.10 | 3.98 % | **0.10** |
| dead air (abs) | 0.02 | 0.0071 | **0.02** |
| weak tips (relative) | 0.10 | 9.94 % | **0.15** |

Bars stay a picture (`BAR_TOL` 0.12). Noise hint stays Expert-only (`HINT_MARGIN_DB` 0.5).
Simple overall line ignores `na` / Expert-only rows (already).

## Pass checks (no CFD)

- C1: one synthetic case per compared row: inside CLOSE → `na` + "Too close to call"; just outside → ✓ or ⚠ as today.
- C2: Stock vs itself is too close on every compared row.
- C3: on the 27.3d cases (9604 and 9610 vs Stock, m1–m5, v4 json), no row flips verdict across the five meshes.

## Results

- **C1 PASS** (synthetics in `tests/test_flow_verdicts.py`).
- **C2 PASS**.
- **C3 FAIL** (recorded, not re-tuned). Same-mesh design-vs-Stock still flips where the delta straddles CLOSE:
  - 9604 direction: backflow Δ −0.036…+0.013 (na / ok)
  - 9610 direction: +0.016…+0.078 (na / warn)
  - 9610 push: −0.039…+0.082 vs CLOSE 0.08 (na / ok)
  - 9610 spin: +0.097…+0.275 vs CLOSE 0.10 (na / warn)
  9604 push/spin and both dead rows are stable.

√2 × Stock's own 2σ does not cover the mesh-to-mesh scatter of a *design-minus-Stock* pair. Widening CLOSE to the max |Δ| of those pairs would swallow 9610's push and 9604's direction; it would also hide 9610's real backflow (+0.05 to +0.08). That choice is Kimball's.
