# QA round 9 (from QA, 2026-10-12): branch `cylinder-sections` @ 7b02bed (master 2ce35b6), clean clone `/workspace/fansim/repo-r9`

**Prereg (A–D in one commit, before any data):** `a0260c0` on branch `prereg/round9` in `/workspace/fansim/qa/prereg_r6`.
File `qa_r9/PREREG_R9.md`, sha256 `eebafe83287c717f41910054f381ccaaedf702347ca191579df54323925fa153`. Amendment A1 is
`9438a9b`: the C-gate is 3.5 GB, written before any C data. Copies are in `docs/qa/`.

Nothing was committed to repo-r9 and no fansim source was edited. Outside STLs were kept in `/tmp/qa9_ext` only.

## Status per task
- **A, wrapped-builder robustness: FINAL, truncated at 66/150 by user decision (box suspends).**
  - W2, W4 (13/13 cup builds) and W5 PASS.
  - W1 FAIL ×1: OOM-like SIGKILL at 7.7 GB on featured S5_0167.
  - W3 FAIL ×1: shrouded S7_0160, ~1.6× in CPU time, 3.8× wall under contention.
  - QA-33: the direction proof can't tell on 30/65 wrapped vs 24/66 planar builds.
  - Note: `docs/qa/notes/wrapped-builder-robustness-r9.md`.
- **B, built vs sliders (wrapped): V1 not confirmed as registered.**
  - Off-clip: 50/52 clean. The 2 exceptions are Stock v3's inner stations, camber −0.0063/−0.0054, possibly the
    NACA bias applied to plate sections.
  - Clip-reached: chord fixed (QA-30 verified), but camber is 0.005–0.011 low and stagger up to −1.1° → new QA-32.
  - Population: 20 % hang below the hub face; ~15 % have a clip-reached station.
  - Note: `docs/qa/notes/built-vs-sliders-wrapped-r9.md`.
- **C, Stock surface fit: FAIL (2/3).** Mean 0.358 mm and outer 0.205 mm both PASS, but the V2 sections fail at
  r/R 0.6 and 0.7. The proposal YAML is in `docs/qa/stock_fit/`. Note: `docs/qa/notes/stock-surface-fit-r9.md`.
- **D, external STLs, radial-led rule: FAIL as registered (7/13 wrong vs truth), and not a valid confirmation.**
  - All 7 disagree on ω only, and the registered truth cue (LE bluntness / tip lead) is unreliable on print-truncated
    plate blades.
  - The two readers never disagreed. Coverage 20/28.
  - Note: `docs/qa/notes/external-stl-radial-led-r9.md`.
- **E, shrouded fuse memory:** 5/12 shrouded builds (all with 9 or 11 blades) grow past the guard's 1.15 × estimate;
  unshrouded 15/15 stay within it.
  - The ring adds only 4 faces at the call, so a per-ring-face rate can't be used.
  - Constant: LOO 0.30 GB. Ring height: no signal.
  - Best fit (post hoc): +66 KiB per *blade* face. Note: `docs/qa/notes/shroud-fuse-memory-r9.md`.
- **F, near-stall flag: not done.** It is optional and was not cheap enough this round.
