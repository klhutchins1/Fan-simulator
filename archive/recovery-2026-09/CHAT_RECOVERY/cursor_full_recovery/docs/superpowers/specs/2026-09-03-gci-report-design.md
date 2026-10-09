# Roache GCI on the grid-convergence script (stage 2)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Wire the existing `grid_convergence_index` helper into `scripts/run_grid_convergence.py` via a testable `gci_report(rows)` that needs no Docker. Keep pairwise % change as a human line. Do **not** turn on `addLayers`, do **not** run a 3-mesh campaign, do **not** change screening `base_cell`.  
**Roadmap:** §1.5 stage 2. The Roache math already lives in `fansim/analyze/grid_convergence.py` and `tests/test_grid_convergence.py`. The script still eyeballs “finest step < 2%”.

## Plain language

A grid study that only prints “CFM moved 3%” is not a GCI. Roache’s index is already implemented: observed order *p*, Richardson *f(h→0)*, and a % band on the fine mesh. Stage 2 is to compute that from the three (or more) `base_cell` solves the script already runs, print it, and stamp it on `gridconv.json`. Layers and a new Docker campaign stay later.

## Problem

```text
scripts/run_grid_convergence.py
  → pairwise % change
  → GRID-INDEPENDENT if last step < 2%

fansim/analyze/grid_convergence.py
  → grid_convergence_index(...)   # tested, unused by the script
```

The 2% pairwise cutoff is not Roache. Unequal refinement (default `0.007,0.005,0.0035`) is exactly what the helper’s *q(p)* iteration is for.

## Goal

1. **Helper** (no Trame, no Docker, no OpenFOAM):

```text
gci_report(rows, *, h_key="base_cell", f_key="cfm_free") -> dict | None
```

- `rows` is the list the script already builds (`base_cell`, `cfm_free`, …).
- Fewer than 3 rows → `None`.
- Sort by `h_key` ascending (fine → coarse). If more than 3 meshes, use the **three finest**.
- Call `grid_convergence_index(h1,h2,h3,f1,f2,f3)` with that order.
- Success → `asdict(GCIResult)` plus `"quantity": f_key`.
- `ValueError` (flat / non-monotone / bad *h*) → `{"quantity": f_key, "error": str(e)}`. Do not crash the script.

Live in `fansim/analyze/grid_convergence.py` next to the existing function.

2. **Script** after the mesh loop:

- Keep the pairwise % print.
- Replace the “finest step < 2% => GRID-INDEPENDENT” verdict with the GCI line: *p*, *f(h→0)*, `GCI_fine` %, asymptotic yes/no (or the error string).
- `gridconv.json` becomes `{"meshes": rows, "gci": <report or null>}`. Nothing in-repo reads the old list-only file.

3. **Quantity** is `cfm_free` only. Do not GCI `eta_total` / Δp₀ this cycle.

## Tests (no Docker)

- Three-mesh A12x25 numbers already in `test_real_fan_grid_study` (h=3,4,6 mm, f=59.6,57.7,56.8) via `gci_report` → same *p* / extrapolated / `gci_fine_pct` band, `quantity == "cfm_free"`.
- Two rows → `None`.
- Flat CFM → dict with `"error"`, no raise.
- Four rows → uses the three **smallest** `base_cell` values.

Do not add a `@pytest.mark.docker` campaign.

## Non-goals

- snappy `addLayers` / y+ / prism layers
- Changing default `--cells` or screening `MeshResolution`
- Full P–Q / shut-off
- Cockpit UI
- Replacing NSGA objectives
- Running the study as part of this slice
