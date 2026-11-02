# QA round 24 handoff (grok, QA bot), 2026-11-01 MST: FINAL

**Setup**
- **Prereg:** `prereg_r6`, branch `prereg/round24`, commit **88c4e798fcadd3d79e58f25be306d50b68ab35be** (12:21:40 MST, before any data).
  - `PREREG_R24_copy.md` is a verbatim copy; `cmp` matches `git show 88c4e79:qa_r24/PREREG_R24.md`.
- **Code:** master **23831da**, from `master_23831da.bundle`, cloned to `/workspace/fansim/repo-r24`. `uv sync --extra dev` was run.
- **Rules kept:**
  - nothing was committed to repo-r24, and no fansim source was edited;
  - no Docker, CFD, OpenFOAM, Assess, Sweep or Optimize run;
  - in the cockpit, only Preview was clicked;
  - no outside data or STLs were used;
  - edits are only in `docs/QA_REVIEW.md`, `docs/qa/notes/r24-*`, `docs/qa/patches/r24-*`, this folder, and the grok r24 lines in `docs/release/RELEASE_PLAN.md`.
  - No images were generated this round, so the generator was not needed.

## Results
- **A: 16/16 items are still open; none verified.**
  - Items: UI-26, UI-27, UI-29, UI-31…UI-38, QA-40, QA-42, QA-61, QA-62 and QA-63.
  - The cockpit, scripts and control images are byte-identical to 3b92eea.
  - UI-38 correction: the Print-material caption already says Optimize uses it.
  - Fast suite: 1883 passed, 4 failed. The failures are the same as r22: QA-62, QA-63 and QA-41 × 2.
- **B: needs grok's proposed wording.**
  - A12x25: −0.5 % at 0 Pa.
  - FAN-01: +2.6 % at 7 Pa (P/Pmax 0.028).
  - lt120: +8.1 % mean (+9.5 % on the 6.2 mm mesh) at 6.85 Pa (P/Pmax 0.20).
  - lt120 fails both "near free air" and "within 8 %". "Within 10 % … lt120 at its lowest measured load (6.85 Pa)" holds.
  - Caveat: tip gap 1.0 mm gives +13.0 %.
- **C: PARTIAL.** K1 is visible only in the reject message. A converged=False score shows nothing. The new item is QA-65 (MED). There is a patch proposal.
- **D: still waiting** (R3.1, R1.10).

## Contents
- **`scripts/`:**
  - `a_ui.py`, `a_probe.py`, `a_flowcard.py`: r22 harnesses, re-pointed at repo-r24, with the Chrome path set.
  - `a_tooltips.py`: UI-32, UI-33, UI-34, UI-36 and UI-38 hovers and text.
  - `scan_controls.py`, `build_inventory.py`: tooltip inventory.
  - `b_qa64_check.py`: B.
  - `c_k1_visibility.py`: C pure calls.
  - The r-tooltip `range_check.py` (in `handoff/2026-10-31_from-qa-tooltips/scripts/`) was run as-is on repo-r24.
- **`data/`:** the JSON outputs of the above, plus `range_check_r24.json` and `inventory.csv`.
- **`screens/`:** Fan first-view screenshots at 1366×768 and 1920×1080 (Simple and Expert), and Preview with PLA+ and PETG.
- **Patch:** `docs/qa/patches/r24-C-k1-visible.patch` (proposal only).

## Placement (uncommitted)
1. Unzip `r24_out.zip` into the repo root, `T:\Projects\Fan Simulator`. The paths inside are repo-relative and overwrite only:
   - `docs/QA_REVIEW.md` (13 rows updated, plus the Round 24 section with QA-65);
   - `docs/release/RELEASE_PLAN.md` (3 grok r24 lines).
2. Everything else is new:
   - `docs/qa/notes/r24-{A,B,C}-*.md`;
   - `docs/qa/patches/r24-C-k1-visible.patch`;
   - `handoff/2026-11-01_from-qa-24/`.
3. These are built on 23831da. If master has moved, merge `QA_REVIEW.md` and `RELEASE_PLAN.md` by hand rather than overwriting them.
4. Nothing is committed. The patch is a proposal; apply it with `git apply docs/qa/patches/r24-C-k1-visible.patch` only if you choose to.
