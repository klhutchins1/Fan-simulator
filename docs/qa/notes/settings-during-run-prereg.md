# Settings changed while a job runs: pre-registration (QA round 7, Task A)

- **Written:** 2026-10-11 MDT, before any Task A testing.
- **Code:** master `5980677` (`/workspace/fansim/repo-r7`).
- **Committed:** in the QA-only clone `/workspace/fansim/qa/prereg_r6`, branch `prereg/round7`.

## Question
For each job × setting pair, which of these happens when the setting is changed (or a different design is selected) while the job runs?
- **(a)** The change alters the run that is already going.
- **(b)** The run ignores the change, but the changed value is **saved with that run's results**.
- **(c)** The run's results are attached to the **wrong design**.
- **(d)** Nothing harmful: the run uses its starting settings and saves them correctly.

**Jobs:** Assess, Assess-existing (re-score), Optimize, Preview, Preview with cup, Export STL, the airflow pictures, Fit hub / Fit frame, and the Mixed / Prop / Volute / CROR equivalents.

**Settings:** every blade slider; hose / preset; material; fan model; the mesh and refine options; wall roughness; the motor-cup switch; the memory tier; and selecting a different design (dropdown or scatter plot).

## Verdict rules (fixed now)
- **(b) and (c) are defects.**
- **(a) is a defect unless the UI says so** (a visible message that the run picks up changes made during it).
- **(d) passes.**
- **(e) n/a:** the setting can't be changed while the job runs, because the control is disabled or the job is synchronous and blocks the UI. This passes, and is recorded as "locked".

## Evidence standard
- A cell is only classified with **file:line evidence**: the point where the job snapshots its inputs, and every `state.*` / `session.*` read after that point and up to the save.
- Where code reading alone is ambiguous, the cell is tested **headlessly in my own clone**:
  - Assess: `fan_assess._blocking_eval` is monkeypatched to sleep and then return a canned result built from the `flat` it was given.
  - Preview / Export: the job is driven through the cockpit's own handlers with state changes during the run.
  - Then check what is saved or displayed.
- **Browser reproduction:** the Round 6 brief dropped UI re-testing on this Linux box, so risky cells get headless reproduction instead. Any cell not reproduced is marked "code only".
- **Recommendation per job:** lock / snapshot-and-say-so / queue, with a one-line reason. Kimball decides.
