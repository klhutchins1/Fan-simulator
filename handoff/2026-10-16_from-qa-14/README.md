# QA round 14 (grok), master 9562574, 2026-10-16/17

- Prereg: `prereg_r6` branch `prereg/round14`, commit `586bbe908636fc92c8874372062f3e5628910f1a`.
  The file is `qa_r14/PREREG_R14.md`, sha256 `0ce049ca79ffba6c0667a9529de93236af4c552b89facfde9342d0cda1f16adc`,
  committed 14:34 MDT before any data.
- Run clone: `/workspace/fansim/qa/run_r14` (9562574); Python: repo-r9 `.venv`; cache `/workspace/fansim/qa/r14_cache`.
- Nothing in the fansim source was edited. No CFD, Docker or outside STLs. Nothing was run on Kimball's PC.

| task | result | note |
|---|---|---|
| A1 QA-35 | **PASS**: worst open 0.85, twin S7_0172 0.826 (was 1.03) | `docs/qa/notes/reverify-r14.md` |
| A2a QA-36 tests | **PASS**: 6/6 | same |
| A2b1 PLA+ Preview→Export | Export **PASS** (README, temps, print_fit, index). Preview line names no material → FAIL as registered → QA-42 | same |
| A2b2 switch during Preview | **INCONCLUSIVE** (11 g for both materials) | same |
| A3 QA-37 | **PASS** (worker gone in 0.75 s; .partial only). An unreaped (zombie) launcher keeps the worker alive → QA-41 | same |
| A4 27.3b Simple card | **FAIL**: "No Stock comparison for noise." shows in Simple mode (s3) → QA-40 | same |
| B maths | B1(d) FAIL → QA-39 (string sort of time dirs); B2, B3 pass; B4c estimator bias; B5 explained 10/10 | `docs/qa/notes/maths-check-r14.md` |
| C 27.7 space | C1 bounds miss Stock; C2 3.3 % refused; C3 FAIL 3/80 as registered (mostly radius basis); C4 bounds proposed, 4.3 % refused | `docs/qa/notes/optimizer-space-wrap-r14.md` |
| D QA-12 data | e387 tables are shaped, not measured; NASA TM-4062 is best (public use) | `docs/qa/notes/prop-ct0-data-sources.md` |
| F 27.3d margins | F1 fails on rounding; F2/F3 numbers (v3 only, superseded by v4) | `docs/qa/notes/flow-margins-two-run-r14.md` |
| E | not done (optional) | – |

Folders:
- `scripts/` holds the harnesses. Re-run with `PYTHONPATH=<run clone>` and the repo-r9 venv.
- `data/` holds the raw results.
- `screens/` holds the browser screenshots from A2b.
- Two A2b/A3 runs were made:
  - `a2b_a3_run1.*`: 30 s UI timeouts made the "switch during Preview" happen after the Preview finished, and the
    launcher was left a zombie;
  - `a2b_a3.*` (run 2) is the one reported.
