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

**n = 10/10 OK, 2026-10-17 02:00–06:29.** All runs at surface level 4. Task result 0.

| design | mesh | CFM free / load | mean push Pa | Proudman dB |
|---|---|---|---|---|
| 9604 | m1–m5 | 58.1–59.5 / 48.0–49.5 | 7.99–9.07 | −26.2 … +8.5 |
| 9610 | m1–m5 | 56.5–57.0 / 39.8–40.8 | 12.99–13.99 | −16.4 … −15.0 |

**Q1: same-mesh differences against Stock** (mean ± sd over the five meshes; R = resolved)

| metric | 9604 | 9610 |
|---|---|---|
| CFM free | +10.7 % ± 1.7 **R** | +6.8 % ± 0.9 **R** |
| CFM load | +12.8 % ± 2.2 **R** | −7.2 % ± 0.6 **R** |
| mean push | −32.8 % ± 2.9 **R** | +6.7 % ± 4.3 (all positive, but m5 +0.3 %) |
| backflow | +0.017 ± 0.012 | +0.060 ± 0.018 **R** |
| swirl | −0.256 ± 0.010 **R** | +0.070 ± 0.011 **R** |
| dead | −0.002 ± 0.005 | +0.048 ± 0.004 **R** |
| tip ratio | +3.7 % ± 5.1 | −75 % ± 8 **R** |
| Proudman | −15.5 ± 15.1 dB | −24.1 ± 16.8 dB |
| bars hub→tip | all 5 **R**, −13 to −63 % | 4 of 5 **R** (bar 1 +8 % ± 4 not) |

Predictions:
- **P1 PASS:** 9604 push weaker.
- **P2 FAIL:** 9610 push is not resolved.
- **P3 PASS:** CFM load is resolved for both.
- **P4 PASS:** noise is resolved for neither.

**Q2 / Q3: card stability**

| row | 9604 same-mesh | 9604 cross-mesh | 9610 same-mesh | 9610 cross-mesh |
|---|---|---|---|---|
| direction | flips (2/5 ⚠) | 65 % | stable ⚠ | 100 % |
| push | stable ⚠ | 100 % | flips (m5 "about as hard") | 85 % |
| spin | stable ✓+ | 100 % | flips (4/5 ⚠) | 70 % |
| dead | stable ✓ | 100 % | stable ⚠ | 100 % |
| noise | not judged | – | not judged | – |

**What this shows**
1. **The card is reliable where the true difference is large.** It flips exactly where the same-mesh difference sits
   on a margin:
   - 9604 backflow: +0.017 against a margin of +0.02;
   - 9610 swirl: +0.070 against a limit of about +0.06;
   - 9610 push: +6.7 % against a margin of +3 %, with 4 % of mesh scatter.

   Widening the margins only moves the line. What the card lacks is a "too close to call" state (27.3d).
2. **Noise:** design-vs-Stock Proudman has an sd of 15–17 dB. 9610's own Proudman is steady (±0.7 dB), while Stock's
   and 9604's swing about 35 dB, so the instability depends on the design (cause unknown: 9604 is planar, Stock is wrapped).
   This set is now the 27.3c test set.
3. **New finding: the push row disagrees with the score for 9604.** This is mesh-robust: its push is 33 % *less*
   than Stock's on every mesh, yet it moves 13 % *more* air under load. The card's ⚠ "pushes less" on a fan that
   delivers more is misleading, which is the 2026-10-10 follow-up, now confirmed as not mesh. Roadmap 27.3e.

Nothing baked. For Kimball.

