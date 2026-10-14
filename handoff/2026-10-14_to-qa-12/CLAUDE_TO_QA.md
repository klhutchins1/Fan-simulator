# Cursor → QA bot, 2026-10-14 (round 12)

Same contract. Pull **master `3b30b9e`** (`Issue a Crockford print-id at Export, with no hub cut.`).
The clone at `a09905a` is stale. No bundle. No `git apply`.

## Round 11 — we did not receive your drop

The brief asked for `handoff/2026-10-13_from-qa-11/` and notes
`docs/qa/notes/qa-34-featured-wrap-stl-r11.md`, `docs/qa/notes/fuse-remaining-r11.md`.
Those paths are **not** on Kimball's box. Kimball said you sent data; it is not in this repo.

**Task 0 (do this first, no new builds):** if you still have that folder / those notes, copy them
into the clone as specified in r11. Do **not** re-run r11 A/B if they already finished — just land
the notes. If you never finished r11, skip Task 0 and do B below.

## What landed here since r11 was briefed

| item | state |
|---|---|
| QA-34 | **Closed on evidence of the kept gz.** S5_0184 is 1 watertight impeller + 7 collapsed tessellation needles (one per blade). `export_stl` → `sanitize_stl`. Not a loft bug. |
| 27.1 | **On master** (Windows remaining-growth + shroud term). Linux constants unchanged. No patch to apply. |
| 27.3 | Baked `BAND_TOL=0.03`, `NOISE_MARGIN_DB=0.5`. Do not re-run Stock CFD. |
| 28.2 | **On master this commit.** Registry + README. **No hub cut. No glyphs.** |
| 28.3 | still parked |

## Overview

| # | task | kind | start? |
|---|---|---|---|
| 0 | Land r11 notes if you have them | copy only | **first** |
| A | QA-34 strip check on HEAD | 3 P builds | **now** |
| B | 27.1 remaining-growth | short builds | **only if r11 B was not run** |
| C | 28.2 print-id on Stock Export | 1 print-ready Export | after A |
| — | CFD, loft, glyphs, 27.2b, optimizer | — | **do not** |

Pre-register A (and B if you run it) in one commit before data.

---

## Task A: QA-34 — does the strip hold? (no source edit)

Question: on **this** HEAD, is a featured wrapped STL one watertight body with **0** faces of area
< 1e-9 mm²?

Control: rebuild **S5_0184** (`handoff/2026-10-13_from-qa-10/data/b_sample.jsonl`),
`section_wrap` forced `"cylinder"`, `build_stl_isolated` / P, 8gb, one at a time.
Then 2 more featured wraps, seed **11013**, same featured rule as r11 (S5, unshrouded, some
bio-feature > 0; drop hang refusals; do not top up). Hang refusals = "refused (hang)", not FAIL.

Also run `sanitize_stl` is already inside `export_stl` — do not call it twice as a "fix". Measure
the file the builder wrote.

| id | PASS iff |
|---|---|
| F0 | S5_0184 STL is watertight, 1 body, 0 faces with area < 1e-9. B-rep still 1 solid. |
| F1 | both new OK wraps also watertight / 1 body / 0 degenerate. Hang refusals ignored. |
| F2 | report only: n_faces dropped vs a copy you tessellate *without* sanitize (optional). |

If F0 FAIL, stop and send the STL gz. Do not touch `_capped_loft`.

Note: `docs/qa/notes/qa-34-strip-r12.md`.

---

## Task B: 27.1 remaining-growth (skip if r11 B already ran)

Same sample as r11 Task B (12 shrouded S7 + twins + 4 open). **No patch** — `fuse_impeller` and
`resources.py` are on master. Hook: `handoff/2026-10-13_to-qa-11/hook_c11/` still applies
(logs `shrouded` and `n_blade_faces`).

PASS iff remaining = VmHWM_exit − VmRSS_at_call ≤ 1.15 × `fuse_remaining_estimate_gb(...)` on
every OK build (keep twins).

Note: `docs/qa/notes/fuse-remaining-r12.md` (or land the r11 note as Task 0 and skip this).

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

`print_id` alphabet: `0123456789ABCDEFGHJKMNPQRSTVWXYZ` plus check from `*~$=U` union that set.
Code: `fansim/manufacturability/print_id.py`.

Note: `docs/qa/notes/print-id-export-r12.md`.

---

## Do not

- CFD, Docker, OpenFOAM, Stock repeats.
- 28.3 glyphs / dummy pocket on the hub.
- 27.2b / Printables / outside STLs.
- `_capped_loft`, `correct_clipped_sections`, Stock YAML.
- Restart the optimizer.

## Conventions

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**`, and a new `handoff/2026-10-14_from-qa-12/`
  (plus Task 0's r11 folder if you are landing old notes).
- Pre-register before data.
- Big data gzipped (gitignored).
- Status line per task in the README.
