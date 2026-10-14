# Cursor → QA bot, 2026-10-14 (round 13)

Same contract. **Finish round 12 first.** Do not abandon A–E there.

Pull **master** at the commit that added this folder (24.2 Results + Design dump
paragraphs) or later. Clone at `cec573a` / `ef31cc5` is missing the Design blurbs.
No bundle. No `git apply`.

## What landed since the r12 brief

| item | state |
|---|---|
| 25.10 | Near-stall Assess caption. Hold-out MIXED. Do not retune. |
| 23.18 | Prop Analyze headline `@ rpm (max), static`. |
| 23.55 | Cup-fuse gauge test isolated in a child. |
| 23.9 | Fast suite is three pytest processes: `scripts/pytest_chunks.py`. |
| 24.2 first slice | Results glossary / Gold ✕ / fits-only / scatter how-to are Expert-only. |
| 24.2 Design blurbs | On master after `ef31cc5`: Geometry panel dump paragraphs are Expert-only too. Hover tooltips stay. |
| 24.4 / QA-22 | Already investigated + stamped-at-click. **Do not re-run** the settings harness. |
| 28.3 | still parked |
| QA-12 CT0 | still parked; do not retry the low-Re polar blend |

## Overview

| # | task | kind | start? |
|---|---|---|---|
| A | 24.2 Simple vs Expert | browser, no CFD | **after r12 return** |
| B | Duplicate-after-run catalog | Preview then look; report | after A |
| C | 23.9 chunked suite RSS | Linux pytest, ~1 h | after A, may overlap B |
| D | Other-tab caption inventory | read UI + screenshots | if idle |
| — | CFD, Docker, loft, glyphs, 27.2b, optimizer, QA-12, 24.4 | — | **do not** |

Pre-register A–C (and D if you will run it) before data.

---

## Task A: 24.2 Simple vs Expert (no source edit)

Cold-open Fan tab, **Simple** (default). Results, then Design → Geometry panels.

| id | PASS iff |
|---|---|
| S0 | Simple Results does **not** show "Glossary — CFM", "Gold ✕ = datasheet", the fits-only paragraph, or "CFM scatter — up and right". Switches (Fits / Declutter / Show stock) and the Design dropdown **do** show. |
| S1 | Flip to Expert: those four blocks appear. Flip back: they hide. `localStorage fansim.ui_mode` remembers across reload. |
| S2 | Simple Design still has sliders, live fit lines (`hub_fit_info` / `tip_fit_info` / wall readout), and "Hover any slider…". It does **not** show the dump paragraphs (Chord = LE→TE, NACA = cambered…, Camber = the scoop, Wall = the thin dimension, NACA: LE/TE scales, Three boxy bites, 0 thickness = off, Blade on hub: + raises). |
| S3 | Expert Design shows those dump paragraphs. Hover tooltips still work in **both** modes. |
| S4 | report only: at **768×** viewport, is the Results scatter above the fold in Simple? Screenshot both modes. |

No OpenFOAM. Preview mesh is optional (S2/S3 do not need a new mesh).

Note: `docs/qa/notes/simple-mode-24-2-r13.md`.

---

## Task B: duplicate-after-run catalog (report only)

24.2 still has "remove the duplicate information that appears after a run."

After **one Preview** of Stock (not Assess CFD): list every caption / alert that repeats
something already on screen (score line vs plot vs Actions chip vs `preview_msg` vs
flow-card). Same after opening a **cached** Assess if one exists on disk; **do not start
OpenFOAM**.

Output: a table `surface → text (first 80 chars) → already shown where?`. No patch.
No recommendation required beyond "hide / keep / needs Kimball copy".

Note: `docs/qa/notes/duplicate-after-run-r13.md`.

---

## Task C: 23.9 Linux chunked pytest RSS

One process used to peak **8.2 GB** (`docs/QA_REVIEW.md`, ~21 min 40 s). Master now runs:

```
uv run --extra dev python scripts/pytest_chunks.py --chunks 3 --all -- -m "not docker and not slow" -q --tb=line
```

Sample RSS every 2 s (`qa/fullsuite_rss.log` style). Log **per chunk** (the script prints
`pytest chunk i/3`).

| id | PASS iff |
|---|---|
| M0 | 0 failed (skips / xfail / OCCT teardown abort after green is noise). |
| M1 | no OOM in dmesg. |
| M2 | report peak RSS per chunk, and the suite wall time. Not a fail if one file (cup fuse) is still ~7 GB **inside its chunk** — the point is the process dies after that chunk. |

Do not run the suite as one process "for comparison" unless M0–M1 are already done and
you have RAM to spare.

Note: `docs/qa/notes/pytest-chunks-r13.md`.

---

## Task D: other-tab caption inventory (filler)

For Mixed, Prop, Volute, CROR: list always-visible `text-caption` dumps (not hover
tooltips, not live `{{ … }}` fit/status). Screenshot Simple vs Expert if those tabs
respect `ui_mode` at all (they may not yet).

Report: which strings should be Expert-only next, with file:line. No patch.

Note: `docs/qa/notes/other-tab-captions-r13.md`.

---

## Do not

- CFD, Docker, OpenFOAM, Stock repeats, QA-12 CT0 retry.
- 28.3 glyphs / dummy pocket.
- 27.2b / Printables / outside STLs.
- `_capped_loft`, `correct_clipped_sections`, Stock YAML.
- Restart the optimizer.
- Re-run 24.4 / `docs/qa/settings_during_run/harness.py` (QA-22 closed).
- Start this round before `handoff/2026-10-14_from-qa-12/` exists.

## Conventions

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**`, and a new `handoff/2026-10-14_from-qa-13/`.
- Pre-register A–C (and D if you run it) before data.
- Big data gzipped (gitignored).
- Status line per task in the README.
