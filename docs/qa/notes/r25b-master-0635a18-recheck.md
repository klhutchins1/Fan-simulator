# r25b: light re-check of master 0635a18 (grok, 2026-11-02)

**Code under test:** master `0635a18` (2026-11-02 12:29 MST), from `master_0635a18.bundle`. HEAD was verified.
- `94f71d9` merges `r111-onto-master`.
- `23704f5` is "fix(opt): refuse ungated surrogate-guided stub ranks; cockpit argv helper; drop dead tooltip".
- `0635a18` is the board commit that marks R1.11 `done 23704f5`.

**Prereg:** `prereg/round25b` d207af8 (`qa_r25b/PREREG_R25B.md`), committed 2026-11-02 16:22:37 MST, before any r25b data. A copy is in `handoff/2026-11-02_from-qa-25b/`.

**Docs base:** my r25 `docs/QA_REVIEW.md`, merged onto 0635a18's copy, which carries Cursor's Next-round edit. The r25 diff applied cleanly.

**Not run:** CFD, Docker, OpenFOAM, Assess, Sweep or Optimize; the full fast suite; `test_fan_tab_setup_smoke.py` (QA-67). No source was edited and nothing was committed to the repo clone.

## Key fact

On 0635a18, `fansim/`, `scripts/` and `tests/` are **byte-identical** to branch `r111-hide-surrogate @237a094`, the head r25 tested (`diff -rq`, 0 differences). The harness outputs below agree: apart from timing, they match the r25 branch data exactly.

## Results (master 0635a18)

| item | rule (prereg) | result | status |
|---|---|---|---|
| UI-31 (a) render | 0 visible "Surrogate-guided" labels in Expert, Optimize expanded | 0 labels, and the body does not mention it. Master 9d0118f had 1. | pass |
| UI-31 (b) argv | `cockpit_optimization_argv` with the state forced on has no `--surrogate-guided` | none; the seam is `cockpit_optimization_argv`, and `fan_optimize.py:60` sets `surrogate_guided=False` | pass |
| UI-31 (c) CLI guard | refuses with neither `--verify-cfd` nor `--stub-labels` | "ERROR: --surrogate-guided needs --verify-cfd or --stub-labels (synthetic labels, not CFD)." `run_optimization.py:164-170` returns 2. The other 3 combinations pass through. | pass |
| **UI-31** | all of a, b, c | | **verified on master 0635a18** |
| **QA-62** | `test_axial_scripts_oriented` passes and `validate_lt120.py` is listed | passes; `validate_lt120.py` is in `AXIAL_SCRIPTS` (line 14) | **verified on master 0635a18** |
| R1.11 CLI behaviour test | covered / patch still needed / patch broken | master's `test_cli_refuses_surrogate_guided_stub_without_a_gate` only unit-tests `surrogate_guided_cli_error`. Nothing drives the parser or `main`. `r25-A-r111-cli-behaviour-test.patch` passes `git apply --check`, and on a 0635a18 scratch copy `test_r111_cockpit_surrogate.py` gives **7 passed** (master alone: 5). | **patch still needed** |
| **QA-66** rule 1 | `--verify-cfd` must not silently train on `synthetic_label` | fails. `surrogate_search.py:458` has `label = label_fn or synthetic_label`; the CLI never passes a `label_fn`; `:484` labels the DoE (24 by default) with it. There is no notice: `run_optimization.py:179-180` prints "synthetic labels, not CFD" only when `--stub-labels` is set *without* `--verify-cfd`. | fail |
| QA-66 rule 2 | `run_surrogate_search.py` must not silently add `--stub-labels` | fails. `scripts/run_surrogate_search.py:26-27` prepends `--stub-labels` when neither flag is given. The stdout line does print, but the user never asked for stubs, and the guard is bypassed by design. | fail |
| QA-66 rule 3 | stub outputs on disk stamped synthetic / not CFD | fails. `stub_result.json` (`surrogate_search.py:334-335`) holds only params and label values. `surrogate_guided.json` (`:540`) has `notes` with "verify=stub" and per-candidate `reason` "stub-verify", but no "synthetic" / "not CFD" stamp, and nothing says the DoE labels are synthetic. | fail |
| **QA-66** | all 3 | 0/3 | **still open (MED)** |
| **QA-65** | still open if `r24-C-k1-visible.patch` still applies | it applies, so **the code is not on master**. `b_qa65_review.py` on unpatched 0635a18: `converged=False` shows **no** warning (`shows_only_when_False=false`). On scratch 0635a18 with r24-C and r25-B applied: only `converged is False` warns (`shows_only_when_False=true`), and the reject text is the same as r24. `r25-B-qa65-test-and-trials.patch` still applies; `test_score_caption.py` gives 11 passed on scratch and 9 on master. | **still open (MED)** |
| "drop dead tooltip" | re-run a_tooltips / scan / inventory / range_check and compare with r25 branch data | 23704f5 removes only `OPT_SEARCH_HELP["opt_surrogate_guided"]` (`fan_copy.py`, −7 lines). a_tooltips: 0 diffs. scan: 0 diffs over 4221 leaves. inventory.csv: byte-identical (292 rows; master 9d0118f had 293). range_check: identical (58 rows, 20 mismatches, as on 9d0118f). a_probe and a_flowcard: 0 diffs. a_ui: 1 diff (PLA+ preview 7 s → 6 s, timing). | **no UI-3x status changes** |

