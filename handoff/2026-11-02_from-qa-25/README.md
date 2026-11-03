# QA bot (grok) → Cursor: round 25 results, 2026-11-02 (MST)

**Brief:** `CLAUDE_TO_QA_r25_DRAFT_copy.md` is a verbatim copy of Cursor's **uncommitted draft** brief. It was left untracked; it is kept here for the record.

**Built against master 9d0118f.** Task A ran on the **unmerged** branch `r111-hide-surrogate` @237a094.

**Prereg:** `PREREG_R25_copy.md`, committed as `prereg/round25` b7e7574e before any data.

## Placement (read first)

Unzip at the repo root. Every path is repo-relative.

**`docs/QA_REVIEW.md` must be MERGED, not overwritten.** Kimball's working copy has Cursor's uncommitted "▶ Next round" edit, the round 25 queue, and this zip's copy does not. To merge:
1. Keep the real file's "Next round" section exactly as it is.
2. Bring over from this zip:
   - the ` r25: …` text appended to the **Status** cell of rows UI-26, 27, 29, 31–38 and QA-40, 42;
   - the new `## Round 25 (2026-11-02) …` section at the end of the file.
3. For example: `git diff 9d0118f -- docs/QA_REVIEW.md` in a clean 9d0118f checkout with this zip applied, then `git apply` that diff onto the real copy. Both hunks sit away from the Next-round block. If it doesn't apply, paste the two pieces by hand.

**`docs/release/RELEASE_PLAN.md`:** three added grok-lane lines only:
- under lt120: r25 C;
- under R1.2 / QA-65: r25 B;
- under R1.11: r25 A.

It is safe to overwrite only if the real copy equals 9d0118f; otherwise merge the same way.

**New files:**
- `docs/qa/notes/r25-A-r111-branch-check.md`, `r25-B-qa65-adopted-review.md`, `r25-C-qa64-strings.md`;
- `docs/qa/patches/r25-A-r111-cli-behaviour-test.patch`, which applies to **237a094**;
- `docs/qa/patches/r25-B-qa65-test-and-trials.patch`, which applies to 9d0118f, alone or after `r24-C-k1-visible.patch`;
- this folder.

## Results

| task | result |
|---|---|
| A | UI-31 and QA-62: **fixed on branch (pending merge)**, verified on unmerged branch r111-hide-surrogate @237a094, not on master; **master still open**. R1.11 is not closable yet: the CLI test is guard-only and **QA-66 (MED)** is new. Every other UI/QA item is still open on both heads |
| B | **holes**. 9d0118f "adopts" QA-65 on the board only; the code is not applied. The behaviour is correct (only `converged is False` warns), but Optimize trials don't carry the flag and there is no test. See the add-on patch |
| C | **still live**: both audit lines still say "near free air … within 8 %" (R1.10 not landed) |
| D | waiting (R3.1, R1.10) |
| suite | master 9d0118f: 4 failed (QA-62, QA-63, QA-41 ×2), 1883 passed. Branch 237a094: 3 failed (QA-63, QA-41 ×2), 1889 passed. New **QA-67 (LOW)**: an unseeded random-geometry smoke test spent ~25 min in an OCC loft on the branch run |

## Contents

- `scripts/`: the harnesses.
  - `run_a.sh <name> <repo> <port>` drives the cockpit headless and runs the r24 harnesses (a_ui, a_probe, a_tooltips plus a UI-31 count, a_flowcard, scan_controls, build_inventory, range_check), followed by the targeted tests.
  - `a_ui31_cli.py` checks the argv seam and CLI guard.
  - `b_qa65_review.py` makes the pure calls on a scratch master + patch.
- `data/branch_237a094/` and `data/master_9d0118f/`: the per-head harness outputs.
- `data/a_ui31_cli_*.json`, `data/b_qa65_review.json`, `data/c_grep_raw.txt`.
- `screens_branch_237a094/`: harness screenshots, not control images.
- `fast_suite_9d0118f.txt` and `fast_suite_237a094.txt`: summary lines.

No CFD, Docker, OpenFOAM, Assess, Sweep or Optimize was run, and no fansim source was edited. No outside sources or STLs were used.
