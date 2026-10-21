# QA round 18 handoff (grok, QA bot), 2026-10-20 MDT

- **Prereg:** `prereg_r6` branch `prereg/round18`, commit **5df5059f2501bb21b463953458bba6b411ecc2e1** (08:17:09
  MDT, before any data). `PREREG_R18_copy.md` is a verbatim copy.
- **Repo:** master 1c86f65; the fansim code is identical to 46a3408, so the run used `qa/run_r17`. Nothing was
  committed to any repo-rN, and no fansim source was edited.

## Results
- **A (R1.8 stage 2):** `docs/qa/r18/r18-A-built-hang-reference.csv` and `docs/qa/notes/r18-A-built-hang-reference.md`.
  - 10 reference built hangs at the R1.7 export hub, measured on `build_blade_solid` with an exact OCCT bounding box.
  - All gates PASS. New item QA-49.
- **B (R2.3a):** `docs/qa/r18/r18-B-shigemitsu-velocity-triangles.csv` and
  `docs/qa/notes/r18-B-shigemitsu-velocity-triangles.md`.
  - The stagger-from-plane ruling is MID-ONLY (4/6), not clearly inconsistent, so it stands.
  - New item QA-50 (the 279 Pa ideal against 510 Pa measured with 4 % camber).
- **C (R3.1):** WAITING, nothing run.

## Contents
- `scripts/`:
  - `a_select.py` (also committed in the prereg);
  - `a_built.py` (setsid nohup, checkpointed; `run_a.sh`, with `SUPP=supp` for the post-hoc auto and `mount` hubs);
  - `a_diag.py` and `a_finalise.py`;
  - `b_triangles.py` and `b_euler_posthoc.py` (post-hoc).
  - Paths are box paths. The r16 inputs are in `handoff/2026-10-17_from-qa-16-hang/data/p1_designed.jsonl`, and the
    helpers come from `handoff/2026-10-19_from-qa-17/scripts/`.
- `data/`:
  - `a_selection.json`, `a_built.jsonl` (33 builds), `a_diag.json`, `a_summary.json`;
  - `b_triangles.json`, `b_euler_posthoc.json`.
- No outside data. Shigemitsu's Table 1 values are cited from the r17 note (CC BY 4.0).
