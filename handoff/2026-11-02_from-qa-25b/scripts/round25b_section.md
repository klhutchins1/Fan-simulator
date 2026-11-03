## Round 25b (grok, 2026-11-02): light re-check of master 0635a18

**Build:** master `0635a18` (2026-11-02 12:29 MST): merge `94f71d9` (`r111-onto-master`), fix `23704f5`, and board `0635a18` (R1.11 `done 23704f5`). Its `fansim/`, `scripts/` and `tests/` are byte-identical to `237a094`, the r25 branch.

**Prereg:** `prereg/round25b` d207af8 (`qa_r25b/PREREG_R25B.md`), committed 2026-11-02 16:22 MST, before any data.

No CFD, Docker, OpenFOAM, Assess, Sweep or Optimize was run, and no full fast suite. Only targeted pytest files ran, and `test_fan_tab_setup_smoke.py` (QA-67) was skipped. No source was edited.

Note: `docs/qa/notes/r25b-master-0635a18-recheck.md`.

- **UI-31: verified on master 0635a18.**
  - 0 Surrogate-guided labels render in Expert (9d0118f rendered 1).
  - `cockpit_optimization_argv` with the state forced on gives no `--surrogate-guided`.
  - The CLI guard refuses with neither `--verify-cfd` nor `--stub-labels` (`run_optimization.py:164-170`).
- **QA-62: verified on master 0635a18.** `test_axial_scripts_oriented` passes, and `validate_lt120.py` is listed.
- **R1.11 CLI behaviour test: patch still needed.** Master's test only unit-tests `surrogate_guided_cli_error`. `docs/qa/patches/r25-A-r111-cli-behaviour-test.patch` applies, and gives 7 passed on a 0635a18 scratch copy (master alone: 5).
- **QA-66 (MED): still open on master, 0/3 rules.**
  1. `--verify-cfd` still trains the DoE on `synthetic_label` (`surrogate_search.py:458,484`), with no notice.
  2. `run_surrogate_search.py:26-27` adds `--stub-labels` silently.
  3. No "synthetic / not CFD" stamp on disk: `stub_result.json` has none; `surrogate_guided.json` has only `notes` "verify=stub" and `reason` "stub-verify".
  - The board's "stamps stub output" is **stdout only** (`run_optimization.py:179-180`).
- **R1.11: not closable.** The CLI test is not covered, and QA-66 is open. UI-31 and QA-62 are verified.
- **QA-65 (MED): still open on master.** The code is **not** on 0635a18: `r24-C-k1-visible.patch` still applies, and unpatched master shows no warning for `converged=False`.
  - The committed brief and the Next-round header say "QA-65 landed in 9d0118f"; that is incorrect.
  - On scratch 0635a18 with r24-C and r25-B, the behaviour is the same as r25: only `converged is False` warns.
  - `r25-B-qa65-test-and-trials.patch` still applies. `test_score_caption.py` gives 11 passed on scratch and 9 on master.
- **"Drop dead tooltip" (23704f5): no UI-3x status change.**
  - It removes only `opt_surrogate_guided` from `OPT_SEARCH_HELP`.
  - a_tooltips, scan (4221 leaves), inventory (292 rows), range_check (58 rows, 20 mismatches), a_probe and a_flowcard are all identical to the r25 branch data.
  - a_ui differs in 1 timing field only.
- **Carried, still open on 0635a18:**
  - UI-26 (1366 Simple miss again, render timing), UI-27, UI-29, UI-32 … UI-38;
  - QA-40, QA-42, QA-61 (8 hits, identical);
  - QA-63 (`test_fuse_memory`: 1 failed, `1.934 < 1.925` false).
  - QA-64 and QA-67 are unchanged and were not re-tested.
- **Targeted tests:**
  - 4 files: 1 failed (QA-63), 33 passed, 1 skipped;
  - `test_score_caption` + R1.11 + argv: 30 passed.
- **ID changes:** UI-31 and QA-62 → **verified**. There are no new IDs.
