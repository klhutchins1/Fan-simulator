# Pre-registration amendments after grok round 17 (QA-46, QA-47, QA-48, R2.2a)

Written 2026-10-19, **before any CFD** for the cases concerned. The amendments come from what the *data sources* and
the *acceptance data* turned out to be (grok r17, `docs/qa/notes/r17-*.md`), not from any model-vs-data comparison.
Each amended document keeps its other rules.

## 1. R1.8 hang check (QA-46): two stages, not one factor

The original acceptance needs both:
- every design with built hang > 2 mm refused;
- at most 3 % false refusals.

On grok's r16 data no constant factor meets both. 1.75× misses S2_0269 (1.997 mm predicted, 2.25 mm built), and
1.78× refuses 4.5 %. **Recorded: the single-factor rule FAILS its own acceptance (1/123 missed).**

Amended design:
- **Stage 1, search prefilter (cheap):** refuse when `1.75 × designed hang > 2 mm`, as specified. It is judged on the
  false-refusal rule only: ≤ 3 % of designs with built hang ≤ 2 mm refused. grok r17 C: 0.4 % at the export hub.
- **Stage 2, authoritative (exact):** wherever the blade is actually built (the Assess CFD build and Export/Preview),
  measure the hang on the **built** solid: the lowest blade point below the hub face, from the realised loft. Refuse when it
  is > 2 mm, before CFD or export, with the plain message "the printed blade would hang X mm below the hub (limit 2 mm)".
- **Acceptance:**
  - on grok's r16/r17 designs, stage 2 refuses every design with built hang > 2 mm (by construction, so the test is that
    the measurement matches grok's built values within 0.05 mm on 10 designs, S2_0269 among them);
  - stage 1 meets ≤ 3 % false refusals.
- R1.7 (one hub for search, score and export) lands first, so both stages see the export hub.

## 2. CROR against Shigemitsu 2018 (QA-47)

- **S1 (rear-rotor share) is withdrawn.** The per-rotor curves and the 77 % share are the authors' URANS, not
  measurements, so comparing them would be CFD against CFD. They may be reported as "against the authors' CFD", but
  that is not a criterion.
- **Replacement shape criterion, S1′:** the measured total P–Q has a dip or plateau between peak ΔPs and shut-off
  (grok's 21 points). The model reproduces the *sign* of dΔP/dQ on the stable branch at 0.5, 0.75 and 1.0 × Q_o.
  S2, A1 and A2 are unchanged.
- **Stagger convention (Table 1 gives the value without a reference):** decided by **velocity-triangle consistency at
  the paper's stated design flow and rpm**, mid-span, front rotor. This is a geometry rule that uses no measured curve.
  - Q_o = 0.55 m³/min, a 25–37.2 mm annulus, so c_ax ≈ 15.4 m/s. U_mid at Ø31.1 mm, 15 000 rpm ≈ 24.4 m/s, so the
    relative flow angle is ≈ 57.7° from the axis.
  - Table value 31.2°. Read from the axis, the incidence is ≈ 26°, which is implausible. Read **from the rotation plane**
    (58.8° from the axis), the incidence is ≈ −1°.
  - **Ruling: Table 1 stagger is measured from the rotation plane**, for both rotors. Cursor maps it to fansim's own
    convention in the builder and states the mapping in `geometry.json`.
  - This overrides grok's from-the-axis suggestion, which was flagged as a guess.
- **Camber (not given):** a NACA 4-digit mean line at 4 % camber, 40 % position, on both rotors. This is the same
  generic section the prop builder uses, stated before any CFD. Thickness 0.8 mm, as in step 0.
- **Axial gap (no scaled drawing):** 0.25 × the mid chord of the front rotor (0.25 × 19.5 ≈ 4.9 mm). Approved.
- **Expectation, written now:** with generic camber, the absolute criteria A1/A2 are likely to miss. The pre-registered
  "trends validated" outcome exists for exactly this.

## 3. Centrifugal against EPJ 180:02023 (QA-48)

- The stand never reaches free delivery, because the curves end at the stand's own resistance (about 208 Pa at
  278 L/min, 9000 rpm). **A1 is restated:** ΔP within ±20 % at 0.4, 0.7 and 1.0 × **Q_max,meas**, the highest measured
  flow at 9000 rpm.
- Pressure definition: the paper's "working pressure p_b" in the outflow tube. The model reports static pressure at the
  equivalent outlet-tube section (same diameter, same distance from the volute exit if stated, else 3 tube diameters).
- The volute has no scaled drawing (Fig 2 is a render), so the log-spiral fallback in step 0 applies. The gap t is not
  given; rule: t = 0.5 mm (the moulded-wheel clearance class), stated now.
- S1 (peak-pressure location) stands only if a measured curve has an interior peak. If the curves rise monotonically to
  shut-off, S1 becomes "the model's ΔP at 0.4 × Q_max,meas exceeds its ΔP at 1.0 × Q_max,meas" (sign of the slope).

## 4. Prop CFD rung A (R2.2a)

- The reference is NACA 4406 (fansim's `naca4(0.04, 0.4, 0.06)`) at **Re 8×10⁴**: C_l 0.855 [0.847, 0.863],
  C_d 0.0201 (grok r17 A, NeuralFoil + XFOIL at Ncrit 9). Re 6×10⁴ is dropped as unusable.
- The measured E387 anchor shows these tools reading about 8 % high on C_l at 1×10⁵. So rung A's "SST-LM within 10 %
  of the reference" tolerance stands, and "SST ≥ 25 % below" is judged against the reference value as given (not
  corrected by 8 %).

## 5. Prop CFD rung B (R2.2b): J points

The ladder named J = 0.3 / 0.5 / 0.7 at 6000 rpm. In the UIUC tables, C_T is about 0 or negative at J ≈ 0.6–0.7
(kt1036: −0.038 at 0.753), so a relative tolerance there is meaningless. That is a property of the data, decided before
any run.

**Amended:**
- J = **0.20, 0.30, 0.43** at **6029 rpm**, all from one table (kt1035): C_T 0.092 / 0.076 / 0.050.
- **B1 (static-specific):** C_T within ±15 % at J = 0.30 **and** 0.43, while static is −44 %.
- **B2 (sectional):** C_T ≤ −30 % at all three J.
- Anything else, or a missing or unconverged point, is reported to Claude (INCONCLUSIVE when a point is missing).

Runner: `scripts/prop_cfd_jsweep.py` (Claude wrote it 2026-10-19 because the Cursor lane was idle). Its rules are unit
tested in `tests/test_prop_cfd_jsweep.py`.
