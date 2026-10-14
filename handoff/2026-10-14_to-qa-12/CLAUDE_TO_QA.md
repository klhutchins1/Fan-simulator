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
| D | PLA+ / material picker | UI + stamps, no CFD | after C |
| E | UI regression tests | headless tests | **if idle** after D |
| — | CFD, loft, glyphs, 27.2b, optimizer | — | **do not** |

Pre-register **A, B, C, and D** (and E if you will run it) before data. If A–C are already
pre-registered, amend that commit / add D+E before starting them.

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

## Task D: material picker does not follow PLA+ (Kimball, 2026-10-14)

**Report, do not patch.** Kimball: the Fan tab defaults to PETG; choosing **PLA+** (or another
filament) still looks like a PETG build.

Two fields exist:

- UI picker: `state.assess_material` (`fan_tab_ui.py` dropdown; default `DEFAULT_MATERIAL` = PETG).
- Fan model: `FanSpec.material` / `active_spec().material` (a12x25 is PETG). Assess click snapshots
  `assess_material` in `run_settings.py`. Export README, print temperatures, and Preview grams use
  `spec.material`.

### Method (no OpenFOAM, no Docker)

Cold-open Fan tab, Stock. Note the material chip. Switch to **PLA+**. Then, without changing it
back, record what each surface says:

| id | surface | how |
|---|---|---|
| M0 | dropdown / Actions chip | still PLA+? |
| M1 | Preview fit line (`✓ fits … g`) | grams; PETG vs PLA+ density should differ if it followed |
| M2 | Export README + print nozzle/bed | one Stock Export (same as Task C is fine if you switch to PLA+ first) |
| M3 | Assess stamp `extra.material` | if you already Assess for C, skip; else settings harness / a cancelled Assess that still writes extras. **No CFD required** — if Assess would start OpenFOAM, use the r8 settings harness pattern instead |
| M4 | optimizer argv `--material` | code read is enough (`fan_optimize.py`) |

**PASS** is not required. Write which of M0–M4 still say PETG after PLA+ is selected, and whether
`active_spec().material` is the cause. Note: `docs/qa/notes/material-picker-r12.md`.

---

## Task E: UI regression tests (filler — only if A–D are done)

The cockpit is Trame/Vuetify. 3-D is slow; **do not wait on VTK / Preview mesh / Export fuse** unless
the test is specifically a caption. Existing coverage: `tests/test_fan_tab_setup_smoke.py` (bind +
async handler bodies) and `docs/qa/settings_during_run/harness.py`. Manual checklists are
`docs/qa/browser_checklist_*.md` (historical).

Add **2–4 headless tests** that would have caught 29.1 or a similar “we say X, we don’t”:

- Prefer extending the smoke test / harness (Python, no Playwright required).
- One test must fail if Export README material ignores `assess_material` (seed from Task D).
- Do not click Assess CFD. Do not require a 3-D screenshot.

If you write tests, they are a **proposal** (do not commit them to master from the QA clone unless
the brief’s edit paths already allow `tests/`; they do **not** — so put the test files under
`handoff/2026-10-14_from-qa-12/tests/` and describe them in `docs/qa/notes/ui-regression-r12.md`).

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
- Pre-register A–D (and E if you run it) before data.
- Big data gzipped (gitignored).
- Status line per task in the README.
