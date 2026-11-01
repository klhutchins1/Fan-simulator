# QA round 23 handoff (grok, QA bot), 2026-10-31 MDT: FINAL

- **Prereg:** `prereg_r6` branch `prereg/round23`, commit **0006f9b5cd196da077fd309a215503c8cb4d406c** (12:19:22
  MDT, before any data). `PREREG_R23_copy.md` is a verbatim copy (`cmp` against `git show 0006f9b:qa_r23/PREREG_R23.md`).
- **Code:** master **3b92eea** (bundle `master_3b92eea.bundle`; the brief's `fansim.bundle` is not on the box), cloned
  to `/workspace/fansim/repo-r23`. `uv sync --extra dev` was used for BEM only.
- **Rules kept:**
  - nothing committed to repo-r23, and no fansim edits;
  - no Docker, CFD, OpenFOAM, Assess or Sweep. Only BEM `pq_curve` was run (4.7 s).
  - No NC/ND or unclear-terms data was copied:
    - Tutar & Cam (CC BY 4.0) figures are cited by number, with approximate read-offs only;
    - the Cybenetics A12x25 table (terms unclear) was used only for % errors.
  - Edits only in `docs/QA_REVIEW.md`, `docs/qa/notes/r23-*`, this folder, and the grok r23 notes in `docs/release/RELEASE_PLAN.md`.

## Results
- **A (is 13.71 Pa / 60 CFM on lt120's knee?): AT THE KNEE, robust (100 % of 5000 MC draws).**
  - Measured slopes, 8→32→40→60→84 CFM: −0.703, −0.307, **−0.049**, −0.286 Pa/CFM (steep, flat, flat, flat).
  - 60 CFM is the high-flow end of a 40–60 CFM plateau. PCHIP slope −0.08 Pa/CFM at 60 CFM vs −0.42 at 84 CFM, so 1 Pa ≈ 12 CFM there.
  - No rising segment, so the stall dip is not resolved.
  - **CFD shape does not agree:** the CFD is on the steep branch at 13.71 Pa, with no plateau. Its slope on 6.85–13.71 Pa
    is 1.5–1.6× the measured one.
  - **Tutar & Cam 2025 (CC BY 4.0):** their own CFD (Figs. 8/9, prescribed flow) shows the plateau and calls 40–60 cfm the
    "stall range".
    - 6.85 Pa: **matched** (≈ 81 cfm, −3.5 %).
    - 13.71 Pa: **did not** in flow terms (≈ 41 cfm, range 38–50, against 60), although they are only ≈ 1 Pa (−7 %) low in pressure.
- **B ("near the knee" warning, proposal only): NEEDS MORE DATA.**
  - Rule R23-KNEE = K1 (unconverged) OR K2 (φ ≤ 0.6) OR K3 (P ≥ 0.6 × BEM shut-off).
  - Over 12 scored points: **6 hits, 1 miss (lt120 13.71 Pa, converged +24.5 %), 0 false flags, 5 clear.**
  - Only K1 fires. K2 is n/a without a free-air CFD (lt120, FAN-01); K3 never fires (Euler shut-off 38.9 / 45.2 Pa).
  - Draft spec: land K1 as the warning, show φ and P/shutoff as report-only, and add a "near-knee can be 25 % off even
    when converged" caveat.
- **C:** waiting (R3.1, R1.10). Not run.
- **New QA item:** QA-64 (LOW): the lt120 part of "validated near free air … within 8 %" is a 6.85 Pa point (about 20 % of
  shut-off), at +8.1 % mean / +9.5 % on the 6.2 mm mesh.

## Contents
- `scripts/a_knee.py`: A slopes, classes, verdict, MC 5000 (seed 23), PCHIP and CFD shape.
  Run: `.venv/bin/python a_knee.py <out.json>` (needs numpy and scipy); 0.4 s.
- `scripts/digitize_tc.py`: approximate read-off of Tutar & Cam Figs. 8/9 (download them from mdpi-res.com; not stored)
  plus the inverse flow at 13.71 Pa.
- `scripts/b_bem.py`: BEM `pq_curve` shut-off (Euler and axial_force) for the A12x25 Stock recipe and lt120. Run from the
  repo root with `.venv/bin/python`.
- `scripts/b_knee_rule.py`: scores K1/K2/K3/OR. Run with `python3 b_knee_rule.py b_bem.json <out.json>`.
- `scripts/b_k4_expl.py`: exploratory BEM-flattening K4x (post-hoc, not scored).
- `data/a_knee.json`, `data/b_bem.json`, `data/b_knee_rule.json`, `data/b_k4_expl.json`.
- Notes: `docs/qa/notes/r23-A-lt120-knee.md`, `docs/qa/notes/r23-B-near-knee-warning-spec.md`.

## Deviations
- **A:** neither lt120 CFD set has a free-air point, so the CFD shape uses the loaded points only (17.14 / 14.69 / 13.71 / 6.85 Pa).
  The tip-gap sets have one segment each, so their class is n/a and only the slope ratio is reported.
- **A, Tutar & Cam:** their CFD prescribes flow and reports pressure. "Matched/did not" was applied by reading their curve
  at 13.71 / 6.85 Pa (linear between their markers, ±0.5 Pa read error). Their pressure-at-60-cfm match is reported alongside.
- **B, choices the prereg left open:**
  - "A12x25 Stock" = the close-ref STL run (audit-02 §4), the run where 5/10 Pa held. The Stock-recipe run in the audit-02
    addendum has every loaded point unconverged, so K1 would flag all of them as hits.
  - The A12x25 5/10 Pa references come from the Cybenetics report (cited only).
  - The K3 shut-off is the `pq_curve` default (Euler, as in `bem_screen_cfm`); axial_force is reported as exploratory.
- **B, K2:** n/a for lt120 and FAN-01 (no free-air CFD), as the prereg's n/a rule says. Values with proxy Q0 are exploratory only.
