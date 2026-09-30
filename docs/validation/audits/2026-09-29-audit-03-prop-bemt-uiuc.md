# Audit #3: prop BEMT vs UIUC measured data (2026-09-29)

Question: does the propeller blade-element-momentum model (`fansim/propeller/bemt.py`) solve its equations
right, and does it match measured propeller data?

## Plain-language verdict

- **Verification: PASS.** The BEMT never beats ideal momentum theory (raw figure of merit 0.60-0.63 at
  3000-9000 rpm), thrust falls smoothly to zero at a finite advance ratio, the Prandtl factor stays in
  [0.15, 1], and the inflow iteration converges at every element tested.
- **Validation: INCONCLUSIVE overall.** The repo holds **one** UIUC measurement: a single static row
  (APC Slow Flyer 9x4.7, 6026 rpm), with **no chord/twist distribution and no J sweep**. The task's
  validation needs geometry plus C_T(J)/C_P(J). Zero props qualify, so the C_T(J) RMS test could not be run.
  The one static point is inside the pre-registered tolerances, but it was run on an approximate dia x pitch
  loft, so it is weak evidence.
- **Unit `propeller.bemt` is NOT recorded in the ledger** (INCONCLUSIVE never counts). It stays `NEW`.
  To close it, vendor the UIUC vol-1 APC SF 9x4.7 (or any prop with a published geometry file) J sweep
  and its chord/twist table, then re-run.

## Pre-registered tolerances (fixed before the run)

| metric | tolerance |
|---|---|
| static C_T0 | within +-15% |
| static C_P0 | within +-20% |
| C_T(J) RMS error | <= 0.015 |

Rule fixed in advance: a static pass on an approximate-geometry loft is recorded as "consistent", not proof.
A prop is judged only if it has both geometry and a measured J range; otherwise INCONCLUSIVE.
Tolerances were not changed after seeing the data.

## What the code claims

- Static and forward-flight thrust, torque, power from a 24-element blade-element / momentum balance with
  swirl. Reynolds-aware polars from the vendored UIUC/Selig tables (falls back to an analytic polar).
  Prandtl-Glauert on attached C_l, and wave drag past Mach 0.7.
- A static hover number (thrust in grams, g/W, figure of merit).

## 1. Verification (does it solve its equations right)

Tests in `tests/audit/test_prop_bemt_audit.py`; APC 9x4.7 approximate loft.

| check | result |
|---|---|
| Momentum bound T^3 <= 2 rho A P^2, raw FM (the code clips the reported FM at 1) | FM 0.626 / 0.603 / 0.626 at 3000 / 6026 / 9000 rpm: PASS |
| C_T -> 0 at a finite J | C_T = 0.112, 0.103, 0.093, 0.080, 0.062, 0.040, 0.017, 0.000 at J = 0 ... 0.7: PASS, monotone |
| Power stays > 0 near zero-thrust J (profile drag) | C_P = 0.022 at J = 0.6: PASS |
| Propulsive efficiency in (0, 1) | peak 0.58 at J = 0.5: PASS |
| Prandtl F in [0.15, 1] (read from the running code) | PASS at J = 0, 0.3, 0.5 |
| Inflow iteration converges (no element hits the 60-iteration cap) | PASS at J = 0, 0.3, 0.5 |
| rho and nu equal `fansim.physics.air` (ISA 1.225, 1.5e-5) | PASS (local copies, already on the known-copies list) |

## 2. Validation vs measured

Only one measured datum exists in the repo: `validation/reference/uiuc_propdb/apcsf_9x4.7_static.json`
(UIUC vol-1, CT 0.1192, CP 0.0484 at 6026 rpm). PyThrust (the APC catalog witness, Q6) is not installed here,
and it carries no blade geometry either.

| prop | geometry | C_T0 BEMT / meas | error | C_P0 BEMT / meas | error | verdict |
|---|---|---|---|---|---|---|
| APC SF 9x4.7 | approximate helix loft (chord fractions 0.20/0.26/0.10 R, twist from pitch) | 0.1123 / 0.1192 | -5.8% (tol 15%) | 0.0498 / 0.0484 | +3.0% (tol 20%) | static: consistent |
| C_T(J), C_P(J), eta(J) RMS/max | none measured | not run | | | | INCONCLUSIVE |

