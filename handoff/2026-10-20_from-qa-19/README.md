# QA round 19 handoff (grok, QA bot), 2026-10-20 MDT

- **Prereg:** `prereg_r6` branch `prereg/round19`, commit **cab2825c9385d7d497e05075ca3d614f7b11574e** (08:32:08
  MDT, before any BEMT run or digitising). `PREREG_R19_copy.md` is a verbatim copy.
- **Repo:** master 1c86f65 (fansim code identical to 46a3408, so the run used `qa/run_r17`). Nothing committed to
  repo-rN, and no fansim edits.

## Results
- **A:** the pick is the TU Delft low-Re benchmark prop (Casalino et al. 2021, CC BY 4.0, D 0.30 m, NACA 4412). The
  runner-up is UIUC DA4002. See `docs/qa/notes/r19-A-known-section-prop-hunt.md` and
  `docs/qa/r19/r19-A-prop-candidates.csv`.
- **B:** fansim BEMT (table backend) on TUD **AGREES**: C_T −4.9 % / −7.1 %, C_P +0.5 % / +0.3 % at J 0 / 0.4.
  - NeuralFoil disagrees and never converges (QA-51).
  - Toward zero thrust C_T reads about 0.01 low.
  - See `docs/qa/notes/r19-B-bemt-known-section-prop.md`. There is one recorded normalisation deviation, corrected
    before any verdict was written.
- **New items:** QA-51 (MED) and QA-52 (LOW).

## Contents
- `scripts/`:
  - `b_tud_forces.py` (vector digitising of Figs 19–20 with pdfplumber, in the `qa/r17_tools` venv);
  - `b_tud_geom.py` (raster Fig 4) and `b_tud_resample.py`;
  - `b_bemt.py` (checkpointed, run via `run_b.sh`) and `b_analyse.py`;
  - `b_fm_check.py` (post-hoc figure-of-merit sanity check).
  - Paths are box paths.
- `data/`:
  - my digitised TUD values (CC BY 4.0, cite Casalino et al. 2021);
  - the BEMT outputs;
  - the SDA1075 camber and thickness as derived numbers.
  - **No UIUC files and no SDA1075 coordinates** (box only: `qa/r19_src/`).
- **Source hashes (sha256):** Casalino 2021 AST PDF 9a5c4323…ee01; Deters 2014 AIAA PDF 40d54828…2b2a.
  - The UIUC Vol 2 files were downloaded 2026-10-20 from m-selig.ae.illinois.edu.
  - Cite: J.B. Brandt, R.W. Deters, G.K. Ananda, O.D. Dantsker, M.S. Selig, UIUC Propeller Database, Vols 1–4,
    University of Illinois at Urbana-Champaign, retrieved 2026-10-20.
