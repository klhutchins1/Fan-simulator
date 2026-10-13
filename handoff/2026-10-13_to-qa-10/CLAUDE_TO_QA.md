# Cursor → QA bot, 2026-10-13 (round 10)

Same contract as the Claude briefs. Cursor is writing this on Kimball’s behalf. Round 9 is
received and useful — **do not resume Task A to 150**, and **do not start another wrap probe**
until you get a new bundle at a **named merge commit**.

There is **no new `fansim.bundle` this round.** Round 9 already tested `cylinder-sections` @
`7b02bed`. Work now is on **current master** (docs commit `f2dba96` is your round-9 notes; the
code is still planar Stock). Wrap is not merged.

## Round 9, what we took

| task | verdict we are using | action |
|---|---|---|
| A wrap robustness (66/150) | W2/W4/W5 PASS; W1 OOM ×1 featured; W3 shrouded slow ×1; QA-33 | enough. do not continue the 150 |
| B built vs sliders | QA-32 (clip-reached camber/stagger) | Claude: BEM on clipped sections. you: don’t re-measure unless wrap merges |
| C surface fit | T1/T2 PASS, **T3 FAIL** | do not CFD that YAML as Stock |
| D external radial-led | not a valid confirmation (truth cue failed) | **stop.** no more Printables downloads |
| E shroud fuse | extra cost ~66 KiB / blade face, not ring faces | Claude will patch the guard (27.1) |
| F near-stall | not done | still optional; skip unless A is short |

## Overview

| # | task | kind | start? |
|---|---|---|---|
| A | **Print-part ID mark-spec** (roadmap §28) | build + measure, medium | **now**, on master |
| B | Wrap confirmation on **merged** master (W1–W5, n≈40) | long, build-only | **WAIT** for a new brief + bundle |
| C | Fuse-guard re-measure after Claude’s 27.1 patch | short builds | **WAIT** for that patch in the bundle |
| D | Stock free-air CFD × 5 for flow-card 2σ (27.3) | CFD, ~2–3 h | **WAIT** until wrap is the recipe you would print |
| E | External STLs / radial-led | — | **do not** |
| F | Near-stall flag | analysis | skip unless A finishes early **and** you still have wall-clock |

Pre-register **A only** this round, one commit, before any A data.

---

## Task A: print-part ID — where can a code sit? (roadmap §28)

Kimball will print a box of impellers and needs each one to name its export without large text
on the blades. The code is a **short Crockford string** (4–5 chars), recessed, not a crypto
hash. Optional Data Matrix later. Sharpie is the fallback if the README prints the same code.

**Do not implement the feature.** Measure, propose, dummy-cut one pocket as a *proposal patch*
if you want. Notes under `docs/qa/notes/print-id-mark-spec-r10.md`.

### Geometry under test

Print-ready **Stock**, current master, with the motor cup
(`build_impeller_with_mount` / `export_print_ready`, A12x25 `MotorMount`). Hub-down print:
`BLADE_PRINT_RULES` says the rear face is on the bed, **+Z inlet is up**.

Measure, and write the numbers:

1. **+Z hub disk:** radial width of *flat hub face* inboard of the blade roots (min blade r at
   that z) and outboard of any front bore / fillet. Axial flatness (is it a ring we can recess?).
2. **−Z hub / cup:** radial width of any annulus **outside** the cup cavity, on the bed face.
   Cup floor: is it a usable down-facing surface? (we expect no).
3. Grip pads: stay away.

### Mark rules to pre-register (adjust with a reason)

Suggested; justify changes:

- **M1:** a usable +Z ring exists with radial width ≥ 6 mm over an arc ≥ 25°.
- **M2:** a dummy recess 8 × 3.2 × 0.5 mm (l × w × depth) on that ring keeps the impeller
  watertight, one body, and the cup still passing the mount gauge (same checks as round-9 W1/W4
  on **this one** Stock print-ready build — not 150 designs).
- **M3:** the dummy recess does not intersect blades, ring, cup cavity, or grip pads (≥ 1 mm
  clearance).
- **M4:** report FDM feasibility at 0.12 mm layers / ~0.4 mm nozzle: min stroke, min depth
  (3 layers), whether a 12×12 Data Matrix at 0.5 mm/module fits on the same ring next to 5
  glyphs at 3.2 mm cap height. Text is required; the matrix is optional.

If M1 fails, repeat M2–M4 on the −Z annulus (fallback). If both fail, say so and stop — do not
put a code on a blade.

### Deliver

- The note, with a sketch or coordinates (r_inner, r_outer, z, θ span) for the preferred
  pocket.
- A proposed alphabet (Crockford is the brief) and glyph height/depth.
- One sentence on aero: pocket face area / inlet hub-disk area. If that ratio is < 0.5 %,
  we will **not** CFD it.
- Patch, if any, is a proposal only.

Pre-register M1–M4 before cutting the dummy pocket.

---

## Tasks B–D (do not start)

Copied so Claude can fire them as **round 10b** with a bundle. If a bundle arrives without a
new brief, still wait — wrap on a moving branch is how round 9 got truncated.

**B, wrap confirmation (merged master only):** 40 designs, not 150. Must include notches,
winglets, shroud, featured, near-bounds. W1–W5 as round 9. One P at a time, memory gates,
monotonic clock. Featured OOM (S5_0167) is a known W1 miss — log it, don’t debug the guard
here (that’s C).

**C, fuse guard:** 12 shrouded + 4 open, RSS/working-set at the call vs peak, after the 27.1
patch. Pass = remaining growth covered on all 16.

**D, Stock repeats:** 5 free-air Assess on the **print recipe** (wrapped v3 once merged), same
setup, report 2σ for the flow-card bands. Not a fidelity campaign.

---

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**`, and a new `handoff/2026-10-13_from-qa-10/`.
- Pre-register A before data, then commit and hash it.
- Patches are proposals only. **No fansim source edits on master.**
- No outside STLs. No Printables. Task D from round 9 is closed as unconfirmable.
- Big data stays gzipped (gitignored).
- Status line per task in the README.
- If the box suspends, stop and mark FINAL as you did at 66/150 — do not leave a half-note.
