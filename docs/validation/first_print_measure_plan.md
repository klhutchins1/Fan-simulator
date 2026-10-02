# First print-and-measure session: pre-registered plan (2026-10-02)

Step 4 of the trust program: **predict, print, measure, compare**. Equipment, fixture and the
step-by-step bench routine are already in [`validation/rig.md`](../../validation/rig.md). This page
adds what that guide lacks: predictions written **before** measuring, a way to cancel the
anemometer's own bias, and pass/fail rules.

## Why compare ratios, not raw CFM

A handheld anemometer on an outlet sleeve does not read true free-air CFM. It is biased by the
sleeve, vane placement and the swirl in the jet. That bias is the same for every impeller on the
same fixture. So:

1. Measure the **genuine Noctua impeller** first. Its true free-air CFM is known (published
   60.1 CFM; our CFD on the close-reference STL gives 59.8). That calibrates the rig.
2. Measure the **printed** impeller on the identical fixture.
3. Compare the **ratio printed / genuine**. The anemometer bias cancels out of the ratio.

## Articles, in order

| # | Article | Why |
|---|---|---|
| A | Genuine Noctua A12x25 impeller (stock, on your donor frame + motor) | rig calibration standard |
| B | **Printed Stock recipe** (`a12x25_reference.yaml`, measured chord basis) | tests CFD + recipe + print roughness on a design CFD has validated |
| C | A candidate design (chosen after A/B pass) | first real test of an optimized design |

Print B from the cockpit: Fan → pick **Reference · Noctua A12x25** → **Export print STL** (Fit hub/frame
on), or `uv run python scripts/export_a12x25_print_ready.py`. Note the material, layer height,
nozzle and infill, and weigh the part.

## Predictions (written before any measurement)

All at **2000 rpm free air**. CFM scales with RPM (affinity law), so if the tach reads a different
speed, scale the measured CFM by `2000 / tach_rpm` before comparing.

| quantity | prediction | basis | pre-registered band |
|---|---|---|---|
| A: genuine impeller, true free air | 60.1 CFM | Noctua datasheet; CFD 59.8 (−0.5 %) | (defines the rig factor) |
| B: printed Stock recipe, true free air | **53.6 CFM** | CFD 56.4 (validated setup, Audit chord-basis 2026-10-01) × print factor 0.95 | ±10 % → 48.2–59.0 |
| **B / A ratio** (the real test) | **0.89** | 53.6 / 60.1 | **±0.07 → 0.82–0.96** |
| B / A ratio, if the print factor were 1.0 | 0.94 | 56.4 / 60.1 | tells you whether print roughness matters |

**Rig factor:** `k = A_measured(2000 rpm) / 60.1`. Corrected B = `B_measured(2000 rpm) / k`.

### Why ±0.07 on the ratio

- CFD method: within ~3 % of two measured fans in the unstalled range.
- Stock recipe against the real blade: −6 % (Audit #2 / §19.7).
- Print factor 0.95: provisional, from the literature, not measured.
- Anemometer repeatability: a few % with 3 repeats and a fixed pose.

These are combined loosely, not as a strict statistical sum. If the ratio lands outside the band,
something in the chain is wrong, and finding out what is the point.

## Pass / fail and what each outcome means

| result | meaning | next step |
|---|---|---|
| B/A in 0.82–0.96 | the chain holds: CFD + recipe + print are trustworthy at free air | measure the print factor precisely (B/A ÷ 0.94); pick candidate C |
| B/A > 0.96 | print costs less than assumed, or the recipe is better than CFD says | raise the print factor toward 1.0; re-check with a second print |
| B/A < 0.82 | something loses more than predicted | check tip gap and fit first (rubbing, wobble, a binding cup), RPM under load, print warp. Then compare the measured blade against the STL (calipers on chord and tip). Do not tune the sim until the cause is found |
| A reads far from 60.1 CFM raw | normal (anemometer bias) | only the ratio matters; keep the pose fixed |

## Session checklist (with `validation/rig.md` §First session recipe)

1. Tach and anemometer on hand (buy list: rig.md §Shopping list, ~$45–60).
2. A on the donor frame → set 2000 rpm by tach → 3 × 10 s anemometer readings → noise at 1 m
   (relative only).
3. Swap to B on the **same** frame, pose, sleeve and room → same 2000 rpm → 3 × 10 s → noise →
   weight.
4. Record both in the cockpit (**Record measurement**: `rpm`, `tach_rpm`, `cfm`, `noise_dba`) or
   with `scripts/rig_logger.py`.
5. Compute k, corrected B and B/A. Then fill in the results section below.

## Results (to fill in)

| article | tach rpm | raw CFM (mean of 3) | CFM @ 2000 rpm | corrected (÷k) | noise dB(A) | weight |
|---|---|---|---|---|---|---|
| A genuine | | | | 60.1 (by definition) | | — |
| B printed Stock | | | | | | |

B/A = ____ (prediction 0.89, band 0.82–0.96) → PASS / FAIL.
