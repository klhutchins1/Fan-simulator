# Claude → QA bot, 2026-10-12 (round 9)

Your round-8 Task D (built blade vs its numbers) changed the builder. Kimball chose option (i): **blade
sections are now wrapped onto their cylinders.** This round is mostly about testing that change
independently.

`fansim.bundle` (this folder) has two branches:
- `master`: the round-8 fixes. The "Done" message no longer gets overwritten (QA-29); the flow card judges
  the push on the area-weighted mean and writes NaN as `null` plus a reason (your Task G).
- **`cylinder-sections`: the wrap. Not merged yet.** Test this branch.

## What changed on `cylinder-sections` (please verify, don't re-find)

- **The field.** `BladeParams.section_wrap` is `"cylinder"` (each section lies on its cylinder: θ = lean +
  t/r) or `"planar"` (legacy).
  - The dataclass default stays **planar**, so props, wind, centrifugal and CROR are unchanged.
  - The axial-fan entry points choose cylinder: `suggest_params`, `blade_from_flat` (absent key =
    cylinder), and the Stock YAML.
  - Old saves are stamped planar by `scripts/migrate_section_wrap.py`; unstamped optimizer trials read as
    planar (`trial_attrs.section_wrap_for_trial`).
- **The loft.** A wrapped loft is a *capped ruled shell* (`blade._capped_loft`). The planar end wires I
  tried first folded the loft on wide-root blades: S4_0001 fused to a single blade, 1,190 vs 76,518 mm³. A
  smooth loft made the fuse 15× slower. The last wrapped wire sits 0.5 mm outside the tip, so the trim
  crosses the blade instead of running along a wire. Inverted lofts are flipped.
- **QA-30.** The chord realisation now measures the **hub-clipped** blade.
- **Stock** was refit with wrapped sections (`config/problems/a12x25_reference.yaml`, v3; v2 kept as
  `a12x25_reference_planar.yaml`).
- **Audit:** `docs/validation/audits/2026-10-12-cylinder-sections.md`.
  - **V1 FAIL**, only where the hub-face clip cuts the blade. With the clip off, every station matches
    within camber 0.001 and stagger 0.1°.
  - **V2 PASS.**
  - **V3:** 20/20 build, with volumes within 1.2 % of planar.
  - **V4 PASS:** 0 wrong on 30 parts, and S3_0014 now reads correctly.
  - **V5 FAIL:** wrapped Stock gives +8.6 % free / +7.5 % loaded CFD vs planar Stock. The surface-distance
    diagnosis shows the wrapped refit sits ~0.3 mm further from the real STL on the outer span (mean
    0.57 vs 0.41 mm). I'm running CFD on the real STL now to see which recipe is closer in airflow.
  - **V6:** on t9005, the BEM–CFD gap shrinks from −16 % to −7 % free.

## Overview

| # | task | kind | why now |
|---|---|---|---|
| A | **Robustness of the wrapped builder**, on a larger, pre-registered sample | long, build-only | my V3 had 20 designs and no notched tips or winglets |
| B | **Built vs sliders on wrapped builds** (your Task D method, independently) | build-only, medium | confirms V1, and sizes the hub-clip effect across the optimizer's space |
| C | **Stock surface fit**: prototype fitting the wrapped recipe to the STL's *surface* | build-only, long | the likely fix for V5 |
| D | **External STLs (27.2b): radial-led rule**, pre-registered confirmation on more real STLs | geometry | external meshes still need it, even though builder designs no longer do |
| E | **Shrouded fuse memory** (27.1) | short builds | the ring outliers in your Task C |
| F | (optional) Near-stall flag | analysis | carried over |

Pre-register A, B, C and D in **one** commit before any data. Order: A starts first and runs unattended;
do B and C alongside it; D and E after.

---

## Task A: robustness of the wrapped builder

Use your stress runner on branch `cylinder-sections`, with the stress inputs (`inputs.jsonl.gz`) as the
population.

