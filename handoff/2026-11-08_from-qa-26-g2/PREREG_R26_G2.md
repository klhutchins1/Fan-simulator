# r26 follow-up pre-registration: R1.10 G2 / QA-55 noise-claims re-check (grok)

**Written:** 2026-11-08 MST, before any G2 code diff, grep, test or probe output.
**Code under test:** fresh clone `/workspace/fansim/repo-r26-g2` of `handoff_in/master_83681c2.bundle`
(sha256 fdea337f…8736, verified), master 83681c2. G2 = 8d06672, merged a3c112b → 3fca917.
**Seen before writing:** commit subjects 419df2e..83681c2; COORDINATOR_STATUS.md; RELEASE_PLAN R0.4 / R1.10 / R1.6
entries; the 10-29 audit §G2; r21 claims CSV rows A01 A04 A10 C10 C14 C16 C17 D03 E01.
**Scope:** G2 only. Not round 27, not full R1.10 (G3–G5), not R3.1/R3.5b. Night-gate counts 717/544/653 are not re-checked.
**Rules:** no Docker/CFD/OpenFOAM/Assess/Sweep/Optimize compute; no browser/UI render. No edits/commits in the snapshot.

## Evidence classes
- **behavioural:** a test or probe executed on 83681c2 (pure functions / string builders, no CFD).
- **static:** grep / code reading only → reported as **inspected, not verified**.
- **visual not done:** anything that needs a rendered cockpit is named as not checked.

## Criteria (from the 10-29 audit §G2 and R0.4 ruling)
- **K1 noise row never judged (C16, R0.4):** the flow-card noise row's verdict is never ✓/⚠/better, for a design with
  more CFM and one with less than Stock. Pass = behavioural probe of the verdict builder + its test passes.
- **K2 Expert text (R0.4):** the Expert hint carries "Scales with tip speed and airflow only; this is not a comparison
  of how quiet the design is." and no "quieter/louder than Stock" judgement. Pass = probe of the builder output (behavioural);
  that it is *shown in Expert only* is static unless a non-render test covers it.
- **K3 README (A01, A04, A10):** README contains "Noise outputs are not validated. The blade-pass tone frequency is exact
  (rpm × blades); sound levels are estimates for exploration only." (or same meaning), and no longer contains
  "tone + relative ranking are usable" / "relative dB(A) ranking" / "scores **noise**" unqualified. Static (grep).
- **K4 no bare dB(A)/dBA on model outputs (C10, C14, E01, Optimize caption):**
  - design list column (`data.py`, was "dBA") labelled as an estimate (e.g. "SWL est."), behavioural via the column table;
  - finalist print sheet `noise_swl` labelled (not bare dB(A); "not validated"), behavioural via the sheet builder if callable without CFD;
  - `fan_tab_ui.py` (was :1108) Optimize text not implying a usable ranking/absolute dB; static;
  - repo-wide grep of `fansim/`, `scripts/`, README, docs/a12x25-reference.md: every dB(A)/dBA hit is published/datasheet,
    user-measured, or qualified (estimate/relative/not validated). Each unqualified model-output hit = fail.
- **K5 secondary copy (C17, D03):** `fan_flow_report.py` no "dB-ish ranking"; `a12x25-reference.md` no "ranks designs relatively"
  without "not validated". Static.
- **K6 tests:** `tests/test_r110_g2_noise_copy.py`, `test_flow_verdicts.py`, `test_design_dropdown.py` pass; the G2 grep test
  fails on a scratch copy with one model-output label reverted to bare "dBA" (red check), if cheap.

## Verdict
- **G2 / QA-55 noise part verified** if K1, K4 (behavioural parts), K6 pass and K2, K3, K5 hold (static parts named as inspected).
- **partly fixed** with the list if any fail. QA-55 as a whole closes only for its noise claims; R1.10 stays open (G3–G5).
