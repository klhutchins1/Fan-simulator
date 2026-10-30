# QA round 22 handoff (grok, QA bot), 2026-10-29 MDT: FINAL

- **Prereg:** `prereg_r6` branch `prereg/round22`, commit **715891fd66d460f9610f580610d0dfaf66cf9d4a** (20:24:14
  MDT, before any data). `PREREG_R22_copy.md` is a verbatim copy.
- **Code:** master **b3d5543** (bundle `master_b3d5543.bundle`; the brief's `fansim.bundle` is not on the box), cloned
  to `/workspace/fansim/repo-r22`.
- **Rules kept:**
  - nothing committed to repo-r22, and no fansim edits;
  - no Docker, CFD, OpenFOAM, Assess or Sweep (Preview only);
  - no outside STLs, and the committed lt120 STL was not rebuilt;
  - edits only in `docs/QA_REVIEW.md`, `docs/qa/notes/r22-*`, this folder, and the grok r22 notes in `docs/release/RELEASE_PLAN.md`.

## Results
- **A (UI and bug pass, cockpit headless on :8080):**
  - **verified:** QA-53 (8080 / 30–40 min / "the GitHub URL", interim) and the R1.4 phrase (README:204 plus the rendered
    Stock Expert caption; nothing in Simple).
  - **still open:**
    - UI-26: Gold/hose on the first view, camber/Difficulty after Preview;
    - UI-27: viewer bottom at 957 of 768 px;
    - UI-29: 'Start here' is a 12 px grey caption;
    - QA-40: s3 noise line in Simple;
    - QA-42: "11 g" for both PLA+ and PETG.
  - **Fast pytest:** 1880 passed, **4 failed** (all repeat when run alone), 21 skipped, 23 deselected, 1 xfailed, in 40 min.
- **B (lt120 freeze re-cut): PASS.** r = 23 is N/M and 9/9 PASS.
  - Worst: chord −2.26 %, stagger 0.063°, camber 0.0002.
  - Identical to r21 S.
  - **QA-60 closed:** all 5 sub-items are closed, and the RELEASE_PLAN:81 text is true.
- **C (A0b α bookkeeping, code reading only):** consistent, with no setup bug. U, liftDir and dragDir share one α, and the
  geometry is not rotated. It **does not explain** the A0 C_l −14 %/−44 %. Candidates are listed (convergence, LE
  resolution, far field, wake blocks).
- **D:** waiting for R3.1. Not run.
- **New QA items:**
  - QA-61 (LOW): Assess "~15–30 min" in the cockpit copy against "30–40 min";
  - QA-62 (MED): `validate_lt120.py` is outside the orientation guard;
  - QA-63 (LOW): fuse remaining > peak estimate.
  - QA-41 is re-observed by `test_worker_parent_watch` (2 fails on Linux).

## Contents
- `scripts/b_lt120_recut.py`: cuts the committed STL at the 10 table radii and compares it with the r21 P/S rows. Run
  from the repo root with `.venv/bin/python b_lt120_recut.py <outdir> <r21 c_lt120.json>`; takes 2.7 s.
- `scripts/c_alpha_table.py`: arithmetic on the formulas read from `prop_section_2d.py` (it does not import or run the
  script). Writes `data/r22-C-alpha-bookkeeping.csv`.
- `scripts/a_ui.py`: Playwright checks for UI-26, UI-27, UI-29, R1.4 and the QA-42 Preview. `scripts/a_probe.py`: layout
  probe (visible viewer canvas, controls column). `scripts/a_flowcard.py`: the r14 QA-40 harness with only its path
  assert changed. Run all three against the cockpit on :8080 with `qa/pwvenv/bin/python` (a_flowcard uses the repo
  `.venv`).
- `data/b_lt120_recut.json` and `r22-B-lt120-recut.csv` (B); `r22-C-alpha-bookkeeping.csv` (C); `a_ui.json`,
  `a_probe.json` and `a_flowcard.json` (A). Screenshots, cockpit and pytest logs stay on the box in
  `/workspace/fansim/qa_r22/a/`.
- Notes: `docs/qa/notes/r22-A-ui-bug-pass.md`, `r22-B-lt120-freeze-recut.md`, `r22-C-a0b-alpha-bookkeeping.md`.
- **Deviations:**
  - The bundle name differs (see above).
  - The cockpit was started without `--reload`; that flag is dev mode only, and the port and URL are unaffected.
  - In a_ui.py, the first viewer measurement picked an off-screen VTK canvas (x ≈ −19 400). a_probe.py measured the
    visible one; both are in data/.
  - QA-42's material was switched through trame state, not the dropdown.
  - pytest was one process, not `pytest_chunks.py`, and no OOM occurred.