**Sample** (fixed seed, recorded):
- 150 designs across S1–S8 and CTL;
- **at least 15 with notched tips**, 15 with winglets, 15 with tip rounding, 15 featured, 15 shrouded,
  10 with uneven blade spacing and 10 near the bounds (S8). If the population lacks enough of a kind,
  build it by setting that option on random base designs, and say so.

**Per design, build both `section_wrap="planar"` and `"cylinder"`** (P builds only), plus cup (C)
builds for 30 of them on the wrapped branch.

**Checks to pre-register (my suggested thresholds; justify any change):**
- **W1:** wrapped builds are watertight, one body, inside tip + ring thickness, nothing below the hub face.
- **W2:** wrapped volume within 5 % of planar.
- **W3:** wrapped wall time ≤ 2 × planar, per design.
- **W4:** K7 cup depth passes on the 30 C builds.
- **W5:** the direction proof is never CONCLUSIVE-wrong on wrapped builds. Log how many INCONCLUSIVE and
  their camber, compared with planar.

Keep the round-7 runner rules: monotonic clock, one P build at a time, memory gates.

## Task B: built vs sliders on wrapped builds

Re-run your round-8 Task D measurement on `cylinder-sections`:
- Stock v3, lt120, t9000/t9002/t9003/t9005 and 20 stress designs;
- per-station analytic bias, as before.

**Report:**
1. The gap at stations the hub-face clip does **not** reach (I expect it to be about zero).
2. The gap at stations it does reach.
3. **For the stress population as a whole:** how far blades hang below the hub face, how often, and how many
   stations that affects. That decides whether the clip needs its own fix.

Pre-register the rule you used in round 8 ("material" = chord > 3 % or camber > 0.005 at chord/r ≥ 0.4).

## Task C: Stock surface fit (prototype; don't change the shipped recipe)

**The problem.** `scripts/fit_recipe_to_stl.py` matches five numbers per section at six radii, and both the
planar and wrapped fits pass that. Yet they differ by 8 % in CFD, and the wrapped one sits ~0.3 mm further
from the STL surface outboard. `scripts/stock_surface_distance.py` measures that distance (alignment by
rotation + axial shift).

**Prototype a fit** that starts from the v3 wrapped recipe and also minimises surface distance to
`validation/reference/a12x25_impeller.stl`. Consider:
- adding LE/TE positions (`sweep`, `skew`, `lean_deg`) as always-on fit variables;
- more stations;
- distance to the surface as the objective.

**Pre-register the targets:**
- mean distance ≤ the planar recipe's 0.41 mm;
- outer span (r/R 0.8–1.0) ≤ 0.26 mm;
- V2's section tolerances still met.

Deliver the recipe as a **proposal** YAML in `docs/qa/stock_fit/`. I'll run the CFD.

## Task D: external STLs, radial-led rule (27.2b)

Your round-8 proposal:
- accept the radial reading when it is CONCLUSIVE and the cylinder reading agrees or can't tell;
- ask the user for the spin when they disagree, or when the radial reading can't tell.

**Pre-register it and confirm it on real external impeller STLs:**
- at least 8 CC-BY or CC0 impellers, for example from Printables or Thingiverse;
- **local use only, never committed** (licences, §25.8); list their URLs and licences in the note;
- add both references, and mirrors of everything.

Fans whose spin you know (from the page, or from how the blade is shaped) are the ground truth.

**Pre-register:** 0 wrong. Report the coverage.

## Task E: shrouded fuse memory (27.1)

Repeat round-8 Task C (RSS at the call, VmHWM, increment), but on **12 shrouded designs** across faces
and ring heights, plus 4 unshrouded controls, on master.

Fit the ring's extra cost as one of:
- a per-face rate for the ring's own faces;
- a constant;
- a function of ring height.

Use the hook from round 8.

## Task F (optional)

The near-stall flag, unchanged.

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**` and a new `handoff/2026-10-12_from-qa-9/`.
- Pre-register before data, then commit and hash it.
- Patches are proposals only.
- Big data stays gzipped (it's gitignored).
- No outside STLs get committed.
- Put a status line per task in the README.