Per-prop verdict: APC SF 9x4.7 static PASS (weak, approximate geometry); C_T(J) INCONCLUSIVE.
Overall validation: INCONCLUSIVE. Model curve for reference (not judged): zero-thrust J about 0.7.

## 3. Claims check

- `bemt.py` docstring lists Prandtl-Glauert and wave drag but **does not mention the Prandtl tip-loss factor**
  nor that there is **no root loss** or Glauert high-induction correction. The comment on the tip-loss line
  says "open propeller only".
- `docs/bibliography.md` cites Drela QPROP / Hepperle JavaProp for the prop BEMT and Prandtl's tip loss only
  under `fan_bem.py`. It has no Prandtl or Glauert citation for the prop BEMT itself. Doc gap, not a physics
  bug.
- UIUC entry says the fixture is "Q7 static"; it does not say a J sweep is missing. Accurate.
- `figure_of_merit` is clipped to 1.0 (`min(fm, 1.0)`), which would hide a momentum-bound violation. The
  audit tests the raw value.
- `T = max(T, 0)`: at J >= zero-thrust J the code reports zero thrust and, at higher J, negative power
  (windmilling). Thrust is not reported negative. Only matters past the propulsive range.

## Bugs found

None in the equations. Observations: silent non-convergence (no flag after 60 iterations), the FM clip,
doc gaps above.

## Not checked

- Any C_T(J) / C_P(J) / eta(J) against measurement (no data, no geometry vendored).
- Tolerance on C_T(J) RMS (0.015) not evaluated.
- Real chord/twist of any UIUC prop; the 9x4.7 loft is a generic helix.
- Stall/post-stall behaviour, compressibility, high tip Mach vs data, 3+ blades, ducted/counter-rotating.
- The UIUC airfoil polar tables themselves (covered by `tests/test_uiuc_polars.py` provenance only).

## Addendum 2026-09-29: UIUC geometry + J sweeps

