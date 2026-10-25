# QA round 20 handoff (grok, QA bot), 2026-10-21 MDT

- **Prereg:** `prereg_r6` branch `prereg/round20`, commit **2c4380d44af3397c08c8ba730c6274b86434357f** (08:38:03
  MDT, before any data). `PREREG_R20_copy.md` is a verbatim copy.
- **Code:** master 027ebcb, which already merges `r33-install-guide` fe899cd although the brief says it is unmerged.
  - fansim, tests and README are identical on both, so master was tested.
  - Kimball's PC working tree is on `r33-install-guide`; that is noted only.
- **Rules kept:** nothing committed to repo-rN, no fansim edits, no Docker, CFD or OpenFOAM.

## Results
- **A:** JSON for the 4 feature designs. All 10 built hangs match r18 to 0.0 mm. Two-stage refusal works as predicted
  (5/10, 6/10), and Export's hub equals the evaluate hub. **QA-43/44/49 are verified fixed.** New: QA-54 (LOW).
- **B:** Ladson TM-4074 reference for rung A0: C_d(0°) 0.00808, C_l(5°) 0.537, C_l(10°) 1.063, with bands inside the
  pass windows.
- **C:** TUD prop build details, each with its figure or table source.
- **D:** the install guide works on clean Linux, with README fixes needed (QA-53, MED). The stop point is
  `git clone <this-repo>`.
- **E:** waiting for R3.1.

## Contents
- `scripts/`: `a_json.py`, `a_r20.py` (run via `run_a.sh`, resumable), `a_analyse.py`, `b_ladson.py`,
  `d_dryrun.py` (run via `run_d.sh`). It creates the throwaway user `fsdry` and a mktemp clone and is resumable. Box
  paths throughout.
- `data/`:
  - `a_r20.jsonl` (30 tasks), `a_summary.json` (gates);
  - `b_ladson.json` (derived reference; the transcribed TM-4074 rows are box-only, in
    `qa/r20_src/tm4074_tables_box_only.json`);
  - `d_steps.jsonl` and `d_logs/` (per-step output).
- **Sources (box only, not committed):**
  - TM-4074 PDF (sha256 8e466706cbdf54b3c778ea2b089c4f52d87686bf7f6b1bd10d224b42c2d06902; NTRS 19880019495;
    GOV_PUBLIC_USE_PERMITTED);
  - TMR NACA 0012 data files (public domain);
  - Casalino et al. 2021 AST (CC BY 4.0, from r19).
- **Box state:** the throwaway user `fsdry` (HOME `/home/fsdry`) and its clone in `/tmp/fsdry_clone.*` are left on
  the box for inspection, with no processes running.
