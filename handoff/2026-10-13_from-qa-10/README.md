# QA rounds 10 + 10b (from QA, 2026-10-13): master a09905a (wrap merge ae3f1c4), clean clone `/workspace/fansim/repo-r10`

This one combined folder holds round 10 (Cursor's Task A) and round 10b (Claude's Tasks B and C).
**Prereg (A, B, C in one commit, before any data):** `26aa359` on branch `prereg/round10` in `/workspace/fansim/qa/prereg_r6`.
File `qa_r10/PREREG_R10.md`, sha256 `d20cdf25f65b36f77de687860fa5052b40216efe993676b19673b1be1b966a04`. A copy is in
`docs/qa/PREREG_R10.md`.

Nothing was committed to repo-r10. No fansim source was edited. No CFD, Docker, OpenFOAM or outside STLs.

## Status per task
- **A, print-ID mark-spec: FINAL. M1, M2 and M3 PASS; M4 is feasible (text yes, Data Matrix marginal at 0.5 mm modules).**
  - The +Z hub top is a flat full-circle ring from r 10 to 21.45 mm. The dummy recess (8 × 3.2 × 0.5 mm at r 11.5–14.7) leaves
    1 solid, a watertight mesh, the cup at K7 and a 3.0 mm roof.
  - Aero ratio is 1.76 %, above the 0.5 % no-CFD threshold.
  - Method change: rasterisation instead of rays (no embree). Note: `docs/qa/notes/print-id-mark-spec-r10.md`.
- **B, wrap confirmation (n = 40): FINAL.**
  - W2, W3, W4 and W5 PASS. W1 and W6 FAIL ×1 on the same featured design, S5_0184 → **QA-34**.
  - 2 designs refused (hang). The fuse fallback fired 0/38 times.
  - S5_0167 built this time, at 8.76 GB.
  - Note: `docs/qa/notes/wrap-confirmation-merged-r10b.md`.
- **C, hang limit and correction: FINAL.** C.1: 19/400 refused, and the refusal matches the 2 mm limit exactly. C.2 PASS on
  49 designs / 105 stations (thin margins). C.3 PASS. C.4: none found. Note: `docs/qa/notes/hang-limit-correction-r10b.md`.
- **D, fuse guard after 27.1: not run.** The patch is not in the bundle.
- **E, near-stall: not done** (optional).

Scripts are in `scripts/`; r9's job/run were adapted, and `hook_b` logs `fuse_many`. Data is in `data/`. Gitignored
(`*.jsonl.gz`): b_results, c2_results, qa10_c1. Not ignored: S5_0184_Pc.stl.gz (1.8 MB), so `git add` it only if wanted.
