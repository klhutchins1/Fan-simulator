# Round 29 for grok (Cursor, 2026-11-12, four pickups)

This replaces the 2026-11-11 bundle (master `98e3f2c`, never returned). Do not use that bundle.

**Build:** `fansim_master.bundle` in this folder is master including the commit that adds this brief. Write `docs/qa/rounds/r29.md` only. Do not edit `docs/QA_REVIEW.md` or the board. Do not invent a tolerance. Do not retune a failed check. Re-check a fix only when it was HIGH, plus the named open UI rows below.

You pick up work several times a day. This file is the queue. Each time, continue at the first pickup that has no written result in `r29.md`. Write that pickup's result before you start the next one, so a timeout does not lose the session. If you finish a pickup early, start the next. If all four are written up, stop. Do not open a new research lead.

No Docker, no OpenFOAM, no Assess, no Sweep, no Optimize run. The propeller-grid solve is already queued on Kimball's machine. Do not start it.

## Pickup 1 — accuracy, geometry

CAD is expected. This is the pickup that must not be skipped.

| # | task | board |
|---|---|---|
| A | **QA-73 HIGH re-check.** Export Stock with a known print-id. From outside +Z the recessed code must read left-to-right, un-mirrored, matching the README / `*_print_fit.json`. Cap **5.0 mm**, stroke **0.9 mm**, band r **11.5–16.5**. Red: the same tests fail on pre-fix `eeb0e2d`. Green: `tests/test_print_id.py` + `tests/test_print_id_glyphs.py`. | QA-73, QA-80 |
| B | **QA-79 hub face, not bbox.** On a t9002-class design (blades above the hub): the mark is on the hub +Z face. A section at `z_hub − 0.25 mm` shows the code; a section at blade `zmax − 0.25 mm` does not. | QA-79 |
| C | **Hub opening, re-derive.** `grip_protrude_mm` is **0.35**, equal to clearance, so A12x25 pad tips sit on `cavity_dia_mm` **37.25**. The old 0.7 mm protrude put tips at **36.55**. Confirm `tests/test_mountable.py` and the layout in `fansim/fan_spec.py`. Measure one exported Stock the same way: pad tips on the cup side, not the engraved print-id on the inlet face. Do not change `cavity_dia_mm`. Prereg: `docs/validation/audits/2026-11-11-hub-opening-prereg.md`. | P4a |

## Pickup 2 — GUI and features

Headless first. Use a browser only if this machine has a display. Do not click Assess, Sweep, Optimize, or Run.

| # | task | board |
|---|---|---|
| D | Run `tests/test_ui_says_what_it_does.py`, `tests/test_qa51_neuralfoil_expert.py`, and `tests/test_r26_hide_scaffolds.py`. Simple mode must not offer NeuralFoil. Expert title contains "experimental". Centrifugal-only and wind-turbine flows stay out of the cockpit and the README Quickstart. Mixed and Volute stay. | QA-51, R2.6, R3.7 |
| E | On this master, re-check these still-open rows and say fixed or still open. Do not patch. UI-26 (Gold = parametric Stock on first view), UI-27 (viewer cut off at 1366×768), UI-31 (surrogate-guided Optimize still skips CFD / `synthetic_label`), UI-33 (Optimize does not say it ignores the Design sliders), QA-40 (Simple mode still shows a noise line with no Stock reference), QA-42 (Preview grams do not name the material). | UI-26, UI-27, UI-31, UI-33, QA-40, QA-42 |

## Pickup 3 — CPU, clean-clone fast suite

This is the long job. Clone the bundle fresh. `uv sync --extra dev`. Then:

`uv run python -m pytest -q -m "not docker and not slow"`

Report passed, failed, skipped, and the first failure if there is one. An OCCT crash after a green summary (exit 3221225477 or -1073741819) is not a failure. Do not run the docker marker, the slow marker, or any OpenFOAM case. If you are about to be cut off, write how far the run got and stop.

## Pickup 4 — accuracy, read the code

No new numbers. No solve.

| # | task | board |
|---|---|---|
| F | **A0c code read.** C-grid defaults stay 48 / 60 / 32, far field 8 chord, wake 16 chord. The gate flags (128 tangential, far field and wake 50 chord, LE/TE cell ≤ 0.1% chord, adjacent ratio ≤ 1.2, normal growth ≤ 1.15) match `docs/validation/audits/2026-11-06-ruling-rung-a0-cgrid.md`. Test file: `tests/test_prop_section_2d.py`. Do not start the solve. | R2.2a″ |
| G | **One bug hunt, then stop.** Read Simple-mode strings and the README Quickstart. Report one claim that says a number is validated, or a measured dB(A), when the code does not have that evidence. If you find none, say none. Do not fix it. Do not open research leads 23+. QA-74/75/76 travel with A. QA-12 stays open; do not propose a new polar blend. | R1.10 |

## Print session (record only)

Kimball printed H7MQ8 (Stock v3, PLA+, 0.6 mm, 27.41 g) and E0MWW (t9002 extra). Both files have pad tips at 36.55 mm and do not seat. A 6 mm ring at 37.25 mm fits the motor better. A full Stock export with that same circle is print-id `AVD9=` (2026-11-12). That print is not a T1 pass until it is on the frame. Do not treat the ring as article B.
