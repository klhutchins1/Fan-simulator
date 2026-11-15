# From QA (grok): round 25b, a light re-check of master 0635a18 (2026-11-02)

**Result:**
- UI-31 and QA-62 are **verified** on master 0635a18.
- **R1.11 is not closable**: QA-66 is still open (0 of 3 rules pass), and the CLI behaviour test is still guard-only (the r25-A patch is still needed).
- **QA-65 is not on master.** The patch still applies; "landed in 9d0118f" is incorrect.
- "Drop dead tooltip" changes no UI-3x item.
- No new IDs.

Details: `docs/qa/notes/r25b-master-0635a18-recheck.md`, and the "Round 25b" section at the end of `docs/QA_REVIEW.md`.

## Placement: MERGE, do not overwrite

- **`docs/QA_REVIEW.md`:** the real file in Kimball's repo already holds r25 plus Cursor's Next-round edit. **Merge into it; do not overwrite it.** The r25b changes are:
  1. a " r25b: …" suffix appended to the Status cell of 13 table rows: UI-26, 27, 29, 31–38, QA-40, QA-42;
  2. a new "## Round 25b …" section at the end of the file (the same text as `scripts/round25b_section.md`).
  - The shipped file is 0635a18's copy plus my r25 diff (applied cleanly) plus r25b. If your copy matches that base, a straight diff shows only the r25b changes. `scripts/apply_qa_review_r25b.py <QA_REVIEW.md> scripts/round25b_section.md` reproduces them on any copy.
- **`docs/release/RELEASE_PLAN.md`:** grok-lane lines only. The shipped file is 0635a18 plus the three r25 grok lines (r25 C, r25 B, r25 A), which are probably already in your copy, plus **two new r25b lines**. Merge only the two new lines:
  - under R1.2 / QA-65, after the "grok r25 B" line: `- grok r25b (2026-11-02, …): **still not on master 0635a18** …`
  - under R1.11, after the "grok r25 A" line: `- grok r25b (2026-11-02, …): on master 0635a18 UI-31 and QA-62 **verified**. **Not closable:** …`
  - R1.11's `Status: done 23704f5` was **not** changed; that is Cursor's and Claude's lane. QA's verdict is "not closable".
- **New files** (copy as-is):
  - `docs/qa/notes/r25b-master-0635a18-recheck.md`;
  - this folder.
  - The r25 patches cited (`docs/qa/patches/r25-A-…`, `r25-B-…`, `r24-C-…`) are already placed from r25 and are not repeated here.

## Contents

- `PREREG_R25B.md`: copy of the prereg, `prereg/round25b` d207af8, committed 2026-11-02 16:22:37 MST before any data.
- `scripts/`:
  - `run_a.sh`: the r25 runner, pointed at `qa_r25b`;
  - the r25 harness scripts: `a_ui`, `a_probe`, `a_tooltips`, `a_flowcard`, `scan_controls`, `build_inventory`, `range_check`, `a_ui31_cli`, `b_qa65_review`;
  - the QA_REVIEW updater and section.
- `data/master0635a18/`: harness and targeted-test output on 0635a18. Screenshots stay on the QA box: `/workspace/fansim/qa_r25b/screens/master0635a18/`.
- `data/`:
  - the UI-31 CLI seam check;
  - the r25-A patch scratch run (7 passed);
  - the QA-65 review, unpatched and patched;
  - the score_caption scratch run (11 passed).

## Rules kept

- No CFD, Docker, OpenFOAM, Assess, Sweep or Optimize run.
- No full fast suite; the QA-67 smoke test was skipped.
- No source edits, and no commits to repo clones. The only commit is the prereg in the QA prereg repo.
- Nothing was done on Kimball's PC.
