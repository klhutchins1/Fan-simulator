
## G3 re-check (grok, 2026-11-09): R1.10 G3 / QA-57 on master 41e2dc9

**Build:** master `41e2dc9`, from bundle sha256 `f999d7de…5939` (verified). Clone: `/workspace/fansim/repo-r26-g3`. **Prereg:** `prereg/g3-41e2dc9` 7e3e214, committed 2026-11-09 09:33 MST, before data (from a separate worktree). No CFD, Docker or OpenFOAM, and no Assess, Sweep, Optimize, Export or Randomize. No source edits. Note: `docs/qa/notes/g3-recheck-2026-11-09.md`.

- **G3 claims C22, C24 and C25: verified.**
  - **Rendered (headless, empty run):** the Expert tab reads "MIXED · EXPERIMENTAL", with tooltip "Experimental: not validated against published data". Mixed Design and Results show "Assess runs MRF CFD (not validated against published data)". The Volute tooltip and Optimize lines say "ranking only, unvalidated (CFD not yet converged)". There are 0 "honest" lines in Mixed or Volute.
  - **Probe:** the mixed export sidecar text carries both sentences.
  - **Tests:** G3 copy (4) + simple-mode copy (28) give 32 passed. A red check fails 2 tests.
- **QA-57 (MED): partly fixed.**
  - The Mixed side is done.
  - The **Volute Assess** copy and result readout still have no unvalidated/unconverged label (`volute_tab.py:159,163,410-419`); the label sits only on the Optimize lines.
  - Patch: `docs/qa/patches/g3-QA57-volute-assess-label.patch`, with a test that fails without the fix (33 passed on scratch).
- **Info only:** the Mixed Optimize done-message has no label (the readout keeps it), and the Export message doesn't mention the sidecar `.md`.
- **ui-hunt-1 regression:** UI-39, UI-40, UI-41, UI-42 and QA-70 are **still open** on 41e2dc9. The cited files are unchanged since 83681c2, both patches still apply, and the probes repeat.
- **R1.10 stays open** (G4/G5, release re-audit). R3.1 is not landed; R3.5b is still "rerun". The night-gate counts 668/568/683 were not re-checked.
- **ID changes:** none new. QA-57 → **partly fixed**.
