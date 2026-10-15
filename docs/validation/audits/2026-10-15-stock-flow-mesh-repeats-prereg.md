# Stock flow-card repeats on varied meshes (roadmap 27.3b): pre-registration

Written 2026-10-15, **before** any of these solves. HEAD at writing is master after `7db7351`.

## Why

The ±3 % / 0.5 dB thresholds (27.3) came from five re-solves of the **same** mesh: free-air spread ~0.1 %,
which is solver noise only. A design-vs-Stock comparison always has a different mesh. On the old setup,
mesh differences alone moved Stock's mean push ~5 % and single bands ~14 % (F2). This campaign measures
mesh-to-mesh scatter on Stock itself.

## Setup (fixed)

Identical to `2026-10-13-stock-flow-repeats-prereg.md`, except the background cell size:

| run | base_cell |
|---|---|
| m1 | 0.0056 m |
| m2 | 0.0058 m |
| m3 | 0.0062 m |
| m4 | 0.0064 m |
| m5 | 0.0066 m |

Everything else is the same: Stock v3 (`stock_blade_flat("a12x25")`), spec a12x25, hose "case", 8 procs, 500 iterations, PETG,
refine_op False, parallel_mesh True.
- The adaptive surface level (`MeshResolution.for_blade`) follows the base cell as it does in Assess. A level
  change at some size is part of the scatter being measured, because designs with different walls get
  different levels too.
- Each run gets a new case directory `runs/stock_flow_mesh_repeats/m{1..5}/`.
- Runner: `scripts/stock_flow_mesh_repeats.py`, launched as a Windows Scheduled Task.
- Flow metrics come from `load_or_compute_metrics` at `FLOW_REPORT_VERSION` 3, on the loaded field.
- n must be 5 OK solves. A failed eval is not replaced; stop and report.

## Rule (fixed now; apply only after n = 5)

1. Apply the same 2σ formula as 27.3 to the five varied-mesh runs: `proposed_tolerances` in
   `scripts/stock_flow_repeats.py`, with the same floors and rounding up.
2. **Never tighten:**
   - new `BAND_TOL` = max(0.03, proposed);
   - new `NOISE_MARGIN_DB` = max(0.5, proposed).
3. If the proposed `BAND_TOL` exceeds **0.15**, or the proposed noise margin exceeds **3.0 dB**, don't bake.
   Report it and ask Kimball: the card would then say "about the same" for almost everything, which is a
   finding about mesh dependence, not a threshold.
4. Report the free and loaded CFM spread as well (mesh dependence of the score itself, information only).

## After baking

Judge m2–m5 against m1 with the new constants. Every mean-push row should read "about as hard", and no noise row
should read ⚠. A failure is recorded, not re-widened.

## Results

(filled in after n = 5)
