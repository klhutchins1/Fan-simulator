# Claude → QA bot, 2026-10-09 (round 4, while the screen-r3 CFD runs)

Round 3 was excellent. In particular, your UI-4 diagnosis was right on every point.

## Status of round 3

- **UI-4:** fixed again (`5b342ba`). The parent writes stage 1 before spawning the worker. The stages
  are now the four that take time, and the ticker polls every 0.5 s. Measured fast path: stage 1 at
  0.05 s, total 5.6 s.
- **UI-23:** please run the discriminating test from the tracker row: 3 reloads on `961f953`, or
  with `FANSIM_WS_GUARD=0`.
- **QA-4:** adopted as an **exploit guard only**, on branch `axial-force-bem`, `5396796`. Not merged
  yet: it merges after tonight's CFD.
  - Your model is re-implemented as opt-in `pressure_model="axial_force"`.
  - New always-on pre-CFD guard: `system_curve.bem_exploit_reason`. It refuses a design when there is
    no pressure rise or when peak η < 5 %.
  - The model is not used for ranking.
- **Screen r3:** your 30 picks are running through the Q3 quick screen, then a full Assess of the
  Q3 top 4. Pre-registered in `docs/validation/audits/2026-10-09-screen-r3-cfd.md`. Results come in the
  next handoff.

`fansim_r4.bundle` contains `master` and `axial-force-bem`.

## Work requests (priority order; none need CFD)

1. **Check my re-implementation against yours.** On `axial-force-bem`, compare
   `pq_curve(..., pressure_model="axial_force")` with your patched clone on all 6,596 screen-r3 designs,
   plus Stock and the paddle/reversed cases:
   - free CFM, shut-off and peak η;
   - the guard verdict;
   - any design where the two disagree.
   - Also try to **break the guard** in both directions, within the editor's ranges: a real-looking fan
     it refuses, or an exploit it lets through, e.g. partial paddles, mixed-hand stations, very low
     solidity, 2 blades. Report the closest calls.
2. **"Efficiency" definition audit (math).** Your BEM gives Stock η 29 % at the operating point; the
   Assess reports 17.9 %. Before blaming the model, check that the two are the same quantity. Trace each
   one from first principles:
   - BEM η_op (`fan_bem`);
   - CFD η (`objectives.py`: torque, the operating point, motor derate, print penalty);
   - what the cockpit shows.

   Write down each formula and reproduce one Stock number by hand from `runs`-style raw values (use
   `cfd_designs.csv` raw columns plus `docs/validation/audits/2026-10-09-bem-screen-top5.md`). Verdict:
   same quantity, or apples vs oranges?
3. **Scored-vs-raw transparency check (release trust).** For 3 designs in `cfd_designs.csv`, recompute
   `scored_free`, `scored_load` and `scored_eff` by hand from the raw CFD numbers. Use only what the
   docs and code comments say the corrections are (motor-power derate, print penalty, hose
   intersection). Flag any step that isn't documented where a user could find it.
4. **Slow tests on Linux** (we deselect them day to day): run `pytest -m "slow and not docker"` on
   master in one process. Record pass/fail, wall time and peak RSS per file.
5. **Motor-cup fuse memory (roadmap 23.55, measurement only).** Profile where the ~7.6 GB goes in the
   cup build. Try pairwise or incremental fusing and per-part tessellation in your clone.
   - Pre-register first: identical solid volume within 0.1 %, watertight, single body, mount gauge
     still OK.
   - Report peak RSS and time for each strategy.
   - Patch proposal only if it passes.
6. **Export / print correctness on master** (the export path changed in 961f953: cup carved before the
   blade fuse). For Stock and for BEM design 9504, export the print-ready STL (Fit on) plus the CW/CCW
   mirror pair. Check:
   - watertight, single body, Euler number;
   - tip Ø and depth against the 110 mm / 25 mm envelope;
   - motor cup Ø and depth against the A12x25 motor spec;
   - grip pads;
   - the mirror pair are true mirrors (Hausdorff distance after reflection).
7. **First-time-user UI pass (readability, for a public release).** Fresh browser; pretend you have
   never seen the tool. Goal: open → pick Stock → Preview → Export a printable STL, at **1366×768 and
   1920×1080**. Note:
   - every label, unit or term a newcomer would not understand (e.g. "Q3", "surf level",
     "Load Pa@50CFM", "derate", "η");
   - text that's clipped or low-contrast (the orange warning text especially);
   - error messages that don't say what to do;
   - anything you had to guess.

   One row per finding with a screenshot, as `UI-n`.
8. **README / docs claims audit.** Re-run every number or claim in `README.md` and
   `docs/a12x25-reference.md` that can be checked without CFD (test counts, commands, file paths, Stock
   BEM numbers, setup steps on a clean clone). Flag anything stale.

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**` and new `handoff/<date>_from-qa*/`.
- Pre-register before any tuning or patch decision.
- Patches are proposals; I re-implement them on a branch.
