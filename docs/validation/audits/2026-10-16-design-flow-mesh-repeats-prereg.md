# Two designs on Stock's five meshes (roadmap 27.3d / 27.3c): pre-registration

Written 2026-10-16, **before** any of these solves. HEAD at writing is master after `2b200d0`. Kimball approved
the plan on 2026-10-16.

## Why

27.3b measured how much Stock's flow card moves on mesh alone. The question that matters is different: when the
card says a design differs from Stock, is the difference larger than the mesh? This campaign runs two real designs
on the **same five meshes** and compares them mesh by mesh with Stock's 27.3b runs.

## Setup (fixed)

Identical to `2026-10-15-stock-flow-mesh-repeats-prereg.md`:
- base cell 5.6 / 5.8 / 6.2 / 6.4 / 6.6 mm (m1–m5);
- spec a12x25, hose "case", 8 procs, 500 iterations, PETG, refine_op False, parallel_mesh True;
- `MeshResolution.for_blade` adaptive surface level, recorded (`surf_max`);
- flow metrics from `load_or_compute_metrics` at `FLOW_REPORT_VERSION` 3.

| design | source | why |
|---|---|---|
| 9604 | `runs/bem_screen_r3_top5/cockpit_assess/design_9604/design.json` | earlier card: push −38 %, the "+24.9 dB louder" noise reading |
| 9610 | `runs/bem_screen_r3_reserve/cockpit_assess/design_9610/design.json` | earlier card: push +7 %, 3 ⚠ |

- Both are stamped **planar** sections (pre-wrap designs), which is how the cockpit assesses them. Both pass
  `validate_blade_params`; hang 0 mm.
- Stock is **not** re-run; its m1–m5 cases are reused.
- Runner: `scripts/design_flow_mesh_repeats.py`, launched as a Windows Scheduled Task at 02:00 that runs
  python.exe directly.
- A failed run is recorded and not retried or replaced; the campaign continues. A design with fewer than 5
  OK runs is INCONCLUSIVE.

## Questions and rules (fixed now)

For each design and mesh i, take the same-mesh difference d_i = design_i − Stock_i:
- relative (design/Stock − 1) for CFM free, CFM load, mean push, each of the 5 bars, and tip ratio;
- absolute for backflow, swirl and dead fractions, and Proudman dB.

**Q1 (resolved?).** A metric is *resolved* for a design if all five d_i have the same sign and
|mean d| > 2 × sd(d).

**Q2 (stable card?).** Judge the design against Stock on the same mesh with today's constants (`21e687e`). A row is
*stable* if its status and better flag are the same on all five meshes.

**Q3 (cross-mesh agreement).** Judge design mesh i against Stock mesh j for all 20 pairs with i ≠ j. Per row, the
share that matches the same-mesh majority. This is what a user sees today, because a design and Stock never share
a mesh.

**Predictions (written now, not tuned):**
- P1: 9604 mean push resolved, weaker.
- P2: 9610 mean push resolved, stronger. Low confidence: +7 % is about twice the mean-push scatter.
- P3: CFM load resolved for both; no sign predicted.
- P4: Proudman dB **not** resolved for either. Noise is mesh-dominated (27.3b).

## Use of the result

Nothing is baked or changed automatically. The results go to Kimball with:
- a proposal for 27.3d: margins for a two-run difference, using Q1–Q3 and grok's round-14 Task F;
- the 15 solved fields as the test set for 27.3c candidates. A noise estimate is useful only if it resolves design
  against Stock (Q1) where Proudman does not.

## Results

(pending)
