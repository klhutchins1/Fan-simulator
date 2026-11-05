# QA round 26 pre-registration (grok)

**Written:** 2026-11-04 MST, before any r26 data.

**Code:** `/workspace/fansim/repo-r26`, a fresh clone of `master_bd6abdd.bundle` at HEAD bd6abdd (the brief calls it `fansim.bundle`). This is the code under test.

**Docs base:** master bd6abdd's `docs/QA_REVIEW.md` and `docs/release/RELEASE_PLAN.md`. These now include r25 and r25b (a7d56a0).

**Seen before this was written:**
- the brief `handoff/2026-11-04_to-qa-26/CLAUDE_TO_QA.md` and its `PREREG_R26.md` (byte-identical to the handoff_in copies);
- commit subjects 0635a18..bd6abdd.

**Not yet opened:** any r26 code diff, render or pytest output.

These rules adopt the brief's PREREG_R26 word for word in meaning and add the items marked (+).

## Status words
- **verified:** the pass rule holds on bd6abdd.
- **still open:** the pass rule fails.
- **partly fixed:** some sub-rules pass, others fail; each one is listed.
- **not re-tested.**

## A. QA-66 (R1.11)
Method: code reading of `scripts/run_optimization.py`, `fansim/optimize/surrogate*`, `scripts/run_surrogate_search.py` and the catalog path, plus targeted tests: `tests/test_surrogate_guided.py` and `tests/test_r111_cockpit_surrogate.py`.

Where the code reading is ambiguous, I run small behaviour probes. These call only the stub path, or entry points that refuse; they never call CFD, Assess, Sweep or Optimize-with-CFD. A probe that would reach CFD is not run; that sub-rule is decided by code reading and marked "(code only)".

**Verified** only if all five hold, and both test files pass. Otherwise **partly fixed** with the list, or **still open**.
1. With `--verify-cfd`, the DoE/seed training rows are not `synthetic_label`. They come only from catalog rows and/or CFD verifies, or the run refuses. A printed notice alone no longer passes (stricter than r25b rule 1).
2. `scripts/run_surrogate_search.py` does not add `--stub-labels` when neither `--verify-cfd` nor `--stub-labels` is given; it refuses (non-zero exit or explicit error).
3. Stub outputs on disk (`surrogate_guided.json` and/or `stub_result.json`) carry "synthetic labels, not CFD" (or a clearly equivalent stamp).
4. `--verify-cfd` with no catalog, or fewer than 8 free-air rows, refuses up front, before any search or stub runs.
5. When the catalog fills `efficiency` (always) or `cfm_load` (when curve `k` is missing), `surrogate_guided.json` stamps those keys "prior, not CFD".

(+) **r25-A CLI behaviour test.**
- **covered** if master has a test that drives the real parser or `main` of `run_optimization.py` (or `run_surrogate_search.py`) through the guard and asserts refusal with neither flag.
- **patch still needed** if not, and `docs/qa/patches/r25-A-r111-cli-behaviour-test.patch` still applies and passes in a scratch copy.
- **patch broken** if it neither is covered nor applies/passes.

(+) **UI-31 / QA-62:** not re-tested unless a regression is obvious while doing A. `test_r111_cockpit_surrogate.py` passing counts as "no obvious regression" for UI-31(b).

## B. QA-65 (R1.2)
Do not apply any patch to the code under test; `git apply --check` only. **Verified** if all three hold:
1. `git apply --check docs/qa/patches/r24-C-k1-visible.patch` **fails** on bd6abdd, because the code is already applied (I confirm the failing hunks are already-present code, not unrelated drift).
2. `score_caption` / `stamp_score_extra`: `converged is False` shows "did not settle"; `True`, `None` and a missing key do not. `tests/test_score_caption.py` passes. Checked by re-running the r25 `b_qa65_review.py` (unchanged) on bd6abdd plus the test file.
3. Optimize trials carry `converged`: `fansim/optimize/study.py` sets the trial user attr, and `fansim/cockpit/data.py` copies it into the trial row. (+) Covered by a test, or by a stub-free unit probe that builds a trial row.

(+) If any sub-rule fails, QA-65 is **partly fixed**. Also report whether `docs/qa/patches/r25-B-qa65-test-and-trials.patch` is now redundant (`git apply --check` fails because the content is present) or still adds anything.

## C. UI-26
**still open** if 'Gold = parametric Stock' (or equivalent) is visible on the first view in Simple or Expert at 1366×768 or 1920×1080. **verified** only if it is gone from the first view in both modes at both sizes. Harness: the r25 `a_ui.py` on a headless cockpit (Preview-only clicks). A 1366 Simple miss that also happened on the other size in the same run, with no code change, is render timing, not a pass. Other UI (27, 29, 32–38) and QA-40/42/61/63 are **not re-tested** (carried still open). New bugs seen in passing are logged.

## D. Waiting
R3.1 export leak check and the R1.10 claims audit / QA-64 strings: recorded as still waiting. No data.

## Closing verdicts (+)
- **R1.11 / QA-66 closable** if A is verified (all five rules plus both test files), and the CLI behaviour test is covered (or "patch still needed" is accepted as a non-blocking follow-up, stated as such).
- **QA-65 closable** if B is verified.

## Tests
Targeted only:
- `test_surrogate_guided`, `test_r111_cockpit_surrogate`, `test_score_caption`, `test_optimization_argv`;
- any test file added or changed in 0635a18..bd6abdd that touches optimize/surrogate/score caption.

No full fast suite. `test_fan_tab_setup_smoke.py` (QA-67) is skipped.
