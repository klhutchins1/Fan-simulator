# Claude → QA bot, 2026-10-15 (round 14)

Rounds 12 and 13 were useful: QA-35, QA-36 and the 24.4 table all came straight from them.
`fansim.bundle` (this folder) is master **`632ea7e`**. Pre-register A, B and C in **one** commit before any data.
D is research only.

## Fixed since round 13 (please verify, don't re-find)

| your finding | fix on master |
|---|---|
| QA-36 / 29.1 (PLA+ picker reached only Assess) | `active_spec()` carries the picked material (when it is registered), so Preview grams, the weight check, the Export README, temperatures, `print_fit` and the print-id registry all follow the picker. Your r12 tests are adopted as `tests/test_ui_says_what_it_does.py` |
| QA-35 (Linux open-fan fuse under-ask) | pre-registered refit of the Linux open constants: **0.515 GiB + 82.3 KiB/face** (was 0.28 + 72). Shroud and Windows constants are unchanged. Audit: `docs/validation/audits/2026-10-15-fuse-open-refit.md` |
| 24.4 leftovers (Preview verdict / Export hint read live state) | Preview's fits/weight verdict and cup build use the spec and cup switch **from the click**. Export's message uses the Fit-hub switch and hub height from the click. Two new tests change a setting mid-run |
| UI tests flaked on a busy box | your export tests now pin `FANSIM_MEMORY_TIER`; the free-RAM gate had refused before the worker |
| physics audit | **32/32 PROVEN**: Stock v3 handedness and 7 units re-proven (119 checks). The flow report's maths is now unit `cfd.flow_report` |
| QA-12 (prop CT0 creep) | **parked: needs data** (see Task D) |

## Overview

| # | task | kind | why now |
|---|---|---|---|
| A | **Re-verify today's fixes** (QA-35 on your Linux box, QA-36, 24.4) | short builds + headless UI | they were fitted or tested on Windows or your old data |
| B | **Independent maths check of the units that drive scores** | analysis, synthetic cases, no CFD | Kimball wants the maths re-checked: tests written by the same author can share the author's blind spots |
| C | **27.7 groundwork: the optimizer's space under wrap** (build-only, no CFD) | builds + measure | sliders now mean the built blade; the bounds were tuned when they didn't |
| D | **QA-12 data hunt**: measured small-prop static thrust at Re 6e4–1.5e5 | research, no downloads committed | the only way to un-park QA-12 |
| E | (optional) the 29.2 UI regression filler | headless tests | standing filler |

---

## Task A: re-verify

1. **QA-35 on Linux.**
   - Re-run your r12 Task B builds: the same 28 IDs, hook `hook_c11`, 8gb tier, serial.
   - **Pass:** every OK build has remaining growth ≤ 1.15 × `fuse_remaining_estimate_gb(...)` with the new
     constants.
   - Report the worst open and the worst shrouded ratio.
   - The refit used your r12 numbers; this checks it on a fresh run.
2. **QA-36 and 24.4.** Run `tests/test_ui_says_what_it_does.py`, then do one browser pass:
   - pick PLA+, Preview, Export. The weight line and README say PLA+, and the print temperatures are PLA+'s.
   - change the picker **during** a Preview and check the verdict line doesn't change for that build.
3. Update the QA-35 / QA-36 rows in `QA_REVIEW.md`.

## Task B: independent maths check (pre-register what "agree" means first)

For each unit below, derive the expected value **yourself, from first principles or a textbook**, on a
synthetic case that the existing tests don't use. Then compare it with the code. Read the unit's claim
in `fansim/audit/registry.yaml` first, and don't read its tests until your expected values are
written down.

1. **`cfd.cfm_from_outlet_flow`**: m³/s → CFM conversion, sign convention, and the tail-mean of an
   oscillating history (`fansim/cfd/metrics.py`). Synthetic `postProcessing` files with a known flow.
2. **The motor derate** (`fansim/optimize/rederate.py`, `fansim/motor/envelope.py`):
   - λ = min(1, (budget/P_shaft)^(1/3));
   - flow ∝ λ, pressure ∝ λ², efficiency invariant on a quadratic hose line.
   - Check that the hose operating point and the stamped scores follow that, with the motor efficiency at
     0.50.
3. **`fan.bem_prescreen`**: the momentum-theory bound (BEM never beats ideal actuator-disc pressure for
   its flow) and zero static rise at free delivery. Check on 5 random wrapped designs, not Stock.
4. **The wrapped section geometry** (`blade._section_loop(wrap=True)`): every point lies on radius r; arc
   length = t; a cylinder cut at r reads the designed chord, stagger and camber. Derive the expected cut by
   hand for one NACA section with lean 20° and skew 5 mm.
5. **The hub-hang measure** (`blade_hang_below_hub_mm`) against the built mesh. For 10 hanging designs,
   compare the designed hang with the lowest point of the **unclipped, chord-realised** lone blade minus
   the hub face. Expect realised ≈ 1.6 × designed (your r9 numbers). Report where that ratio comes from.
6. **The flow report card** is already checked (your r7 Task G). Skip it unless something above touches it.

**Pre-register:**
- agree = within 1 % (or 0.001 absolute) for exact formulas, and within the stated tolerance where the claim
  has one;
- any disagreement you can trace to a wrong formula is a defect (new QA-n);
- one that comes from a different convention is a documentation note.

## Task C: the optimizer's space under wrap (roadmap 27.7, build-only)

The optimizer's bounds (`fansim/optimize/search_space.py`, `suggest_params`) were tuned while a camber slider
of 0.06 built about 0.01–0.04. Under wrap, the sliders are the built blade.

Sample 300 designs from `suggest_params` (fixed seed) and report:
- the distribution of each slider against Stock v3's values (camber 0.024–0.048, stagger 22–40°);
- the share **refused by the 2 mm hang limit** (`validate_blade_params`), and which sliders drive the refusals;
- for 40 of the built ones, the built cylinder-cut camber and stagger against the sliders. Expect agreement
  now; anything else is a finding.

**Proposal only:** new camber and stagger bounds that bracket Stock v3 with sensible margin, and keep the
hang-refused share under about 5 %. **No optimizer campaign, no source edits.**

## Task D: QA-12 data hunt (research; nothing downloaded is committed)

QA-12 needs measured static thrust (CT0) for a small prop (~5–9") at Re(0.75 R) **6e4–1.5e5**, or measured
low-Re polars for the airfoil family the 5" preset uses (e387-like).

Find candidate datasets and list for each:
- URL, licence, prop or airfoil, diameter, pitch, rpm range, the Re(0.75 R) range you compute, and the
  data format;
- whether it is redistributable. We cite and keep data local unless the licence allows more (§25.8).

Candidates to check: UIUC propeller database volumes 1–4 (APC 8–9" at 5–6k rpm), thrust-stand datasets for
5" FPV props at 20–30k rpm, published low-Re airfoil polars (Selig, Lyon, Williamson).

Note: `docs/qa/notes/prop-ct0-data-sources.md`. Pick the best one or two and say what the comparison would
pre-register.

## Task E (optional)

29.2 UI regression tests, as in round 12 E: extend `tests/test_ui_says_what_it_does.py` with checks of the
form "we say X, we do Y". Proposals only.

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**` and a new `handoff/2026-10-15_from-qa-14/`.
- Pre-register before data, then commit and hash it.
- Patches are proposals only.
- No outside STLs or datasets committed.
- Big data stays gzipped (gitignored).
- If the box suspends, stop and mark FINAL.
- Status line per task in the README.
