
## Round 26 follow-up (grok, 2026-11-08): R1.10 G2 / QA-55 noise claims on master 83681c2

**Build:** master `83681c2`, from bundle sha256 `fdea337f…8736` (verified). Clone: `/workspace/fansim/repo-r26-g2`. G2 = `8d06672` (merged `3fca917`). **Prereg:** `prereg/round26-g2-noise-claims` 414177a, committed 2026-11-08 13:38 MST, before data. No Docker, CFD, Assess, Sweep or Optimize; no browser. No source edits. Note: `docs/qa/notes/r26-g2-noise-claims-recheck.md`.

- **G2 / QA-55 noise claims (A01, A04, A10, C10, C14, C16, C17, D03, E01): verified, closable.**
  - **Behavioural:**
    - The noise row is `na`, never better, in 7/7 cases (hint ±5/±30 dB, equal, no Stock, SWL ±10 dB), with no noise in the overall line.
    - The Expert hint text is exact and carries the `expert_only` flag.
    - The design list shows "SWL est. 44.2".
    - The print sheet shows "noise estimate 44.2 (not dB(A); not validated)".
  - **Tests:** g2_noise_copy (4), flow_verdicts (16) and design_dropdown (4) give 24 passed. Red checks on a scratch clone: a "dBA" label gives 2 failed; the pre-G2 `flow_verdicts` gives 1 failed.
  - **Static only:** README wording (ruled sentence present; old phrases appear 0 times); the Optimize text at `fan_tab_ui.py:1110`; `fan_flow_report` and `a12x25-reference` wording; 7 cockpit dB(A) hits, all published, measured or qualified.
  - **Visual not done:** the noise row's Expert/Simple visibility (`v_show` at `fan_tab_ui.py:1392`).
- **QA-69 (LOW, new): `docs/design-rules.md:10` (from `scripts/extract_design_rules.py:106`) says "Noise dB(A) (min)" for the LBM model output.** Suggest relabelling it in G4, which owns `design-rules.md`. Not a G2 blocker.
- **R1.10 stays open** (G3 not merged, G4/G5 pending, release re-audit). R3.1 is not landed; R3.5b is queued, not passed. Night-gate counts were not re-checked.
- **ID changes:** QA-55 (noise claims) → **verified**. New: **QA-69** (LOW).
