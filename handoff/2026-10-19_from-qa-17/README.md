# QA round 17 handoff (grok, QA bot), 2026-10-19 MDT

- **Repo:** master 46a3408, run clone `/workspace/fansim/qa/run_r17` (box). Nothing committed to any repo-rN, and no
  fansim source edited.
- **Prereg:** `prereg_r6` branch `prereg/round17`, commit **a212b2962968319c8591110d48f593ee16e41bdb**
  (12:34:27 MDT, before any data). `PREREG_R17_copy.md` is a verbatim copy, sha256 b4cc7f0c…ff77ed.

## Results
- **A (R2.2a):** `docs/qa/notes/r17-A-reference-polars.md`.
  - Section: fansim NACA 4406, n = 60, closed TE.
  - At Re 8e4, α 4°: **CERTAIN**, C_l 0.855 [0.847, 0.863], C_d 0.0201 [0.0199, 0.0204].
  - Re 1.2e5: CERTAIN. Re 6e4: UNUSABLE (fails the anchor).
  - NASA TM-4062 E387 anchor: the Ncrit-9 tools are about 8 % high on C_l and −10 % on C_d at 1e5. Ncrit 5 fails C_d.
- **B (R2.3 / R2.5):** `docs/qa/notes/r17-B-digitised-cror-centrifugal.md`.
  - CC BY 4.0, confirmed in both PDFs. B-cal, B-rep (63/63) and B-text all PASS.
  - Shigemitsu: only the total is measured.
  - EPJ: 3 speeds, never reaches 0 Pa.
- **C (R1.3/1.7/1.8):** `docs/qa/notes/r17-C-hang-refusals.md`.
  - r14 P0 bounds with both fixes: **2.0 % refused** (Wilson 0.9–4.3 %), PASS.
  - 300 r16 designs: 24.3 % / 42.3 % / 10.7 % / 19.3 %.
  - The 1.75× rule misses S2_0269 (QA-46).
- **D (R3.1): WAITING.** R3.1 hasn't landed, nothing was run.
- **New items:** QA-46 (MED), QA-47 (LOW), QA-48 (LOW). See `docs/QA_REVIEW.md` § Round 17.

## Contents
- `scripts/`: every script used. Paths are box paths (`/workspace/fansim/qa/...`); the source PDFs live in
  `qa/r17_src/` on the box and are **not** included.
  - XFOIL 6.99 was built from source at `qa/xfoil_build`. NeuralFoil 0.3.3 is `xxxlarge`.
  - Long jobs ran under setsid nohup with checkpoint and resume (`run_*.sh`).
- `data/A`: raw polars (jsonl), the summary, and the NeuralFoil resolution check.
- `data/B`: method-1 detections, method-2 overlay reads, and the summary (calibration residuals, licence, checks).
- `data/C`: per-design rows (analytic, built at the export hub, r14 P0/guided) and the summaries.
  - `c_r14_ruleI.json` is the report-only, post-hoc sweep_tip bound check.
- **Source hashes (sha256):**
  - Shigemitsu 2018: 1de8a870…a98;
  - EPJ WoC 180:02023: f7065ec8…1e (fetched via the Wayback copy, because the publisher has a captcha);
  - NASA TM-4062: public domain.
