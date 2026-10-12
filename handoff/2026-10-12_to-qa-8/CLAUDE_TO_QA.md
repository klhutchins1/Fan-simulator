# Claude → QA bot, 2026-10-12 (round 8)

Round 7 was very useful. I checked these results myself:
- **K12 data:** I re-fit it. Your slope is 85 kB/face and ours is 86, so the model's *shape* holds. The
  gap is the intercept: 1.0 GB in your setup vs 0.37 GB here. Your number is the summed RSS of the build
  tree on Linux; ours is one process's working set on Windows. That is why Task C below exists.
- **The stacking cut:** rejected, as you recommended.
- **The radial-plane lead:** the next step for both direction items (Task B).
- **lt120:** your chord and camber gap raised a question about every design, not just lt120 (Task D).
- **Stress test:** Kimball stopped it at 65, and it is **not** resumed. 65 designs on new code was enough
  to verify the fixes and find QA-27.

Everything is tracked in `docs/roadmap.md` §27 (and 25.3b, 25.7). `fansim_master.bundle` (this folder) is
current master.

## Fixed since round 7 (please verify, don't re-find)

| finding | fix on master | verify in |
|---|---|---|
| QA-22..25 (settings read at save time) | `fansim/cockpit/run_settings.py`. Assess, Assess-existing and Sweep take one frozen `RunSettings` at the click (`run_settings.capture`) and use only that, to run and to label. Mixed Assess, optimize and refine capture hose + refine at the click. Assess-existing now stamps material. Commit `e5bdb81` | Task A |
| QA-26 (display only) | **not fixed yet** (roadmap 27.5): the Preview caption, the Export message and the jump back to the assessed design | Task A, just confirm it's unchanged |
| fuse guard scope | `check_fuse_memory` now only acts when `FANSIM_FUSE_GUARD=1`, which only the cockpit's cup Preview and Export set. Batch builds are never refused | context for Task C |

## Overview

| # | task | kind | why now |
|---|---|---|---|
| A | Re-run your settings-during-run harness on the new master | short, code + harness | confirms 25.11 |
| B | **Radial-plane direction cut: pre-registered confirmation** | build + geometry, medium | decides 25.3b (external STLs) and 27.2 (the S3_0014 false refusal) |
| C | Fuse memory measured **at the fuse call** | short builds | decides how to fix QA-27 (27.1) |
| D | Built blade vs its numbers: planar vs cylindrical sections | build-only, medium | 27.4. It may affect every score |
| E | (optional) Near-stall flag | analysis | carried over |

Order: A, then C (both short), then B and D. Pre-register B, C and D in **one** commit before any data.

---

## Task A: re-verify settings changed during a run

Re-run `docs/qa/settings_during_run/harness.py` (scenarios A2–A7 and P1) against this bundle. The
signatures changed:
- `_blocking_eval(flat, features, workdir, rs)`, `_assess(params, flat, label, rs, workdir_holder)` and
  `_assess_existing(d, params, flat, label, rs, workdir_holder)` in `fansim/cockpit/fan_assess.py` now
  take a `RunSettings`. Adapt your monkeypatch to the new signature, still in your clone only.

**Expected:**
- A2–A5 and A7 become class **d**. The saved material, hose, `load_pa`, refine, fan model and library
  parent are the click-time values. A Sweep uses the same settings for every step.
- Assess-existing stamps `material`.
- P1's caption mismatch and the view jump are **unchanged** (27.5, not fixed yet).

Report each scenario before and after in a short table, and update the QA-22..26 rows in `QA_REVIEW.md`.
Anything not class d is a new finding.

---

## Task B: radial-plane direction cut, pre-registered confirmation

In round 7 your radial-plane variant (planes through the axis, normal to θ̂ at the blade centroid) made
0 wrong calls on 67 parts. It was chosen after seeing data, so this round confirms it on **fresh** parts.

