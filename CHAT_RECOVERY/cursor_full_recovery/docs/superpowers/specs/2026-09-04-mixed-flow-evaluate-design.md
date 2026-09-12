# Mixed-flow `evaluate_candidate` path (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Add **`evaluate_mixed_flow(MixedFlowParams, workdir, …)`** that exports the mixed-flow STL and runs the **same axial MRF free + load CFD** path as axial `evaluate_candidate`, plus a CLI `scripts/evaluate_mixed_flow.py`. Not cockpit, not NSGA search, not mixed-flow BEM, not a volute.  
**Roadmap:** §4.1 remaining (`evaluate_candidate`).

## Plain language

We can already build a mixed-flow STL. Scoring it still means hand-running `validate_stl.py`. Stage 1 gives one function and one script that do the honest drop-in score in the existing through-flow duct — free CFM, load CFM, efficiency — so a high-Pa campaign can start without inventing a radial domain.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **1 (chosen)** | Separate `evaluate_mixed_flow` + shared CFD helpers | Clean; no BladeParams fake |
| **2** | Force MixedFlow → BladeParams adapter | Lies about hub/stations; breaks gates |
| **3** | Full NSGA archetype.evaluate | Out of scope (user picked A) |

## Goal

### 1. Shared CFD core (minimal extract)

Factor the post-STL part of `evaluate_candidate` (rig, frame/stator optional **off** for mixed-flow stage 1, free+load solves, metrics packing) into something like:

```text
_score_impeller_stl(stl, workdir, *, tip_radius_mm, spec, load_pa, ...) -> ObjectiveResult
```

Or duplicate the CFD block once in `evaluate_mixed_flow` if extract is messy — prefer a small private helper to avoid drift. Mixed-flow stage 1: **no stator**, **circular duct on**, default tip gap floor 0.5 mm vs `2*r_tip` leftover to frame ID.

### 2. `evaluate_mixed_flow` (`fansim/optimize/objectives.py` or `fansim/centrifugal/evaluate.py`)

```text
evaluate_mixed_flow(params: MixedFlowParams, workdir, *,
    load_pa=1.0, tip_gap_mm=0.5, refine_op=False, print_penalty=True, ...) -> ObjectiveResult
```

Gates (cheap, no CFD):

- Params already validate mount / cone in `__post_init__`.
- Tip leftover: `casing_id/2 - r_tip_mm >= tip_gap_mm` (use loft tip radius helper if export grows the tip).
- Skip: axial printability/solidity floors, flutter, BEM prescreen, catalog surrogate (those are `BladeParams`-shaped).

Geometry: `export_mixed_flow_stl` → `impeller.stl`.  
CFD: same `build_case` + free/load (and optional `--refine-op`) as axial.  
Stamp `raw["archetype"] = "centrifugal"`, `raw["topology"] = "mixed_flow"`.

### 3. Archetype

`MixedFlowArchetype.evaluate(...)` calls `evaluate_mixed_flow` (no longer `NotImplementedError`).

### 4. CLI

`scripts/evaluate_mixed_flow.py`:

```text
uv run python scripts/evaluate_mixed_flow.py [--out-dir DIR] [--load-pa PA] [--iters N]
```

Uses default `MixedFlowParams()`, prints the same metric summary style as other eval scripts (cfm_free, cfm_load, efficiency). No `★`. Requires Docker OpenFOAM like axial eval.

### 5. Docs

- Spec accepted; roadmap §4.1: evaluate path done; remaining cockpit / BEM / volute / campaign.
- Honesty: axial MRF duct is still an approximate domain for mixed-flow.

## Honesty

- Not a centrifugal volute case. High-Pa claims need a campaign, not this wiring alone.
- Skipped axial structural/BEM gates — mixed-flow stress/printability stay later.
- Do not switch default NSGA to mixed-flow.

## Tests (no Docker for unit tests)

- Tip-gap infeasible when `r_tip_mm` too large (monkeypatch / tiny floor).
- `MixedFlowArchetype.evaluate` is no longer `NotImplementedError` (monkeypatch CFD/score to a fake result).
- CLI help mentions evaluate mixed-flow; no `★`.
- Existing mixed-flow geometry tests stay green.

Optional (manual / docker): one default mixed-flow through the CLI when the image is up.

## Non-goals

- Cockpit UI
- NSGA `--archetype centrifugal` study driver
- Mixed-flow BEM
- Volute / 90° radial
- Stator + mixed-flow
- Changing axial `evaluate_candidate` defaults

## Success

`evaluate_mixed_flow(MixedFlowParams(), workdir)` (with CFD mocked in tests) returns a feasible-shaped `ObjectiveResult`; with Docker, the CLI scores default mixed-flow in the A12x25 duct.
