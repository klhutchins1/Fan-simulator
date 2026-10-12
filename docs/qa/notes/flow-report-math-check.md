# Flow-report math, independent check (round 7, Task G; synthetic fields only, no CFD)

- **Pre-registration:** G1/G2 in `prereg/PREREG_R7.md`, branch `prereg/round7` (commit 2073315), sha256 `c163f1d7…2d0e6e`. Written before the check script existed.
- **Script:** `handoff/2026-10-11_from-qa-7/scripts/flow_report_math_check.py`. It runs against master 5980677 and prints PASS/FAIL per case.
- **Synthetic fields:** annular cell grids on the exit and inlet slabs, weighted by exact annulus area. The expected values are hand-derived from the spec table, not from the code.

## Plain-language verdict
- **The arithmetic is right.** Every number on the card matches its written definition exactly on fields with known answers: backflow, spin share (including reversed spin and pure spin), dead air, tip ratio, per-band push in Pa (with swirl correctly ignored) and the Proudman noise level (to 0.00 dB, cells outside the rotor region excluded).
- **G1: PASS (16/16).**
- **G2: FAIL (3 cases).** Degenerate inputs give NaN silently:
  - zero exit flow → spin share and tip ratio are NaN;
  - all weights zero → every metric is NaN;
  - a coarse mesh with no samples in the outer 10 % or in a band → tip ratio and those bands are NaN.
  - **Harm is limited.** `flow_verdicts._bad()` turns NaN into "Couldn't measure" / "unknown", so the card does not show a wrong verdict.
  - **Two real gaps remain:**
    1. `flow_report.json` is written with Python's non-standard `NaN` token, so strict JSON readers would choke.
    2. Nothing records *why* a value is missing.
  - **Proposal:** emit `None` plus a reason string, or raise `FlowReportUnavailable` when the weights sum to 0.
- "All backflow" and "no exit cells" behave well: net_reversed is set, and an explicit error is raised, respectively.

## Cases the repo's tests (`tests/test_flow_report.py`, 13 tests) miss
- **Numeric value of the noise level:** the test only checks it is present. This check pins it to the closed form α·ρ·Cμ·k·ω·(√(2k)/c0)⁵·V. Cells outside |z − z_fan| ≤ 1.5 r_tip are excluded.
- **Swirl sign:** with the opposite spin, swirl_frac is unchanged (correct). Also a mixed field (Uz 3, Uθ 4 → 0.64).
- **The degenerate/NaN cases above**, and the NaN-in-JSON write.
- **Radial equilibrium (important for interpreting the push bars).** A field whose only change is a uniform 4 m/s swirl, with the physically required static-pressure gradient dp/dr = ρUθ²/r, gives push bands of **−8.9, −3.4, +0.9, +4.4, +7.4 Pa** (hub → tip), even though no axial work was added.
  - So excluding ½Uθ² does **not** fully remove swirl from "push". Swirl still moves static pressure from hub to tip.
  - For Stock (62 % swirl energy) this is the same size as its band values (8–17 Pa). A swirly fan's push bars will look hub-weak and tip-strong for that reason alone.

## Decision 1: excluding swirl from "push" (audit run 1 → run 2)
- **Right call on physics.** Exit swirl is not useful pressure for a fan without a stator, and swirl already has its own row. Counting ½Uθ² twice was a definition error.
- **The audit disclosed** that the change was made after seeing data. It is defensible because it changes *what* is measured, not a threshold. It also flipped t9005's push from "weaker" to "better", which is the result you would want, so treat it with that bias in mind.
- **Remaining limitation:** the radial-equilibrium effect above.
- **Proposal (not a patch):**
  - Add one line under the push bars: "spin also shifts pressure from hub to tip; compare the bar shape only between fans with similar spin".
  - Or compare the **area-weighted mean** push across bands, which radial equilibrium leaves almost untouched (its mean shift here is about 0).

## Decision 2: widened thresholds (±15 % per band, 2.8 dB)
- **Weak basis.** Each is set to the smallest value that passes **one** pair of runs, so it equals a single observed difference.
  - One pair can't pin the spread. If 14.3 % was the largest of the 5 band differences, it implies a per-band σ of about 8.6 %. Then ±15 % is about 1.7σ, an 8 % chance per band and about 34 % per comparison that some band flips spuriously.
  - If 14.3 % was a typical band difference, σ is about 18 %, ±15 % is about 0.8σ, and it is about 40 % per band and about 90 % per comparison.
  - Either way, a same-fan comparison will often show a spurious "stronger/weaker" band.
- **The pair is not a pure repeat.** "Stock-prev" is the pre-hub-clip geometry, and the reference has the hub clip. Part of the 14.3 % (band 2) and 2.75 dB may be a real geometry effect. The rest is solver run-to-run noise.
- **Proposal:**
  - Get 3–5 repeats of the *same* Stock case and set each tolerance at about 2σ of the pairwise differences.
  - Until then, require ≥ 2 adjacent bands, or the mean, to cross before the push row says "stronger/weaker".
  - Keep 2.8 dB as a floor for noise, and label it "rough".