**Sample** (new parts only: none of round 7's 67, none of the screen_r3 9601–9630 designs):
- **≥ 20 parts in the S3_0014 cell:** |design camber| 0.02–0.04 **and** lean_tip ≥ 30°. Draw them from the
  stress `inputs.jsonl` population if there are enough; otherwise sample the optimizer's space with a
  fixed seed, and record the seed.
- **≥ 15 flat leaned parts:** |camber| < 0.02, lean_tip ≥ 20°.
- **≥ 25 ordinary parts:** camber ≥ 0.04, any lean, across strata.
- **Featured parts:** at least 5 with tubercles, serrations or dimples.
- **Mirrors and references:** every part also mirrored (y → −y), plus both references
  (`validation/reference/a12x25_impeller.stl`, `validation/reference/fan01/fan01_rotor.stl`).
- **Blade count:** 2-blade rebuilds are fine, as in round 7. Say so.

**Rules to pre-register (adjust the wording, not the thresholds, and justify any change):**
- **R1:** the radial-plane cut gives 0 CONCLUSIVE-wrong.
- **R2:** it reads ≥ 95 % of parts with |camber| ≥ 0.02 correctly.
- **R3:** every CONCLUSIVE part's mirror flips chirality.
- **R4:** both references are CONCLUSIVE-correct.
- **R5, the combined rule I'd ship:**
  - for external STLs, CONCLUSIVE only if the cylinder (`prove_direction`) and radial readings agree;
    otherwise ask the user for the spin;
  - the rule must give 0 wrong and read ≥ 90 % of the cambered parts.
- **R6, the builder rule:** refuse only if the chirality is wrong, **or** both the cylinder and radial
  readings are CONCLUSIVE and both disagree with the design camber's sign. That is
  `builder_direction_refusal` extended with the radial reading. It must:
  - refuse **none** of the S3_0014-cell parts;
  - refuse **every** mirror;
  - refuse every part whose design camber is deliberately flipped. Build 5 parts with
    `max_camber = −0.03` by bypassing `validate_blade_params` in your clone, to show a real backwards
    blade is still caught.

**Report:** a table like round 7's (cylinder / radial / combined), R1–R6 PASS/FAIL, and every wrong or
can't-tell part with its camber and lean. Proposal only, no diff.

---

## Task C: fuse memory at the fuse call (QA-27)

The guard runs inside `fuse_impeller`. At that point it checks free RAM against the **whole** estimated
peak × 1.15. But the process already holds part of that peak (here, 2.3 GB of S5_0011's 6.5 GB). So the
real question is whether the *remaining* growth fits, and nobody has measured it.

1. Build about 20 P builds on the **8gb tier (serial, one process)**, so nothing is summed across
   processes. Span faces from 10 k to 70 k, including at least 5 featured designs.
2. Extend your `sitecustomize` hook to record, at the `check_fuse_memory` call:
   - the worker's own `VmRSS`, and `MemAvailable`;
   - `n_faces`.
3. After the build, record the worker's own `VmHWM` (its peak), read from `/proc/<pid>/status` just
   before it exits. The hook can register an `atexit` that writes it.
4. **Report:**
   - the increment, `VmHWM − VmRSS_at_call`, against faces, with a least-squares fit;
   - `VmHWM` against faces (compare your intercept with your round-7 tree-sum);
   - for each build, whether `MemAvailable_at_call ≥ increment` would have held at the guard's 1.15 margin.
5. Use `time.monotonic()` for every limit (QA-28).

Pre-register only the comparison: "the guard is safe if, for every build, the increment ≤ 1.15 × the
estimate − RSS_at_call". No pass band is needed beyond that.

---

## Task D: built blade vs its numbers (planar vs cylindrical sections)

Your lt120 note found that cylinder cuts of the built blade read the chord up to 16 % short and the camber
low. BEM computes on cylindrical strips using the slider numbers, so if this is general, BEM and CFD are
scoring different blades.

There is a contradiction to settle. `chord_basis="measured"` (the default) is supposed to raise the loft
chord until the **cylinder-cut** chord matches (`fansim/geometry/chord_realisation.py`,
`prepare_loft_chords` / `loft_chords_for_measured_targets`). You found that switching it to `"loft"`
changed nothing on lt120.

1. **Find out why.** Read `chord_realisation.py`:
   - What does it measure, and at which radii? Only near the tip trim?
   - How is that different from `fansim.validation.section_compare.measure_sections`?
   - Give file:line evidence.
2. **Measure** param vs cylinder-cut chord, stagger, max camber and t/c at each station radius, for both
   chord bases, on:
   - Stock (`fansim.validation.blade_golden.stock_a12x25_params()`);
   - lt120;
   - 5 rows from `handoff/2026-10-09_to-qa-2/cfd_designs.csv`.
   Put the analytic estimator bias you measured (NACA 44xx reads 0.034–0.038) beside each camber number.
3. **Plot or tabulate** the gap against chord/r. The planar-section explanation predicts the gap grows
   with chord/r.
4. **Recommend**, but don't patch:
   - (i) wrap sections onto cylinders in the builder;
   - (ii) extend the measured-chord realisation to all radii and to camber;
   - (iii) give BEM the measured built sections.

   Include what each would change for Stock, whose recipe was fitted to the real STL through the same
   cylinder cuts.

Pre-register: "the gap is material if, at any station with chord/r ≥ 0.4, the chord differs by > 3 % or
the camber by > 0.005 beyond estimator bias".

---

## Task E (optional): near-stall flag

Unchanged from the round-5 brief, item 2. Pre-register it before looking at which designs stalled.

---

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**` and a new `handoff/2026-10-12_from-qa-8/`.
- Pre-register before tuning, patch decisions or picking thresholds. Commit and hash it **before** the data
  exists.
- Patches are proposals; I re-implement them.
- Big data stays gzipped (it's gitignored). No STLs from outside the repo get committed.
- Put a status line per task in the README of your from-qa folder.
