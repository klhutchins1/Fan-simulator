
## Round 26 follow-up (grok, 2026-11-08): QA-68 re-check on master 419df2e

**Build:** master `419df2e`, from bundle sha256 `24bcef9c…2e25c` (verified). Clone: `/workspace/fansim/repo-r26-qa68`. **Prereg:** `prereg/round26-qa68-recheck` 491f0d2, committed 2026-11-08 13:30 MST, before data. No Docker, CFD, OpenFOAM, Assess, Sweep or Optimize compute: Docker presence is mocked and CFD verify is guarded. No source edits. Note: `docs/qa/notes/r26-qa68-recheck.md`.

- **QA-68 (LOW): verified, closable.**
  - **Behavioural:** `run_optimization.py --surrogate-guided --verify-cfd` returns 2 with the refusal message and no exception in all 4 refusal cases (no catalog; 7-row catalog; Docker absent at the CLI guard; Docker absent at the library refusal). A real subprocess exits 2 with empty stderr. There were 0 CFD verify calls and no JSON written. An 8-row control reaches the guarded verify, which shows the mock is live.
  - **Tests:** r111 (9), surrogate_guided (11) and argv (16) give 36 passed. With the fix reverted in a scratch clone, the QA-68 test fails (1 failed, 8 passed).
  - **Static:** d08e48c (merged d365bea) is our script hunk exactly, and nothing later touches it.
  - **Info only, no ID:** the `except RuntimeError` covers the whole run, so a later runtime error would also exit 2 without a traceback.
- **Not re-tested:** R1.10 G2 (queued, not merged), R3.1 (not landed), R3.3 and the r26 carried items.
- **ID changes:** QA-68 → **verified**.
