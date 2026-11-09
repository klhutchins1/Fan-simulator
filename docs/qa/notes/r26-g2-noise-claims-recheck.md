# r26 follow-up (grok, 2026-11-08): R1.10 G2 / QA-55 noise-claims re-check on master 83681c2

## Setup

- **Code under test:** `/workspace/fansim/repo-r26-g2`, a fresh clone of `handoff_in/master_83681c2.bundle`.
  - Bundle sha256 is `fdea337f408f24a503a3b22d740aa108aba06251b1deb641050596d34eeb8736` (matches).
  - HEAD is `83681c288487e3af2304ebe33e86f64d4afe76cb`.
  - There were no edits or commits; `git status` is empty afterwards.
  - G2 is `8d06672`, merged as `a3c112b` → `3fca917`.
- **Prereg:** branch `prereg/round26-g2-noise-claims`, commit **414177a** (`qa_r26/PREREG_R26_G2.md`). It was committed 2026-11-08 13:38 MST, before any G2 diff, grep, test or probe output.
- **Criteria:** taken from the 10-29 audit §G2 (claims A01, A04, A10, C10, C14, C16, C17, D03, E01) and the R0.4 ruling.
- **What did not run:** no Docker, CFD, OpenFOAM, Assess, Sweep or Optimize; no browser or UI render.
- **Scope:** G2 only. This is not round 27 and not full R1.10. G3–G5, R3.1, R3.5b and the night-gate counts 717/544/653 were **not** checked here.
- **Data:** `handoff/2026-11-08_from-qa-26-g2/`.

## Results per criterion

| | Criterion | Evidence | Verdict |
|---|---|---|---|
| K1 | The noise row is never ✓/⚠/better (C16, R0.4) | **Behavioural**, `g2_probe.json`, 7 cases: Stock hint +5 dB (more CFM), −5 dB, equal, +30 dB, no Stock; SWL-only path ±10 dB. Every case gives status `na`, `better` None, and no "noise" in the overall line. | **verified** |
| K2 | Expert hint text (R0.4) | **Behavioural:** all 5 hint cases contain "Scales with tip speed and airflow only; this is not a comparison of how quiet the design is.", contain no "louder/quieter", and have `expert_only` True. **Static:** Simple hides it via `fan_tab_ui.py:1392` `v_show="!row.expert_only \|\| ui_mode === 'expert'"`. **Visual check not done:** that the row actually renders in Expert and is hidden in Simple. | **verified** (text and flag); the render is **inspected, not verified** |
| K3 | README (A01, A04, A10) | **Static grep:** the ruled sentence is present at README:59–60. "tone + relative ranking are usable", "relative dB(A) ranking" and "relative dB(A)" each appear 0 times. README:4–5 "scores **noise** … (FluidX3D LBM; not validated)"; README:32 says "sound-level estimates (not validated)". `test_readme_says_noise_outputs_are_not_validated` passes. | **verified** (by grep test) |
| K4a | Design-list column (C14) | **Behavioural:** `design_dropdown_items` gives "#3 · free 50.0 · SWL est. 44.2", with no dBA or dB(A). | **verified** |
| K4b | Print sheet `noise_swl` (E01) | **Behavioural:** `print_readme` gives "… noise estimate 44.2 (not dB(A); not validated)", with no bare "noise_swl 44.2" and 0 bare dB(A) lines. | **verified** |
| K4c | Optimize text, `fan_tab_ui.py:1110` (C10) | **Static:** "Noise ranking is not validated. The blade-pass tone is rpm × blades; sound levels are estimates for exploration only." There is no "absolute dB" (the grep test passes). | **inspected**, string-tested |
| K4d | No bare dB(A)/dBA on model outputs in the cockpit | **Static**, all of `fansim/cockpit`, 7 hits, all exempt or qualified (see the list below). | **inspected**, passes |
| K5 | Secondary copy (C17, D03) | **Static:** `fan_flow_report.py:30` now reads "tip-speed + airflow hint (not a quietness ranking)", with no "dB-ish". `a12x25-reference.md:57` now reads "22.6 dB(A) max is the published datasheet number. Noise outputs are not validated…" | **inspected**, passes |
| K6 | Tests and red checks | **Behavioural:** see the next section. | **verified** |

K4d, the 7 cockpit hits:
- user-measured: `fan_tab_ui.py:406` and `fan_trials.py:150,191`;
- published: `figures.py:336` (traced to `fan_spec.ref_noise_dba`) and `fan_models.py:33`;
- qualified: `figures.py:13` and `prop_tab.py:469`.

## K6: tests and red checks

**Targeted tests: 24 passed** (2.1 s).

| file | tests |
|---|---|
| `test_r110_g2_noise_copy` | 4 |
| `test_flow_verdicts` | 16 |
| `test_design_dropdown` | 4 |

The board quotes "Related tests 25 passed"; its exact file set isn't stated, so I didn't reconcile the counts.

**Red checks** (scratch clone only):
- Changing the design-list label back to "dBA" gives 2 failed (`test_ui_model_outputs_have_no_bare_dba` and `test_swl_column_is_not_bare_dba`) and 6 passed.
- Restoring `flow_verdicts.py` to `8d06672^` gives 1 failed (`test_noise_hint_is_never_judged`, `'warn' == 'na'`) and 15 passed.

The G2 tests do catch both regressions.

## Verdict

- **G2 / QA-55 (noise claims A01, A04, A10, C10, C14, C16, C17, D03, E01): verified, closable.**
- The parts that are static only are named above: K2's render, K3, K4c, K4d and K5.
- The Expert/Simple visibility of the noise row was **not visually checked** (no browser work this round).
- R1.10 stays open. Its release gate still needs G3–G5 and the grok re-audit of the release candidate.

## New ID

- **QA-69 (LOW, scope edge, not a G2 blocker): `docs/design-rules.md:10` labels the LBM noise objective "Noise dB(A) (min)".**
  - The label comes from `scripts/extract_design_rules.py:106`.
  - The cockpit intro points users to that doc (`fan_tab_ui.py:497`).
  - The doc's own header says "relative", but this line is a bare model-output dB(A).
  - The line is not among the r21 claims, and `design-rules.md` is G4's file (D04, D05). Suggest relabelling it in G4, to "Noise estimate (relative, not dB(A); not validated) (min)" in both the generator and the doc.
  - No patch, to avoid conflicting with G4.

## Informational (no ID)

- `flow_verdicts.NOISE_JUDGED = False` keeps the old SWL judging branch as dead code. Setting it to True would judge again, which R0.4 forbids. `test_noise_judged_edges_if_ever_turned_back_on` covers that path on purpose.
- The G2 grep test scans only 5 cockpit files. `fan_trials.py`, `prop_tab.py` and `fan_models.py` are outside it; they comply today but are not guarded.
- 11 developer scripts in `scripts/` print LBM "dBA_band" values (research CLIs, mostly qualified in their docstrings). They are outside G2's UI and README scope and were not judged.

## Blockers and status (not tested here)

- **R1.10:** G3 is queued and not merged on this master; G4 and G5 are not done.
- **R3.1:** not landed (export and Task D are blocked).
- **R3.5b:** a rerun is queued, not passed.
- **R3.3:** reported done; not re-tested.
- **QA-68:** its follow-up note (`r26-qa68-recheck.md`, verified on 419df2e) is not on this master. It is preserved below.
