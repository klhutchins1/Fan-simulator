# Claude → QA bot, 2026-10-13 (round 10b, alongside Cursor's round 10)

Round 9 was decisive. Kimball adopted the wrap, and it is **merged**. `fansim.bundle` (this folder) is master at
the merge commit **`ae3f1c4`**, plus later docs-only commits. This is the "named merge commit" Cursor's round-10
brief told you to wait for.

**Do Cursor's round-10 Task A first** (`handoff/2026-10-13_to-qa-10/`, the hub-face mark-spec). One correction to
that brief: "current master" is now the **wrapped** Stock v3. The hub is unchanged and the blade roots differ
slightly. Then do the tasks below. Cursor's Task D (Stock CFD repeats) runs on Kimball's Windows box, not yours.

## What landed since round 9 (please verify, don't re-find)

| your finding | what master does now |
|---|---|
| QA-30 (clip shortens chord) | chord realisation measures the **hub-clipped** blade |
| QA-32 (clip-reached camber/stagger) | **Kimball chose a limit plus a correction:** blades may hang at most **2 mm below the hub's motor face, as designed** (`blade.MAX_HANG_BELOW_HUB_MM`, `blade_hang_below_hub_mm`, refused in `validate_blade_params` for wrapped + clipped designs). Under that limit, `chord_realisation.correct_clipped_sections` nudges loft camber/stagger at every station the cut changes (chord > 0.1 mm, camber > 0.001 or stagger > 0.2°) until the cut section reads like the designed one |
| your round-9 hang numbers | you measured the **realised** loft (chord-stretched), about 1.6× the designed hang. The limit uses the **designed** hang: 39/200 of your B population hang, 8/200 exceed 2 mm, worst 7.2 mm (your 13.0) |
| C (surface fit) | parked as a diagnostic. **In the rig, Stock v3 is closer to the real STL in airflow than v2:** 55.7 / 48.0 / 37.5 vs STL 58.3 / 49.5 / 37.1 at 0/5/10 Pa (v2 54.5 / 46.9 / 36.6) |
| W1 / the 6-body Stock | `fuse_impeller` now requires one solid and redoes an all-at-once fuse one blade at a time if it left loose pieces. The repro is the first sharp-edge v3 (2 solids / 6 bodies with the parallel and serial fuse): `tests/data/stock_v3_fuse_fragile.yaml` |
| Stock v3 inner stations (your "maybe estimator bias") | it was the hub cut: Stock hangs about 1 mm and the cut trims the trailing edge at an angle. With the correction they read within 0.005 |
| 27.2 / the radial reader | closed by the wrap. The builder rule keeps the cylinder proof only; on wrapped blades the radial (tangent-plane) cut is the mismatched one |

Old saved designs are stamped `section_wrap="planar"` and rebuild as scored.

## Overview

| # | task | kind | why |
|---|---|---|---|
| (A) | Cursor's round-10 Task A, the hub-face mark-spec | build + measure | first, as briefed |
| B | **Wrap confirmation on merged master** (W1–W6, n ≈ 40) | build-only, long | the builder changed again after round 9 (caps, correction, fuse net) |
| C | **Hang limit and correction, independently** | build-only, medium | confirms QA-32 is closed, and that the limit refuses the right designs |
| D | Fuse guard re-measure | short builds | **wait** for Cursor's 27.1 patch; skip if it isn't in a bundle |
| E | (optional) Near-stall flag | analysis | carried over |

Pre-register (A), B and C in **one** commit before any B/C data.

## Task B: wrap confirmation (Cursor's round-10 B, with one addition)

- 40 designs, not 150: notches, winglets, tip-round, shroud, featured, near-bounds and uneven spacing, at least
  4 of each. Build them with the options set on random bases if the population lacks them, and say so.
- W1–W5 as in round 9: sound, volume within 5 % of planar, time ≤ 2× planar, cup K7, direction 0 wrong.
- **New W6: no design the limit allows produces a broken fuse.** Every wrapped P build is one solid
  (`len(Solids()) == 1`) and watertight. Log how often the one-blade-at-a-time fallback fired. `fuse_impeller`
  doesn't report it, so time it, or wrap `fuse_many` in your hook.
- Designs the hang limit refuses count as "refused (hang)", not as W1 failures. Report how many.
- One P build at a time, memory gates, monotonic clock. S5_0167's OOM is a known W1 miss: log it, don't debug
  it.

## Task C: hang limit and correction

1. Run `blade_hang_below_hub_mm` (designed) on your whole round-9 B population (200) plus 200 fresh stress
   designs. Report the distribution and the refused share, and compare it with your realised-loft numbers.
2. For **every allowed design that hangs at all** (expect about 30–40 of the 400), build it and run your
   round-8/9 built-vs-sliders measurement at all stations.
   - **Pre-register the rule:** at every readable station, chord within 3 %, camber within 0.005 and stagger
     within 1.5° of the same section read analytically. **Use the design's own section family for the bias.**
     Your round-9 note subtracted the NACA bias from plate (Stock) sections; use the family the design uses.
3. Check that the refusal message is plain and that the optimizer treats it as infeasible: call
   `objectives.evaluate_candidate` on two refused designs with CFD stubbed, as in
   `tests/test_objectives_orientation.py`.
4. Report anything the limit gets wrong: a refused design that doesn't really hang (for example, its lowest
   point is on the hub-embedded root), or an allowed one that's distorted.

## Task D: wait

Cursor's 27.1 patch (the guard on remaining growth plus a shroud term) isn't merged yet. When a bundle has it,
re-run your round-8/9 hook on 12 shrouded + 4 open designs. Pass = remaining growth covered on all 16.

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**` and a new `handoff/2026-10-13_from-qa-10b/` (or a combined
  `_from-qa-10/` with both A and B/C; say which in the README).
- Pre-register before data, then commit and hash it.
- Patches are proposals only; no fansim source edits.
- No outside STLs.
- Big data stays gzipped (gitignored); `git add -f` small ones you want committed.
- If the box suspends, stop and mark FINAL.
- Status line per task in the README.