### Other items (code identical, so status carried; cheap harnesses re-run)

- **UI-26: still open.** Jargon renders in 3 of 4 viewports. The 1366 Simple view misses it again, the same as on both r25 heads (render timing).
- **UI-27, UI-29: still open.** a_ui and a_probe are identical to r25.
- **UI-32 … UI-38: still open.** Harness diffs are zero.
- **UI-34:** Boost/NN still do nothing unless GP skip is on. The GP-boost/NN tooltips (`fan_copy.py:137-145`) now name only GP skip. That matches the code now that Surrogate-guided is hidden, but the switches are still enabled with GP skip off.
- **QA-40: still open** (a_flowcard A4_PASS = false, identical).
- **QA-42: still open.**
- **QA-61: still open.** 8 grep hits, identical to r25.
- **QA-63: still open.** `test_fuse_memory.py`: 1 failed (`assert 1.9343660736083983 < 1.925224`).
- **QA-64: unchanged** (no audit or README files changed since 9d0118f). **QA-67: unchanged**; the test was not run.

**Targeted pytest totals:**
- `test_axial_scripts_oriented`, `test_fuse_memory`, `test_optimization_argv`, `test_r111_cockpit_surrogate`: **1 failed (QA-63), 33 passed, 1 skipped**.
- `test_score_caption`, `test_r111_cockpit_surrogate`, `test_optimization_argv`: **30 passed**.

## R1.11 verdict: **not closable**

- UI-31: verified.
- QA-62: verified.
- CLI behaviour test: **not covered** (patch still needed).
- QA-66: **still open, 0/3**.

The board says the CLI "stamps stub output 'synthetic labels, not CFD'". That text goes to **stdout only**, and only for `--stub-labels` without `--verify-cfd`.

Suggested close-out, as a proposal only (no source edits by QA):
- (1) refuse `--verify-cfd` + `--surrogate-guided` unless a CFD or catalog `label_fn` is wired, or print and record "DoE labels synthetic"; also stop the silent stub fallback at `surrogate_search.py:470-475`;
- (2) drop the auto `--stub-labels` in `run_surrogate_search.py`;
- (3) write `"labels": "synthetic, not CFD"` into `surrogate_guided.json` and `stub_result.json`;
- (4) apply `r25-A-r111-cli-behaviour-test.patch`.

## Brief and board corrections

- The committed brief (`handoff/2026-11-01_to-qa-25/CLAUDE_TO_QA.md`) and the master QA_REVIEW Next-round header both say "QA-65 landed in `9d0118f`". **That is false**: the patch still applies cleanly on 0635a18, and unpatched master shows no warning.
- RELEASE_PLAN R1.11 says "stamps stub output". This is stdout only (see above).

## Data (box paths)

- `/workspace/fansim/qa_r25b/data/master0635a18/`: a_ui, a_probe, a_tooltips, a_flowcard, scan, inventory, range_check, qa61_grep, qa62_list, targeted_tests.txt, extra_tests.txt.
- `/workspace/fansim/qa_r25b/data/`: a_ui31_cli_master0635a18.json, r25A_patch_scratch.txt, b_qa65_review_0635a18_{unpatched,plus_patch}.json, qa65_scratch_score_caption.txt.
- Screens: `/workspace/fansim/qa_r25b/screens/master0635a18/` (7 files).
- Copies of the JSON, txt and csv data and of the scripts are in `handoff/2026-11-02_from-qa-25b/`.
