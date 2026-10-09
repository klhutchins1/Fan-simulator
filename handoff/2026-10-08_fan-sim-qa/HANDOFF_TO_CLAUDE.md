# Handoff to Claude: Fan Sim QA results (2026-10-08)

Produced on a separate Linux machine from a **copy** of this repo's working tree, taken 2026-10-08 at 3:27 PM MT. The copy had no `.git` and no edits were made to repo code there. Nothing in here has been merged yet.

## What's in this folder
- `screen_results.zip`: A12x25 BEM multi-fidelity screen. It has 6596 designs, a shortlist, the top-5 STLs with STL QA, cockpit-importable `runs/bem_screen_top5` and `runs/bem_screen_reserve`, and the scripts used. Unzip it and read `screen/README.md` first. The **"Running it on your PC"** section has the exact import and CFD steps. BEM numbers are for ranking only.
- `QA_REVIEW.md`: the full QA review. It is also copied to `docs/QA_REVIEW.md`, and the previous version is kept as `docs/QA_REVIEW.md.bak`. It has repro steps, expected vs actual, and suspected file:line for each issue. Its "How to use this file" section is written for you.
- `BUGS.md`: the running bug log (QA-1..n) referenced by the README and the review.
- `research/`: improvement leads from the arXiv/web scout and the leads tracker, if present.

## Suggested merge order
1. Read `QA_REVIEW.md` and triage the bugs against the current tree. Some may already be fixed by the uncommitted edits in `fansim/centrifugal/isolated.py` and `fansim/cfd/*`, which the QA copy couldn't diff.
2. Fix the confirmed bugs on a branch, with tests.
3. Import the screen runs (copy the `cockpit_import/runs/*` folders into `runs/`) and run CFD per `screen/README.md`. CFD was never run on the QA machine.
4. Don't add the 13 MB zip or `all_designs.jsonl` to git unless Kimball wants them tracked.
