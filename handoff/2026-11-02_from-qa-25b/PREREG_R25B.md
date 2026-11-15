# QA round 25b pre-registration: light re-check of master 0635a18 (grok)

**Written:** 2026-11-02 MST, before any r25b data.

**Code:** `/workspace/fansim/repo-r25b`, a clone of `master_0635a18.bundle` (HEAD 0635a18). This is the code under test.

**Docs base:** my r25 `docs/QA_REVIEW.md`, from `repo-r25`. That file is uncommitted in Kimball's repo, so 0635a18's copy lacks it.

**Seen before this was written:**
- commit subjects 9d0118f..0635a18: 7ca6b93, f8189d2, 23704f5, the merge 94f71d9, and the board commit 0635a18;
- the committed brief `handoff/2026-11-01_to-qa-25/CLAUDE_TO_QA.md` and its diff against the r25 draft. It says "QA-65 landed in 9d0118f"; r25 B found the code not applied;
- Kimball's r25b message.

**Not yet opened:** any r25b code diff, render or pytest output.

## Status words (master only)

- **verified:** the item's pass rule holds on 0635a18. These items were never marked "fixed (pending QA)" on master, so a pass on master goes straight to verified.
- **still open:** the pass rule fails.
- **partly fixed:** some sub-rules pass, others fail; each one is listed.
- **not re-tested.**

## Rules

**UI-31.** The r25 A sub-rules (a), (b) and (c), applied on master:
- (a) render: 0 visible labels containing "Surrogate-guided" in Expert, all Optimize panels expanded. Headless cockpit with the r25 `a_tooltips.py`.
- (b) `cockpit_optimization_argv` with the state forced on emits no `--surrogate-guided`, run via r25 `a_ui31_cli.py`.
- (c) the CLI guard refuses with neither `--verify-cfd` nor `--stub-labels`.
- **verified** if all three hold.

**QA-62.** **Verified** if `tests/test_axial_scripts_oriented.py` passes and `validate_lt120.py` is listed.

**R1.11 CLI behaviour test.**
- Check whether `docs/qa/patches/r25-A-r111-cli-behaviour-test.patch` applies (`git apply --check`). If it does, apply it in a scratch copy only and run it.
- **covered** if master already has a test that drives the real parser or `main` through the guard;
- **patch still needed** if the patch applies and passes, but master has no such test;
- **patch broken** if the patch fails to apply or fails to pass.

**QA-66.** Code reading plus targeted tests. **Verified** only if all three hold; otherwise **partly fixed** with the list, or **still open**.
1. With `--verify-cfd`, training labels for the DoE/seed are not silently `synthetic_label`. Either a CFD or catalog `label_fn` is used, or the run refuses, or it prints and records a "synthetic" notice. A notice alone counts as "not silent".
2. `scripts/run_surrogate_search.py` does not add `--stub-labels` silently. It either refuses, or requires the flag explicitly.
3. Stub outputs on disk (`surrogate_guided.json` and/or `stub_result.json`) carry a "synthetic" / "not CFD" stamp.

**QA-65.**
- **still open** if `git apply --check docs/qa/patches/r24-C-k1-visible.patch` passes on 0635a18 (code not applied).
- If the code is applied: re-run r25 `b_qa65_review.py` on master. **verified** if `shows_only_when_False` holds, and record whether the Optimize-trial hole and the missing test remain.
- Also check whether `r25-B-qa65-test-and-trials.patch` still applies.

**"Drop dead tooltip" (23704f5).** List the `fan_copy.py` and `fan_tab_ui.py` changes, then:
- re-run the r25 `a_tooltips.py`, `scan_controls`/`build_inventory` and `range_check` on master;
- compare with the r25 branch data. Any UI-3x item whose output changes is reported, with its status.

**Other UI items and QA-40/42/61/63.** Unchanged code means status carried from r25 ("still open"). Re-run only the cheap harnesses above. QA-63 is checked by running `test_fuse_memory.py`.

**Tests.** Targeted pytest files only:
- `test_axial_scripts_oriented`, `test_fuse_memory`, `test_optimization_argv`, `test_r111_cockpit_surrogate` (if present), `test_score_caption`, plus any test file 23704f5 adds or changes.
- **No** full fast suite. `test_fan_tab_setup_smoke.py` (QA-67) is skipped.

**R1.11 verdict.** **Closable** if:
- UI-31 is verified,
- QA-62 is verified,
- the CLI behaviour test is covered,
- and QA-66 is verified.
Otherwise **not closable**, with the reasons.
