# QA → Cursor/Claude, round 12 (2026-10-14), master 143d5a8

Prereg `42004b3fa85fbace378b4671a8eeaa2cd1b4778d` (qa/prereg_r6, branch prereg/round12, A–E in one commit, before any data).
Run clone: `/workspace/fansim/qa/run_r12` (local clone of repo-r13 @ 143d5a8). Nothing is committed to repo-r13. Python is repo-r9 .venv
with PYTHONPATH=run clone. No CFD, Docker, loft or glyph work. Round 11 skipped; 27.1.patch not applied.

| task | status | result |
|---|---|---|
| A QA-34 strip | **FINAL** | **F0 PASS, F1 PASS.** S5_0184 + S5_0080 + S5_0242: 1 watertight body each, 0 faces < 1e-9, B-rep 1 solid. `docs/qa/notes/qa-34-strip-r12.md` |
| B 27.1 remaining | **FINAL** | **FAIL 1/26.** S7_0172_twin (open, 11 blades) at 1.032× the ask, reproduced 3/3. Shrouded ≤ 0.80×. S7_0097 ±twin now refused (hang). → QA-35. `docs/qa/notes/fuse-remaining-r12.md` |
| C 28.2 print-id | **FINAL** | **P0–P4 PASS** (SB862; K7 identical to r10). → QA-37 (LOW, orphan STL from an interrupted export). `docs/qa/notes/print-id-export-r12.md` |
| D PLA+ picker | **FINAL** | Chip, Assess stamp and optimizer follow PLA+. **Preview grams and the Export README/temps/sidecar/registry still say PETG**, because of `active_spec().material`. → QA-36. `docs/qa/notes/material-picker-r12.md` |
| E UI tests | **FINAL** (proposal) | 4 tests in `tests/`: 2 FAIL on HEAD as intended (QA-36), 2 PASS. `docs/qa/notes/ui-regression-r12.md` |

Scripts: `scripts/run_a.py`, `run_b.py` (r9 run_e selection verbatim), `analyse_b.py`, `repeat_b.py` (unregistered), `cd_cockpit.py`,
`c_check.py`, `chain_ab.sh`, `chain_cd.sh`, `hook_b/` (copy of r10). Data in `data/`.
