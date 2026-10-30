# QA round 21 handoff (grok, QA bot), 2026-10-25 MDT — FINAL

- **Prereg:** `prereg_r6` branch `prereg/round21`, commit **956b8ffa209d17e8c50af72050198b95657b54df** (15:41:33
  MDT, before any data). `PREREG_R21_copy.md` is a verbatim copy.
- **Code:** master **5063a65** (bundle `fansim_master_r21.bundle`), cloned to `/workspace/fansim/repo-r21`.
- **Rules kept:**
  - nothing committed to repo-rN, and no fansim edits;
  - no Docker, CFD, OpenFOAM, Assess or Sweep;
  - no outside STLs;
  - edits only in `docs/QA_REVIEW.md`, `docs/qa/notes/r21-*`, `handoff/2026-10-25_from-qa-21/data/`, this folder, and the grok notes in
    `docs/release/RELEASE_PLAN.md`.

## Results
- **A (release claims audit): FAIL.** 60 claims: 20 supported, 20 need a label, 15 overstated, 5 unsupported.
  - The worst:
    - the Assess message "vs stock free 60 CFM" is really vs the Noctua datasheet (QA-56);
    - the noise ranking is presented as usable (QA-55);
    - Volute/Mixed are called "honest MRF CFD", and Mixed is not labelled experimental (QA-57);
    - "validated on Stock: 59.8" (it is the close-ref STL) and "~3–5 % discretization" against GCI ≈ 21 % (QA-58).
  - The missing labels are the board's undone R1.4 / R1.5 / R1.6 / R2.1 / R2.4 items (QA-59).
  - QA-53 is still open (README port, Assess time, clone URL).
- **B (draft `docs/VALIDATION.md`):** 13 surfaces plus a "Known limits" list, with R1.4 wording verbatim.
  - 9 board/user-text mismatches; the main ones are:
    - Stock v2 −5.5 % vs v3 −4.5 %;
    - 59.8 vs 58.3 for the same STL, from different rigs;
    - the "`wrapped-sections` audit" link has no file;
    - prop CFD "35–45 % low" holds at static only (−58 % at J 0.43);
    - figures "~2×" has no source, and BEM "~0.6×" is stale.
  - Everything else recomputes within rounding.
- **C (lt120 pre-check, no CFD):**
  - P = `replace(load_blade_params(fansim_params.json), section_wrap="cylinder", clip_below_hub=False)` →
    `build_impeller`.
    - 9/9 cuttable radii PASS (26.7–56.5 mm): worst 0.11 % chord, 0.06° stagger, 0.0006 camber against the
      same-estimator reference.
    - r 23.0 is N/M (inside the hub).
    - One watertight solid, 7 blades, direction CONCLUSIVE.
  - S (clip on, hang checks bypassed) also PASSES, but is 0.8–2.2 % shorter in chord outboard.
  - **Formally NOT PASS** on freeze blockers (QA-60):
    - r 23.0 N/M;
    - no `reference_build`;
    - `validation/reference/lt120/` absent.
  - Hang: 4.76 mm designed, 4.82 mm built; with the clip on the build is refused at 8.3 mm.
- **D:** waiting for R3.1. Not run.
- **New QA items:** QA-55 (MED), QA-56 (MED), QA-57 (MED), QA-58 (LOW), QA-59 (LOW), QA-60 (MED).

## Contents
- `scripts/c_lt120.py`:
  - builds P and S and cuts them at the 10 table radii;
  - run from the repo root with `.venv/bin/python`, under `setsid nohup`, 163 s;
  - writes its STLs to `/workspace/fansim/qa_r21/c/out/` (box only, not committed).
- `scripts/a_claims.py`: the A claims table. It writes `handoff/2026-10-25_from-qa-21/data/r21-A-claims.csv` and the markdown table.
- `data/c_lt120.json`: C summary and per-radius rows (P and S); `data/r21-C-lt120-cut-check.csv` (same rows); `data/r21-A-claims.csv` (60 A claims).
- Notes: `docs/qa/notes/r21-A-release-claims-audit.md`, `r21-B-validation-draft.md`, `r21-C-lt120-reference-precheck.md`.
- **Deviation:** C's S was built and cut as the full impeller (shipping `build_impeller` minus only the hang checks),
  not blade-only. That makes no difference at the cut radii (all are outside the hub).
