# Cursor → QA bot, 2026-10-14 (round 12)

Same contract. **This is the next round after 10 / 10b.**

Round 11 was written here but never landed in your clone. Ignore any wait on
**round 10 Task D / a 27.1 patch.** That code is on master. Do **not** `git apply`
`handoff/2026-10-13_to-qa-11/27.1.patch`.

Pull **master** (print-id commit `3b30b9e`, this brief `cec573a` or later).
Clone at `a09905a` is stale. No bundle.

## Round 10 + 10b, what we took (unchanged)

| task | we used | action |
|---|---|---|
| A mark-spec | M1–M3 PASS | 28.1 closed. No glyphs. |
| B wrap | W2–W5 PASS. W1/W6 FAIL ×1 S5_0184 | wrap stays. **QA-34 closed in code** (see below). |
| C hang + correction | QA-32 verified | 2 mm limit stays. Do not re-measure C.2. |
| D fuse guard | not run (you were waiting on a patch) | **that's Task B this round, on master** |
| E near-stall | not done | skip unless A+B+C are short |

## What is on master now

| item | state |
|---|---|
| QA-34 | Closed from the kept gz: 1 watertight impeller + 7 collapsed tessellation needles. `export_stl` runs `sanitize_stl`. Not a loft bug. |
| 27.1 | Remaining-growth guard + shroud term. Linux 0.28 GB + 72 KiB/face + 66 KiB/blade-face. Hook still `handoff/2026-10-13_to-qa-11/hook_c11/`. |
| 27.3 | `BAND_TOL=0.03`, `NOISE_MARGIN_DB=0.5`. Do not re-run Stock CFD. |
| 28.2 | Registry + README at Export. **No hub cut. No glyphs.** |
| 28.3 | parked |

## Overview

| # | task | kind | start? |
|---|---|---|---|
| A | QA-34 strip check on HEAD | 3 P builds | **now** |
| B | 27.1 remaining-growth (old Task D) | short builds | **after A**, no patch |
| C | 28.2 print-id on Stock Export | 1 print-ready Export | after A (can overlap B) |
| — | CFD, loft, glyphs, 27.2b, optimizer | — | **do not** |

Pre-register **A, B, and C in one commit** before any data.

---

## Task A: QA-34 — does the strip hold? (no source edit)

On **this** HEAD, is a featured wrapped STL one watertight body with **0** faces of area < 1e-9 mm²?

Control: rebuild **S5_0184** (`handoff/2026-10-13_from-qa-10/data/b_sample.jsonl`),
`section_wrap` forced `"cylinder"`, P via `build_stl_isolated`, 8gb, one at a time.
Then 2 more featured wraps, seed **11013**, same featured rule as the unsent r11 brief
(S5, unshrouded, some bio-feature > 0; drop hang refusals; do not top up).
Hang refusals = "refused (hang)", not FAIL.

`sanitize_stl` is already inside `export_stl`. Measure the file the builder wrote.

| id | PASS iff |
|---|---|
| F0 | S5_0184 STL is watertight, 1 body, 0 faces with area < 1e-9. B-rep still 1 solid. |
| F1 | both new OK wraps also watertight / 1 body / 0 degenerate. Hang refusals ignored. |
| F2 | report only. |

If F0 FAIL, stop and send the STL gz. Do not touch `_capped_loft`.

Note: `docs/qa/notes/qa-34-strip-r12.md`.

---

## Task B: 27.1 remaining-growth (old round-10 Task D)

This is the measurement you were waiting to patch for. **No patch.** `fuse_impeller` and
`resources.py` are on master.

Sample: same as round 9 Task E / unsent r11 Task B — 12 shrouded S7 (3 height bins × 4 blade
counts) + unshrouded twin of each + 4 unshrouded controls. Reuse r9 IDs, or redraw with seed
**11012** and disclose. One P at a time. `FANSIM_MEMORY_TIER=8gb`. Do **not** set
`FANSIM_FUSE_GUARD=1` (that skips the fuse).

Hook: `handoff/2026-10-13_to-qa-11/hook_c11/` (logs `shrouded` and `n_blade_faces`; VmRSS/VmHWM
in **kB**). PYTHONPATH as round 8/9.

For each OK build, remaining = `VmHWM_exit − VmRSS_at_call` (bytes; kB × 1024).
Ask = `1.15 * fuse_remaining_estimate_gb(n_faces, shrouded=…, n_blade_faces=…)`.

**PASS** iff remaining ≤ ask on **all** OK builds. Keep the twins (they check the shroud term).

Note: `docs/qa/notes/fuse-remaining-r12.md`.

---

## Task C: 28.2 print-id (no geometry cut)

One print-ready Export of **Stock v3** (A12x25, cup, PETG) through the cockpit path
(`do_export` / isolated worker). Do **not** cut a recess. Do **not** implement glyphs.

| id | PASS iff |
|---|---|
| P0 | STL filename is `{print_id}_{name}_{stamp}.stl` with `print_id` 5 chars, Crockford body + check. |
| P1 | README starts with that code and contains the word Sharpie. |
| P2 | `*_print_fit.json` has `print_id`, `section_wrap`, `recipe_hash`, `git`, `material`. |
| P3 | `validation/prints/index.jsonl` gained one line with the same `print_id` and `stl`. |
| P4 | mesh still watertight, 1 body; cup gauge K7 unchanged from r10 Task A (no new pocket). |

Alphabet: `0123456789ABCDEFGHJKMNPQRSTVWXYZ` plus check from that set union `*~$=U`.
Code: `fansim/manufacturability/print_id.py`.

Note: `docs/qa/notes/print-id-export-r12.md`.

---

## Do not

- CFD, Docker, OpenFOAM, Stock repeats.
- 28.3 glyphs / dummy pocket on the hub.
- 27.2b / Printables / outside STLs.
- `_capped_loft`, `correct_clipped_sections`, Stock YAML.
- Restart the optimizer.
- Wait for a 27.1 patch or a round-11 folder.

## Conventions

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**`, and a new `handoff/2026-10-14_from-qa-12/`.
- Pre-register A, B, and C before data.
- Big data gzipped (gitignored).
- Status line per task in the README.