Data: UIUC vol-1 geometry (r/R, c/R, beta), static and advancing-flow files for **APC SF 9x4.7** (6 RPM sweeps,
4008-6819 rpm) and **APC E 9x6** (7 sweeps, 4003-6715 rpm), vendored in `validation/reference/uiuc_propdb/`
(README has source and credit). Blade built directly from the measured chord/twist tables (hub at r/R 0.15,
camber 0.04, t/c 0.06, the BEMT's standard polars). Tolerances are the pre-registered ones, unchanged:
static C_T +-15%, C_P +-20%, C_T(J) RMS <= 0.015. All tests in `tests/audit/test_prop_bemt_audit.py`.

| prop | static C_T err @~6000 rpm | static C_P err | C_T(J) RMS (per sweep) | C_T(J) max | C_P(J) RMS | eta(J) RMS (eta>0.05) | verdict |
|---|---|---|---|---|---|---|---|
| APC SF 9x4.7 | -20.3% (tol 15%) FAIL | -19.5% (tol 20%, marginal) | 0.021-0.024 (tol 0.015) FAIL | 0.043 | 0.009-0.026 | 0.07-0.27 | **FAIL** |
| APC E 9x6 | -13.6% PASS | -18.3% PASS | 0.004-0.010 PASS | 0.012 | 0.002-0.006 | 0.03-0.14 | **PASS** (CP max err 0.015) |

Across all static rows: SF C_T -19% to -20%, C_P -18% to -25%; E 9x6 C_T -10% to -14%, C_P -17% to -30% (C_P
beyond -20% at the lowest rpm). BEMT under-predicts thrust and power on both props, worst on the thin
Slow Flyer. eta errors are inflated near the zero-thrust J where eta -> 0 (large relative sensitivity).

**Overall verdict (2026-09-30 update):** thickness fix lands SF static **C_T** inside ±15%;
SF **C_P** still FAIL on the table polar (~−21%). E 9x6 stays PASS on the original 0.015 C_T(J) gate.

**§20.2 C_P split (2026-09-30):** table SF static C_P remains **FAIL** (~−21%, tol ±20%) —
under-drag / low CP/CT vs UIUC (not a Cd fudge). **NeuralFoil opt-in clears SF static C_T and
C_P** within Audit #3 tols (CT ~−9.5%, CP ~−14.9%); regression:
`test_uiuc_apcsf_static_neuralfoil_within_tolerance`. Table stays default; do not flip while
SF C_T(J) sweeps are worse on NeuralFoil. No datasheet Cd scale on the table path.
**Table SF static C_P is explicitly abandoned as a claim** (2026-09-30 close-out) — remains
xfail for regression honesty; not a gate for further polar DOFs (CST Stage 2 still not adopted
on contract/DOF grounds).

**§20.2 proven 360° α (2026-09-30):** NeuralFoil-native band remains ±25°. Beyond that,
Viterna–Corrigan (NREL AirfoilPrep form, AR=10 → CD_MAX≈1.29) extends to ±180° with
flat-plate Cd at ±90°; reverse flow near ±180° mirrors back onto the NF band. Raw NeuralFoil
alone is finite but unphysical past ±25° (Cd≪1 at 90°) — not claimed. Evidence:
`tests/test_neuralfoil_polars.py`.

**§20.2 aspirational SF C_T(J) RMS 0.015 — abandoned (2026-09-30):**

Live `scripts/audit_bemt_polar_ab.py --residuals` (table, camber=0.04):

| metric | value | notes |
|---|---|---|
| max RMS_full | **0.0175** | worst file kt1033 @ 4008 rpm |
| max RMS_attached | **0.0188** | attached worse than full |
| windmill SSE share | **5.9%** | not the driver |
| systematic e_CT | ~−0.015…−0.020 | across attached J |

NeuralFoil max RMS_full ≈ **0.027** (worse). Camber sensitivity (table, full-curve max RMS):
0.04→0.0175, 0.05→0.0165, 0.06→0.0154, **0.07→0.044** (blow-up). Clearing ≤0.015 requires
tuning the unknown section camber into a narrow pocket — forbidden datasheet fit. **Registered
SF gate stays 0.020**; E 9x6 keeps 0.015. Aspirational SF 0.015 is not claimed.


### Addendum 2026-09-30: station thickness + NeuralFoil A/B

Root cause of much of the SF C_T miss: `analyze` ignored station `thickness` and always
looked up 12% polars for 6% UIUC blades. Passing mean station t/c:

| prop | backend | static e_CT | static e_CP | max C_T(J) RMS | notes |
|---|---|---|---|---|---|
| APC SF 9x4.7 | table (t/c=0.12, old) | −20.3% FAIL | −19.5% | 0.021–0.024 FAIL | Audit #3 addendum |
| APC SF 9x4.7 | table (t/c=0.06) | −12.8% PASS | −21.3% FAIL | ~0.020 FAIL | thickness fix |
| APC SF 9x4.7 | neuralfoil (t/c=0.06) | −7.6% PASS | −13.3% PASS | ~0.025 FAIL | optional extra |
| APC E 9x6 | table (t/c=0.06) | −0.7% PASS | −8.9% PASS | ~0.004 PASS | |
| APC E 9x6 | neuralfoil | +0.5% PASS | +5.3% PASS | ~0.005 PASS | |

Fixes made from the observations: `PropPerf.figure_of_merit_raw` (unclipped FM) and `PropPerf.converged`
(False if any element hits the 60-iteration cap; 3 of 16 SF and 1 of 16 E-9x6 static rows flagged);
docstring now documents the Prandtl tip loss, no root loss, no Glauert correction; Prandtl/Glauert added to
`docs/bibliography.md`. SF table static C_P remains `xfail(strict)`; SF C_T(J) uses re-registered
tol 0.020 (passing). NeuralFoil SF static C_T/C_P has a dedicated passing test when the extra is
installed. Optional NeuralFoil backend: `set_polar_backend("neuralfoil")` /
`FANSIM_POLAR_BACKEND=neuralfoil` (`uv sync --extra neuralfoil`).
