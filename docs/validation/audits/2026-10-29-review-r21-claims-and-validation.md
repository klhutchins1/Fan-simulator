# Review of grok r21 A (release claims audit) and r21 B (VALIDATION draft): board R2.1 / R1.5 / R1.6 / R3.8

Claude, 2026-10-29, reviewer role (Cursor is lead). Read against the audits, not the board.

## Verdict

**r21 A is confirmed.** 60 claims: 20 supported, 20 need a label, 15 overstated, 5 unsupported. I spot-checked the two
with the most user impact against the code:
- **C15** (`fan_assess.py:405-411`): it compares the *scored* `cfm_free` with `spec.ref_cfm` (the Noctua **datasheet**,
  60.1) and labels that "stock". Confirmed: Stock assessed against itself reads about −17 % "lower free-air".
- **C13** (`figures.py:399`): "CFD also under-predicts static ~2×" has no audit behind it. v5 is −9 to −13 % at shut-off.

**r21 B is approved** as the base for `docs/VALIDATION.md` (R3.8). Its recomputed numbers agree with the audits, and its
mismatches M1–M9 are real. M3 and M5 are mine (R1.4 wording): fix as below.

**The release gate stays:** 0 overstated and 0 unsupported user-facing claims before v0.1.0 (grok's pre-registered rule).
grok re-runs the audit on the release candidate (R4).

## Fixes (Cursor; one branch per group, each with a grep or UI test)

### G1 (worst first): the Assess message compares with the datasheet (C15 / M6, QA-56)

Replace the "vs stock free" line with a like-for-like comparison:
- **If a scored Stock result exists at the same test settings:**
  `vs Stock (same test): +X % free air`, using Stock's scored `cfm_free`.
- **If not:** omit the comparison. Never compare a scored number with a datasheet number in the same sentence.
- The datasheet marker on the plot stays: it is labelled as a datasheet value (C09, C11 are supported).
- Test: assessing Stock against itself prints 0 % (or no line), never "−17 %".

### G2: noise (A01, A04, A10, C10, C14, C16, C17, D03, E01; QA-55; carries out R0.4 and R1.6)

- Flow card noise row: never ✓/⚠/better (R0.4, still `ready`). Expert text: "Scales with tip speed and airflow only; this
  is not a comparison of how quiet the design is."
- README: replace "tone + relative ranking are usable" with "Noise outputs are not validated. The blade-pass tone
  frequency is exact (rpm × blades); sound levels are estimates for exploration only."
- No bare "dB(A)/dBA" for model outputs anywhere: the design list column, the finalist print sheet `noise_swl` and
  `fan_tab_ui.py:1108`. Datasheet values may keep "dB(A)" with "published".

### G3: "honest MRF CFD" for Volute/Mixed (C22, C24, C25; QA-57; carries out R2.4)

- "Assess runs MRF CFD (not validated against published data)".
- Mixed tab and results: "Experimental: not validated against published data" (R2.4 wording).
- Volute: "ranking only, unvalidated (CFD not yet converged)" until R2.5 resolves.

### G4: stale or wrong numbers (A02, A16, C02, C05, C13, D01, D02, D04, D05, D07; QA-58)

- `figures.py:399`: drop "~2×". Say "CFD's static-pressure ceiling is a little below the datasheet's (about 10 %)".
- `fan_tab_ui.py:493`: "Assess runs two CFD solves (free air and a loaded point), about 20–40 min".
- `fan_copy.py:129`: drop "under-ranks CFD (~0.6×)". BEM is "ranking only; coarse; can't separate close designs".
- "~3–5 % discretization" → "screening mesh, GCI ≈ 21 %; ranks designs, ±1 % run to run on Stock" (`design-rules.md:43`,
  `adversarial-review.md:237`).
- `design-rules.md:39-40`: delete "more blades raise airflow" (its own table gives ρ −0.35).
- `a12x25-reference.md:24`: "validated on a close-reference STL of the A12x25: 59.8 vs 60.1 CFM". At :30, replace
  "every gap … closed" with a list of what is still open (near-stall points, Stock recipe gap).
- README "The one real gap" → "Known limits", as a list:
  - nothing printed or measured yet;
  - propeller CFD is not a performance predictor (BEMT is);
  - volute CFD is unconverged;
  - mixed-flow and CROR are not validated against published data;
  - noise levels are not validated;
  - the Stock recipe reads about 5 % low.

### G5: labels already decided but not landed (A08, A12–A14, C04, C06–C08, C12, C19, C21, C23, C26, C27, E01, D08, D09)

- **R1.4 Stock gap.** grok r22 A verified the README and the Stock Expert caption. It must also go in `fan_trials.py:354`.
  - **M3:** in `docs/VALIDATION.md`, say that 58.3 is the close-reference STL **in the cylinder-sections diagnostic
    rig**, and 59.8 is the same STL in the full v5 setup. Never put 58.3 next to the datasheet 60.1 without naming the rig.
  - **M5:** the link target is `docs/validation/audits/2026-10-12-cylinder-sections.md` (there is no "wrapped-sections"
    audit file).
- **R1.5:** structural/flutter outputs say "estimate, not validated (resonance check, not flutter)". Drop "safety" from
  "cheap safety gate".
- **R2.1 prop:**
  - BEMT: "±15 % on thrust at static; worse toward zero-thrust J; validated on a known-section prop (TU Delft) within 7 %".
  - Prop CFD: "not a performance predictor: thrust reads 40–60 % low in validation; use it for direction and flow
    pictures only".
- **Print knockdown (C04):** "an assumed 5 % print loss, not yet measured".
- **Export print sheet (E01):** add "screening mesh: compare designs, not absolute airflow; Stock reads about 5 % low".
- **Historical banners:** `adversarial-review.md` ("historical, 2026-09; see docs/VALIDATION.md") and the superseded
  "+22–29 %" line in `a12x25_pq_report.md`.

## R3.8

Cursor adopts `docs/qa/notes/r21-B-validation-draft.md` as `docs/VALIDATION.md`:
- apply M1–M9;
- link every number to its audit;
- add the lt120 result when R1.1b has a verdict, and the prop CFD outcome when R2.2 ends.

grok checks the final page against the audits (round 23).
