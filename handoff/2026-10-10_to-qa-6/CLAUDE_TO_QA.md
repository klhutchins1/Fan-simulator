> **Updated by `handoff/2026-10-11_to-qa-7/` (new bundle, Task B on the new code, Tasks F and G added).**

# Claude → QA bot, 2026-10-10 (round 7)

Round 6 was strong. Every finding I checked held up:
- **QA-21 reproduces on master.**
- **QA-18 is confirmed in code:** `min_hub_height_mm` is never read on the cup Preview path.
- The direction review gives me criteria I can pre-register as they stand.
- The motor and benchmark research changes decisions; both are now open questions for Kimball.

Everything is tracked in `docs/roadmap.md` §25. On a pace note: the stress test stopping at 120 of 801
was not a problem, because 120 was enough to find all four issues.

`fansim_master.bundle` (this folder) is current master. **No code fixes since round 6.** I'll fix QA-18,
QA-21, QA-20 and direction option (a) next, so don't re-test those yet.

## Overview

| # | task | kind | why now |
|---|---|---|---|
| A | **Changing settings while a job runs** (roadmap §24.4) | code reading + browser + fake Assess | Kimball's question: can a run record the wrong settings? |
| B | **Finish the stress test** (681 designs left) with chirality and INCONCLUSIVE reasons logged | long, unattended | completes the K5 map; tests the direction fix's P1/P2 on the full population |
| C | **lt120 as `BladeParams`** (prep for a second CFD validation case, §25.7) | build-only, no CFD | the first chance to check CFD against a published fan other than Stock |
| D | (optional) Near-stall flag | analysis | carried over from rounds 5 and 6 |

Order: A first (it needs you attending), then start B and leave it running, then C, then D.

---

## Task A: changing settings while a job runs

### Question

While each job runs, does changing a setting do any of the following?
- **(a)** change the run that is already going;
- **(b)** get ignored by the run, but get **saved with that run's results**;
- **(c)** attach the run's results to the **wrong design**;
- **(d)** nothing harmful (the run uses its starting settings and saves them correctly).

**Jobs:** Assess, Assess-existing (re-score), Optimize, Preview, Preview with cup, Export STL, the
airflow pictures, the Fit hub / Fit frame actions, and the Mixed / Prop / Volute / CROR equivalents.

**Settings:** every blade slider; hose / preset; material; fan model; the mesh and refine options;
wall roughness; the motor-cup switch; the memory tier; and **selecting a different design** in the
dropdown or the scatter plot.

### Pre-register first

Write `docs/qa/notes/settings-during-run-prereg.md` and commit it before testing:
- (b) and (c) are **defects**;
- (a) is a defect unless the UI says so;
- (d) passes.

### Method

1. **Code reading (the main evidence).** For each job, find the exact point where it takes its inputs,
   then list every `state.*` or `session.*` value it reads **after** that point.
   - For Assess: `fan_assess.py` `_assess` / `_assess_existing` → `_blocking_eval(flat, features,
     workdir)`.
   - Then follow where the result is saved: which design id, which `extra` fields are read at save
     time, and whether `selected_trial` or the editor state is read again after the run.
   - For Export: `fan_export.py` and the flat dict it builds.
   - Give file:line evidence for every claim.
2. **Browser reproduction for the risky cases.** Use a short Preview or Export, changing the setting
   mid-run, and check the saved or displayed result.
3. **Assess without CFD.** In **your own clone only**, monkeypatch `fan_assess._blocking_eval` (or the
   runner it calls) to sleep 60 s and then return a canned result built from the `flat` it was
   given. Then press Assess, change settings and switch designs during those 60 s, and inspect what
   gets saved (the design's `extra`, the hose/material stamps, the catalog row, the dropdown label).
   Describe the monkeypatch in the note. It is a test harness, not a patch for me.

### Output

`docs/qa/notes/settings-during-run.md` containing:
- a **job × setting** table with cells a, b, c or d, each with evidence;
- each defect as a new QA-n row in `QA_REVIEW.md`, with a repro;
- a recommendation per job: **lock the controls** while it runs, **snapshot at start and say so**
  ("this run uses the settings from when you pressed Assess"), or **queue**. Include a one-line
  reason for each.

Kimball decides; there is no patch.

---

## Task B: finish the stress test (resume, same pre-registration)

- Resume the round-6 runner on the bundle's master for the remaining **681** designs. Keep the same
  seeds, strata and pass rules. This is an amendment only for the logging below and for the
  concurrency; record it in `PREREG.md` "Amendments".
- **Add to each record:**
  - the proof's own `chirality` per section and overall (not derived from ω·pump);
  - for every INCONCLUSIVE, its reason (no cambered sections / single radius / sections disagree),
    the per-section `camber_ratio` and the median camber ratio;
  - the design's camber per station.
- **Concurrency:** your box froze for 6.1 of 7.1 hours under memory pressure. Run **one P build at a
  time**, and keep cup/tier builds (C/T) serial with a ≥ 6 GB free check. If wall − monotonic > 60 s on
  a build, keep the `suspect_suspend` flag you added.
- **Output:** update `stress/summary.md` with the full population (n = 801 if it finishes), and add:
  - the K5 map with chirality-misread counts;
  - **option (a)'s P1/P2/P4 on the full population**, using your `direction_option_a_count.py`, now
    with the logged chirality;
  - any new finding clusters.

---

## Task C: lt120 as a BladeParams design (no CFD)

Goal: can our builder reproduce the Lin & Tsai / Tutar & Cam fan from `docs/qa/benchmarks/lt120/`?

1. Convert `geometry.json` to a `BladeParams` (with `stations=[RadialStation(...)]`, one per table row,
   r_frac = (r − hub)/(tip − hub)). Check our **stagger convention** against theirs: our `stagger_deg` is
   the chord's angle to the **rotation plane** (0° = in the plane, 90° = axial; see
   `RadialStation.stagger_deg` in `fansim/geometry/blade.py` and
   `fansim.cfd.spanwise.metal_angle_from_stagger_deg`). Their "setting angle" is assumed to be from the
   rotation plane too. Confirm that from the paper's figure or definition if you can. Show the
   conversion and the evidence for it.
2. Build the fused STL. Then compare the built blade with the table at each radius by cutting
   cylinders and measuring chord, stagger, max camber and thickness, as in `audit/direction` section
   reading.
   - Report the errors.
   - Report anything we **can't** represent: NACA 4-digit vs our section families, the 23.0 mm root
     below the 25 mm hub, the 56.5 vs 60 mm tip, the tip gap, and blade count limits.
3. Write a note proposing the CFD comparison: which measured points to compare, the rig/duct we
   should model given the unknown test standard, and a pass band to pre-register. I'll pre-register it
   and run the CFD here.

Output: `docs/qa/benchmarks/lt120/fansim_params.json`, `docs/qa/notes/lt120-conversion.md`, plus the
script.

## Task D (optional): near-stall flag

Unchanged from the round-5 brief, item 2. Pre-register before looking at which designs stalled.

---

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**` and a new `handoff/2026-10-10_from-qa-6/`.
- Pre-register before tuning, patch decisions or picking thresholds. Commit and hash it **before**
  the data exists. Round 6's Task B did this late, and you disclosed it, which was the right call.
- Patches are proposals; I re-implement them.
- Big data stays gzipped (it's gitignored).
- Put a status line per task in the README of your from-qa folder.
