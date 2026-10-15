# QA → Cursor/Claude, round 13 (2026-10-14), master 143d5a8

Prereg `02584e67482d8abf8a7874695d6be9e7a6d49e35` (qa/prereg_r6, branch prereg/round13, A–D, written after the r12 return and before any r13 data).
Run clone `/workspace/fansim/qa/run_r13`. Cockpit :8080 driven headless (Playwright + Chrome 154, 1366×768).

| task | status | result |
|---|---|---|
| A Simple vs Expert | **FINAL** | **S0–S3 PASS.** S4: the Simple scatter starts at y=652 of 768, so only its title is above the fold → QA-38 (LOW). `docs/qa/notes/simple-mode-24-2-r13.md` |
| B duplicates | **FINAL** | 10-row table: 2 hide, 1 hide-after-Preview, 3 needs Kimball copy. No cached CFD Assess on disk. `docs/qa/notes/duplicate-after-run-r13.md` |
| C chunked pytest RSS | **FINAL** | **M0 PASS** (1777 passed, 0 failed), **M1 PASS** (no OOM in the run window), M2 peaks 5.1 / 2.9 / 6.9 GB per chunk (was 8.2 GB single process), 45 min active wall time. `docs/qa/notes/pytest-chunks-r13.md` |
| D other-tab captions | **FINAL** | None of Mixed/Prop/Volute/CROR respects ui_mode. 13 Expert-only candidates listed with file:line. `docs/qa/notes/other-tab-captions-r13.md` |
