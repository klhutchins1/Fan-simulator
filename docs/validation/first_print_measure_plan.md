# First print-and-measure session: pre-registered plan (2026-10-02; band rewritten 2026-10-13)

Step 4 of the trust program: **predict, print, measure, compare**. Equipment, fixture and the
step-by-step bench routine are already in [`validation/rig.md`](../../validation/rig.md). This page
adds what that guide lacks: predictions written **before** measuring, a way to cancel the
anemometer's own bias, and pass/fail rules.

**Print freeze (2026-10-13):** article B is **Stock v3**, wrapped sections, sharp 0.2 edges,
hub-cut corrected (`config/problems/a12x25_reference.yaml`, merge `ae3f1c4`). Do not print the
planar v2 recipe. Do not print optimizer candidates (their sliders mean a different blade under
wrap, roadmap 27.7). Do not slice until this band is the one you are testing.

The 2026-10-02 B/A **0.89 (0.82–0.96)** used planar-recipe CFD 56.4 × print 0.95. That band is
retired. The 57.6 CFM figure was a round-edge v3 (fit-script bug); do not use it.

## Why compare ratios, not raw CFM

A handheld anemometer on an outlet sleeve does not read true free-air CFM. It is biased by the
sleeve, vane placement and the swirl in the jet. That bias is the same for every impeller on the
same fixture. So:

1. Measure the **genuine Noctua impeller** first. Its true free-air CFM is known (published
   60.1 CFM). That calibrates the rig.
2. Measure the **printed** impeller on the identical fixture.
3. Compare the **ratio printed / genuine**. The anemometer bias cancels out of the ratio.

## Articles, in order

| # | Article | Why |
|---|---|---|
| A | Genuine Noctua A12x25 impeller (stock, on your donor frame + motor) | rig calibration standard |
| B | **Printed Stock v3** (`a12x25_reference.yaml`, wrapped, sharp 0.2 edges) | tests CFD + recipe + print roughness on the recipe that matches the close-ref STL |
| C | A candidate design (chosen after A/B pass **and** after 27.7 bound re-derivation) | first real test of an optimized design |

Print B from the cockpit: Fan → pick **Reference · Noctua A12x25** → **Export print STL** (Fit hub/frame
on), or `uv run python scripts/export_a12x25_print_ready.py`. Note the material, layer height,
nozzle and infill, and weigh the part. If a §28 print-id exists by then, record it; otherwise write
the export stem on the hub with a sharpie from the README.

## Predictions (written before any measurement)

All at **2000 rpm free air**. CFM scales with RPM (affinity law), so if the tach reads a different
speed, scale the measured CFM by `2000 / tach_rpm` before comparing.

Same-setup CFD (validation rig, base cell 5 mm, frame, 1000 iterations,
`docs/validation/audits/2026-10-12-cylinder-sections.md`):

| geometry | 0 Pa (CFM) |
|---|---|
| close-ref STL (the real blade, as meshed) | 58.3 |
| Stock v3 wrapped, sharp, hub-cut corrected | **55.7** |
| Stock v2 planar (not printed) | 54.5 |

Recipe / real-blade in that CFD: 55.7 / 58.3 = **0.955**. Datasheet A is 60.1, so the unprinted
v3 geometry would be 0.955 × 60.1 = 57.4 CFM if the screening bias is the same on both shapes.
A literature print factor 0.95 is still unmeasured.

| quantity | prediction | basis | pre-registered band |
|---|---|---|---|
| A: genuine impeller, true free air | 60.1 CFM | Noctua datasheet | (defines the rig factor) |
| B: printed Stock v3, true free air | **54.5 CFM** | 57.4 × print factor 0.95 | ±10 % → 49.1–60.0 |
| **B / A ratio** (the real test) | **0.91** | 0.955 × 0.95 | **±0.06 → 0.85–0.97** |
| B / A ratio, if the print factor were 1.0 | 0.955 | 55.7 / 58.3 | tells you whether print roughness matters |

**Rig factor:** `k = A_measured(2000 rpm) / 60.1`. Corrected B = `B_measured(2000 rpm) / k`.

### Why ±0.06 on the ratio

The recipe-vs-real gap is now **inside the 0.955**, not an extra unknown (it was −6 % in the 2026-10-02
plan). What is still loose:

- Print factor 0.95: literature, not measured (allow roughly 0.90–1.00).
- Anemometer ratio: a few % with 3 repeats and a fixed pose.
- CFD recipe/STL relative: about 3 % (same mesh; screening, not datasheet-truth).

Combined loosely, not as a strict statistical sum. Width is similar to the old ±0.07; the *centre*
moved because v3 is closer to the real blade than planar was.

If the ratio lands outside the band, something in the chain is wrong, and finding out what is the
point.

## Pass / fail and what each outcome means

| result | meaning | next step |
|---|---|---|
| B/A in 0.85–0.97 | the chain holds: CFD + v3 recipe + print are trustworthy at free air | measure the print factor precisely (B/A ÷ 0.955); pick candidate C only after 27.7 |
| B/A > 0.97 | print costs less than assumed, or the recipe is better than CFD says | raise the print factor toward 1.0; re-check with a second print |
| B/A < 0.85 | something loses more than predicted | check tip gap and fit first (rubbing, wobble, a binding cup), RPM under load, print warp. Then compare the measured blade against the STL (calipers on chord and tip). Do not tune the sim until the cause is found |
| A reads far from 60.1 CFM raw | normal (anemometer bias) | only the ratio matters; keep the pose fixed |

## Session checklist (with `validation/rig.md` §First session recipe)

1. Tach and anemometer on hand (buy list: rig.md §Shopping list, ~$45–60).
2. A on the donor frame → set 2000 rpm by tach → 3 × 10 s anemometer readings → noise at 1 m
   (relative only).
3. Swap to B on the **same** frame, pose, sleeve and room → same 2000 rpm → 3 × 10 s → noise →
   weight.
4. Record both in the cockpit (**Record measurement**: `rpm`, `tach_rpm`, `cfm`, `noise_dba`) or
   with `scripts/rig_logger.py`. Stamp the export stem / print-id.
5. Compute k, corrected B and B/A. Then fill in the results section below.

## Results (to fill in)

| article | tach rpm | raw CFM (mean of 3) | CFM @ 2000 rpm | corrected (÷k) | noise dB(A) | weight |
|---|---|---|---|---|---|---|
| A genuine | | | | 60.1 (by definition) | | — |
| B printed Stock v3 | | | | | | |

B/A = ____ (prediction 0.91, band 0.85–0.97) → PASS / FAIL.
