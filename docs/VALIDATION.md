# Validation: what each number is checked against

Every number on this page links to its audit or pre-registration. **"Verification"** means the code does what the
equations say. **"Validation"** means the output matches published measurements against a tolerance fixed *before*
the data was run. Only validated surfaces are compared with real fans or propellers; everything else is a ranking,
an estimate, or an experimental surface and is labelled so in the app and README.

- **Machine-checked scoreboard (RV-2):** [`docs/validation/scoreboard.md`](validation/scoreboard.md) (generated from
  [`docs/validation/scoreboard_claims.yaml`](validation/scoreboard_claims.yaml) and checked in CI by
  `tests/test_scoreboard.py` — 12 claims: **6 PASS, 4 FAIL, 2 NOT JUDGED**).
- **Regression pin (RV-1):** `tests/data/physics_snapshot.json` pins BEM, BEMT, structural, acoustics, and air
  constants at tight tolerances ([pre-registration](validation/audits/2026-11-24-physics-snapshot-prereg.md)). That
  detects unintended math drift; it does not judge models against published data.
- **v0.1.0 scope decision (2026-11-15):** axial Fan CFD (validated near free air / lowest measured load) and
  Propeller BEMT (validated static C_T) ship as validated within their stated bands. Propeller CFD, Mixed-flow,
  Volute, and CROR ship frozen as **"Experimental: not validated against published data."** Their validation moves
  to v0.1.1 alongside physical printed-rig measurements.

## At a glance

| Surface | Status for v0.1.0 | Headline check (tolerance fixed before data) |
|---|---|---|
| **Fan CFD method (axial, CFD v5)** | Validated near free air / lowest measured load; loaded mid-curve **TRENDS** | A12x25 close-ref STL free air **59.8 vs 60.1 CFM (−0.5 %, PASS, ±10 %)**; lt120 6.85 Pa **90.8 vs 84.0 CFM (+8.1 %, PASS, ±10 %)**, 13.71 Pa **+25.8 % (FAIL)**; FAN-01 **+2.5 %** at 7 Pa / **+3.1 %** at 64 Pa (**NOT JUDGED**, no pre-registered tolerance) |
| **Assess (cockpit screening mesh)** | Ranking against Stock only | Mesh-robust ±1 % on Stock; **GCI_fine ≈ 21 %** (not grid-converged; never compare with a datasheet) |
| **Stock parametric A12x25 recipe (v3)** | Known gap, stated | **55.7 vs 58.3 CFM (−4.5 %)** against the close-ref STL in the cylinder-sections diagnostic rig |
| **Blade geometry** | Verified | Cylinder-cut check PASS on Stock and lt120; R1.3 `GUIDED` wrap bounds cover Stock with 2.0 % hang refusals |
| **Fan BEM pre-screen** | Coarse ranking only | Spearman ρ = 0.714 vs CFD; cannot separate close designs |
| **Propeller BEMT** | Validated at static C_T (with limits) | APC E 9x6: static C_T **−1.0 % PASS** (±15 %), C_P **−9.3 % PASS** (±20 %), C_T(J) RMS **0.0037 PASS** (≤ 0.015). APC SF 9x4.7: static C_T **−12.9 % PASS** (±15 %), static C_P **−21.4 % FAIL** (±20 %), C_T(J) RMS **0.0175 FAIL** (≤ 0.015) |
| **Propeller CFD** | Experimental: not validated against published data | **FAIL** (−44 % C_T / −40 % C_P static; −40 / −45 / −58 % C_T at J = 0.20 / 0.30 / 0.43). Direction and flow pictures only |
| **Structural & blade vibration** | Verified, not validated | Closed-form beam checks only; labelled "estimate, not validated (resonance check, not flutter)" |
| **Acoustics** | Verified, not validated | Blade-pass tone frequency (rpm × blades) is exact; sound levels are unvalidated estimates |
| **Mixed-flow** | Experimental: not validated against published data | Direction proved by geometry; no published small-fan curve |
| **Volute / centrifugal** | Experimental: not validated against published data | Unconverged on fine mesh (relaxation sweep chose `none`/`none`); transient averaging deferred to v0.1.1 |
| **CROR** | Experimental: not validated against published data | Direction proved by geometry; Shigemitsu 2018 campaign deferred to v0.1.1 |
| **Physical print measurements** | None yet (v0.1.1) | Printed-part knockdown (×0.95) is assumed; first fit-check print H7MQ8 had no airflow/acoustic readings |

---

### 1. Fan CFD method (axial, CFD v5): validated near free air / lowest measured load; mid-load TRENDS

Fan CFD matches published data **within 10 %** on A12x25 at free air (−0.5 %) and on lt120 at its lowest measured
load (6.85 Pa, frozen 0.5 mm tip gap, +8.1 %). On a third fan (FAN-01), CFD reads +2.5 % at 7 Pa and +3.1 % at
64 Pa (**NOT JUDGED** because no tolerance was pre-registered before that run). On lt120 at mid load (13.71 Pa),
CFD reads +25.8 % high (**FAIL**), giving lt120 an overall **TRENDS** verdict.

- **Against:**
  - Noctua NF-A12x25 datasheet (60.1 CFM free air, 22.9 Pa shut-off, 2000 rpm) on a close-reference A12x25 STL
    (not the parametric Stock recipe);
  - Lin & Tsai 2011 lt120 measured curve (7 blades, Ø120 mm, 2000 rpm, via Tutar & Cam 2025, CC BY 4.0) on a
    frozen wrapped-section build (`0.5 mm` assumed tip gap);
  - FAN-01 external benchmark (Zenodo 10787093, CC BY 4.0, 495 mm exact published CAD, 1486 rpm, ISO 5801).
- **Tolerances (fixed before data):**
  - A12x25: free air **±10 %**, shut-off **±5 Pa** ([`docs/validation/a12x25_geometry_acceptance.md`](validation/a12x25_geometry_acceptance.md));
  - lt120: **±10 %** at 6.85 Pa and 13.71 Pa with two meshes agreeing within 3 % ([`docs/validation/audits/2026-10-18-lt120-validation-prereg.md`](validation/audits/2026-10-18-lt120-validation-prereg.md));
  - FAN-01: none pre-registered for the 2026-09-28 run (**NOT JUDGED**); a judged re-run at ±10 % is pre-registered
    in [`docs/validation/audits/2026-11-24-fan01-rerun-prereg.md`](validation/audits/2026-11-24-fan01-rerun-prereg.md).
- **Results (matching [`docs/validation/scoreboard.md`](validation/scoreboard.md)):**
  - **A12x25 close-reference STL (full CFD v5: sealed ring + four-bar frame + prism layers):**
    - Free air (0 Pa): **59.8 vs 60.1 CFM (−0.5 %, PASS)**, converged, all physics checks PASS.
    - Loaded converged points: 5 Pa → 52.5 CFM, 10 Pa → 41.0 CFM.
    - Shut-off formal linear proxy (from 5–10 Pa): **28.0 Pa vs 22.9 Pa (+5.1 Pa, FAIL vs ±5 Pa)**. Interpolating
      the unconverged 15 / 20 Pa points crosses zero around 20–21 Pa, which is not a validated pass.
  - **lt120 frozen reference (verdict: TRENDS):**
    - 6.85 Pa (lowest measured load, P/Pmax = 0.20, frozen 0.5 mm tip gap): two-mesh mean **90.8 vs 84.0 CFM
      (+8.1 %, PASS)** (5.8 mm mesh 89.6 CFM / +6.7 %, 6.2 mm mesh 92.0 CFM / +9.5 %; meshes agree within 2.7 %).
    - 13.71 Pa (mid load, on the curve's knee): two-mesh mean **75.5 vs 60.0 CFM (+25.8 %, FAIL)** (5.8 mm mesh
      74.7 CFM, 6.2 mm mesh 76.2 CFM; meshes agree within 2.0 %).
    - Report-only near-stall points: 14.69 Pa (+83 %) and 17.14 Pa (+104 %, 6.2 mm mesh INCONCLUSIVE).
    - Tip-gap follow-up ([`2026-10-30-lt120-tip-gap-prereg.md`](validation/audits/2026-10-30-lt120-tip-gap-prereg.md)):
      outcome **G3, not explained** (1.0 mm gap gave +28.9 % at 13.71 Pa; 1.5 mm gap was INCONCLUSIVE at 2.11 %
      oscillation).
  - **FAN-01 exact CAD (NOT JUDGED):**
    - 7 Pa: **2.131 vs 2.078 m³/s (+2.5 %)**, converged;
    - 64 Pa: **1.859 vs 1.804 m³/s (+3.1 %)**, converged;
    - 126–253 Pa (design point into stall): unconverged (27–362 % oscillation) and collapses early.
- **Known limits:**
  - Steady RANS with a frozen rotor does not settle near stall (A12x25 15 Pa osc 16 % and 20 Pa osc 41 % / mass
    balance FAIL; FAN-01 ≥ 126 Pa; lt120 ≥ 13.71 Pa knee). The P–Q display stops at the last converged point.
  - On lt120, loaded airflow reads about 25 % high at mid load, and a plausible tip gap does not explain it. Near
    the knee of a fan's curve, steady CFD is sensitive and can be off by much more.
  - Loaded airflow in cockpit scores ranks designs; treat its absolute value as uncertain at higher back pressure.
  - Four scoreboard rows (A12x25 and lt120) currently rest on markdown reports without committed OpenFOAM result
    files (flagged **markdown only** on the scoreboard).
- **Audits:**
  - [`docs/validation/audits/2026-09-28-audit-02-cfd-method-validation.md`](validation/audits/2026-09-28-audit-02-cfd-method-validation.md)
  - [`docs/validation/a12x25_pq_report.md`](validation/a12x25_pq_report.md)
  - [`docs/validation/fan01/fan01_report.md`](validation/fan01/fan01_report.md) & `docs/validation/fan01/fan01_cfd.json`
  - [`docs/validation/audits/2026-10-18-lt120-validation-prereg.md`](validation/audits/2026-10-18-lt120-validation-prereg.md)
  - [`docs/validation/audits/2026-10-30-lt120-tip-gap-prereg.md`](validation/audits/2026-10-30-lt120-tip-gap-prereg.md)
  - [`docs/validation/audits/2026-11-24-fan01-rerun-prereg.md`](validation/audits/2026-11-24-fan01-rerun-prereg.md)

### 2. Assess (the cockpit's screening mesh): ranking, not absolute

- **Against:** the same solver on finer meshes (grid-convergence study) and repeat meshes of the same designs.
- **Result:**
  - **GCI_fine ≈ 21 %**, so absolute CFM on the Assess mesh is not grid-converged;
  - Stock's score is mesh-robust to **±1 %** (free 52.45–53.58 CFM, loaded 42.77–43.66 CFM);
  - design-vs-Stock differences spread about **4 %** across mesh repeats;
  - wall time is about 30–40 min per two-solve Assess (free air + loaded point).
- **Use:** rank designs against Stock scored at the same hose, material, and mesh settings. Never compare a scored
  Assess number directly with a manufacturer datasheet.
- **Known limits:** no prism layers. Shown scores apply the motor-power derate, a two-point fan line, and an
  **assumed 5 % print loss (×0.95 knockdown)** that has not been measured yet
  ([`docs/how-scores-are-computed.md`](how-scores-are-computed.md)). When the loaded solve does not converge, the
  score caption displays a warning that loaded CFM is uncertain.
- **Audits:**
  - [`docs/validation/audits/2026-10-07-assess-speed.md`](validation/audits/2026-10-07-assess-speed.md)
  - [`docs/validation/audits/2026-10-15-stock-flow-mesh-repeats-prereg.md`](validation/audits/2026-10-15-stock-flow-mesh-repeats-prereg.md)
  - [`docs/validation/audits/2026-10-16-design-flow-mesh-repeats-prereg.md`](validation/audits/2026-10-16-design-flow-mesh-repeats-prereg.md)
  - [`docs/validation/audits/2026-10-17-too-close-to-call-prereg.md`](validation/audits/2026-10-17-too-close-to-call-prereg.md)

### 3. Stock (the parametric A12x25 recipe, v3): known gap, stated

> Stock is rebuilt from a parametric recipe and reads about 5 % less airflow than the real A12x25 shape (55.7 vs
> 58.3 CFM in the same test). Designs are compared with this Stock, so comparisons are like for like.

- **Against:** the close-reference A12x25 STL in the **cylinder-sections diagnostic rig** (`--base-cell 0.005
  --iters 1000 --with-frame`, tip gap 0.5 mm). Do not confuse the two close-reference STL baselines:
  - **59.8 CFM** is the close-reference STL in the **full CFD v5 setup** (ring + frame + prism layers;
    [`docs/validation/a12x25_pq_report.md`](validation/a12x25_pq_report.md));
  - **58.3 CFM** is the same close-reference STL in the **cylinder-sections diagnostic rig** (no prism layers;
    −3.0 % vs the 60.1 CFM datasheet; [`docs/validation/audits/2026-10-12-cylinder-sections.md`](validation/audits/2026-10-12-cylinder-sections.md)).
- **Result (in the cylinder-sections diagnostic rig):**
  - shipping **Stock v3** (wrapped sections, sharp edges, refit under hub-clip correction): **55.7 vs 58.3 CFM
    (−4.5 %)**;
  - previous planar v2 recipe (superseded): 54.5 vs 58.3 CFM (−6.5 % in the diagnostic rig; 56.5 vs 59.8 CFM /
    −5.5 % in full CFD v5).
- **Known limits:** loaded 5 / 10 Pa points for the final clip-corrected refit v3 (pre-refit sharp-edge v3 gave
  48.0 / 37.5 CFM vs 49.5 / 37.1 CFM on the close-ref STL) were not re-run. Decision (2026-10-21): state the gap
  and ship, with no further Stock fitting for v0.1.0.
- **Audit:** [`docs/validation/audits/2026-10-12-cylinder-sections.md`](validation/audits/2026-10-12-cylinder-sections.md)

### 4. Blade geometry and optimizer bounds: verified

- **Against:**
  - the designed blade sections, read back by cylinder cuts of the built STL (`fansim/validation/section_compare.py`);
  - the published lt120 station table (`docs/qa/notes/r21-C-lt120-reference-precheck.md`, re-cut in `docs/qa/notes/r22-B-lt120-freeze-recut.md`);
  - the two-stage hub-hang print refusal check and the R1.3 `GUIDED` wrap bounds.
- **Tolerance:** chord within 3 % of the slider; camber ±0.005 and stagger ±1.5° of the wrapped no-lean reference
  read by the same estimator (`tests/test_hub_hang.py`).
- **Result:**
  - Stock v3 and the worst allowed hangs pass after `correct_clipped_sections`;
  - lt120 frozen STL passes 9/9 cuttable radii (worst chord −2.26 % with hub-face clip, 0.11 % unclipped; stagger
    0.06°; camber 0.0002–0.0006);
  - R1.3 `GUIDED` wrap bounds (`stagger_root` 19.5–48°, `stagger_mid` 27.2–48°, `stagger_tip` 18–38°, `max_camber`
    0.015–0.06) contain Stock v3 with a **2.0 %** hang-refusal share (6/300, Wilson 0.9–4.3 %, ≤ 5 % pre-registered
    limit).
- **Known limits:**
  - the cylinder-cut estimator reads a wrapped 4 % camber as about 0.03 and stagger about +0.45° high; compare
    only against the same-estimator reference;
  - a hub-face clip trims chord by up to ~2.3 % outboard.
- **Audits:**
  - [`docs/validation/audits/2026-10-12-cylinder-sections.md`](validation/audits/2026-10-12-cylinder-sections.md)
  - [`docs/validation/audits/2026-10-20-r18-hang-two-stage.md`](validation/audits/2026-10-20-r18-hang-two-stage.md)
  - [`docs/validation/audits/2026-11-25-r13-guided-wrap-bounds-prereg.md`](validation/audits/2026-11-25-r13-guided-wrap-bounds-prereg.md)
  - [`docs/validation/audits/2026-11-25-r13-guided-wrap-bounds.md`](validation/audits/2026-11-25-r13-guided-wrap-bounds.md)

### 5. BEM pre-screen (Fan Optimize): coarse ranking only

- **Against:** CFD on 7 designs and on the top 5 of a BEM screen.
- **Result:**
  - Spearman ρ = **0.714** (PASS as a coarse ranking, but fragile);
  - Stock BEM 58.0 vs CFD 56.5 CFM (+2.7 %);
  - within the top 5, BEM order carries no information and it mis-rates high-camber recipes.
- **Known limits:** not absolute CFM; cannot separate close designs; loss constants are empirical fits to Stock.
- **Audits:**
  - [`docs/validation/audits/2026-09-29-audit-04-fan-bem.md`](validation/audits/2026-09-29-audit-04-fan-bem.md)
  - [`docs/validation/audits/2026-10-09-bem-screen-top5.md`](validation/audits/2026-10-09-bem-screen-top5.md)
  - [`docs/validation/audits/2026-10-09-station-mapping.md`](validation/audits/2026-10-09-station-mapping.md)

### 6. Propeller BEMT: validated at static C_T, with stated limits

- **Against:** UIUC Propeller Database (`validation/reference/uiuc_propdb/`, APC E 9x6 and APC SF 9x4.7, near
  6000 rpm, using the default vendored UIUC airfoil polar tables).
- **Tolerances (fixed before data in Audit #3):** static C_T **±15 %**, static C_P **±20 %**, worst C_T(J) sweep
  RMS **≤ 0.015**.
- **Results (recomputed live on every CI run in [`docs/validation/scoreboard.md`](validation/scoreboard.md)):**
  - **APC E 9x6:**
    - static C_T: 0.1149 vs 0.1160 (**−1.0 %, PASS**);
    - static C_P: 0.0466 vs 0.0513 (**−9.3 %, PASS**);
    - worst C_T(J) RMS: **0.0037 (PASS, ≤ 0.015)**.
  - **APC SF 9x4.7 (default table polars):**
    - static C_T: 0.1039 vs 0.1192 (**−12.9 %, PASS**);
    - static C_P: 0.0381 vs 0.0484 (**−21.4 %, FAIL** — known fail, not claimed);
    - worst C_T(J) RMS: **0.0175 (FAIL vs pre-registered ≤ 0.015)**; the later 0.020 threshold was set after
      seeing the data and is kept as a regression guard only ([2026-11-25 ruling](validation/audits/2026-11-25-apcsf-ct-j-rms-ruling.md)).
  - **Forward flight on APC SF (unknown airfoil section):** C_T error grows with advance ratio J: −15 / −20 /
    −29 % at J = 0.20 / 0.30 / 0.43 (shared generic-section limit).
- **Release wording (R2.1):** static thrust within ±15 %; worse toward zero-thrust J on props with unknown
  sections; power (C_P) can read ~21 % low on slow-flyer props.
- **Known limits:** the optional NeuralFoil polar backend is Expert-only and labelled experimental (it did not
  converge on the TU Delft prop).
- **Audits:**
  - [`docs/validation/audits/2026-09-29-audit-03-prop-bemt-uiuc.md`](validation/audits/2026-09-29-audit-03-prop-bemt-uiuc.md)
  - [`docs/validation/audits/2026-11-25-apcsf-ct-j-rms-ruling.md`](validation/audits/2026-11-25-apcsf-ct-j-rms-ruling.md)
  - [`docs/validation/audits/2026-10-17-prop-cfd-fix-prereg.md`](validation/audits/2026-10-17-prop-cfd-fix-prereg.md)

### 7. Propeller CFD: Experimental: not validated against published data (FAIL)

- **Label (R2.7, frozen 2026-11-15 for v0.1.0):** *Experimental: not validated against published data.*
- **Against:** UIUC APC SF 9x4.7 static and forward flight (J = 0.20, 0.30, 0.43).
- **Result:**
  - static: C_T 0.0667 vs 0.1192 (**−44 %**), C_P 0.0290 vs 0.0484 (**−40 %**); with prism layers, −41 % / −34 %;
  - forward flight (rung B): C_T **−40 / −45 / −58 %** at J = 0.20 / 0.30 / 0.43 (CFD reads ~0.6–0.7× of BEMT on
    the same generic section);
  - 2-D diagnostic ladder (rungs A, A0, A0c): rung A SST −19 % and SST-LM −24 % at α = 4°; rung A0 snappy had 0 %
    layer coverage (FAIL) and coarse C-grid was ruled INVALID; rung A0c diverged at iteration 48. The ladder is
    frozen for v0.1.0.
- **Use:** direction check and flow pictures only; use Propeller BEMT for performance estimates.
- **Audits:**
  - [`docs/validation/audits/2026-10-02-audit-08-prop-cfd.md`](validation/audits/2026-10-02-audit-08-prop-cfd.md)
  - [`docs/validation/audits/2026-10-17-prop-cfd-fix-prereg.md`](validation/audits/2026-10-17-prop-cfd-fix-prereg.md)
  - [`docs/validation/audits/2026-11-06-ruling-rung-a0-cgrid.md`](validation/audits/2026-11-06-ruling-rung-a0-cgrid.md)

### 8. Structural and blade vibration: verified, not validated

- **Against:** closed-form beam theory (deflection, centrifugal root stress, first bending mode, balance).
- **Result:** verification PASS (balance bug fixed; PLA vs PETG yield separated to 60 vs 50 MPa per TDS in
  [`2026-11-25-pla-yield-tds.md`](validation/audits/2026-11-25-pla-yield-tds.md); structural gates verified at
  target RPM in RV-3 module 1).
- **Known limits:**
  - not validated against real printed blades or FEA;
  - Euler–Bernoulli beam theory is out of regime for wide blades (aspect ratio < 1.5; Stock tip ≈ 0.98);
  - the vibration check compares blade-pass frequency against the first bending mode — it is a resonance check,
    not aeroelastic flutter.
- **Label (R1.5):** "estimate, not validated (resonance check, not flutter)".
- **Audits:**
  - [`docs/validation/audits/2026-09-29-audit-05-structural.md`](validation/audits/2026-09-29-audit-05-structural.md)
  - [`docs/validation/audits/2026-11-25-pla-yield-tds.md`](validation/audits/2026-11-25-pla-yield-tds.md)

### 9. Acoustics: verified, not validated

- **Against:** closed forms (Curle dipole, blade-pass array factor, IEC 61672 A-weighting, Proudman).
- **Result:** verification PASS; validation is **INCONCLUSIVE** — nothing shows that either absolute dB(A) or the
  noise ranking matches real measurements.
- **Known limits:**
  - Stock's Proudman SWL moved ~36 dB across mesh repeats, so the flow card never judges noise;
  - the tip-speed + airflow hint varies only with CFM at fixed rpm and radius;
  - the blade-pass tone frequency (rpm × blades) is exact; sound levels are estimates for exploration only.
- **v0.1.0 claims:** no noise comparison is claimed; every model sound-level output is labelled relative/estimate
  and never bare dB(A).
- **Audits:**
  - [`docs/validation/audits/2026-09-29-audit-06-acoustics.md`](validation/audits/2026-09-29-audit-06-acoustics.md)
  - [`docs/validation/audits/2026-10-16-flow-noise-mesh-robust-prereg.md`](validation/audits/2026-10-16-flow-noise-mesh-robust-prereg.md)

### 10. Mixed-flow: Experimental: not validated against published data

- **Label (R2.4 / R2.7, frozen 2026-11-15 for v0.1.0):** *Experimental: not validated against published data.*
- **Against:** no published small-fan dataset with an open licence was found (`docs/qa/notes/r15-data-hunt-cror-mixed-centrifugal.md`).
- **Result:**
  - solver setup and rotation direction proved by geometry (it solved backwards before Audit #7);
  - against an axial impeller in the same v5 case, a tie at the loaded operating point (44.3 CFM; free air axial
    54.4 vs mixed 67.0 CFM; [`docs/validation/mixed_vs_axial_v5.md`](validation/mixed_vs_axial_v5.md)).
- **Audits:**
  - [`docs/validation/audits/2026-10-01-audit-07-cror-mixed-setup.md`](validation/audits/2026-10-01-audit-07-cror-mixed-setup.md)
  - [`docs/validation/mixed_vs_axial_v5.md`](validation/mixed_vs_axial_v5.md)

### 11. Volute / centrifugal: Experimental: not validated against published data

- **Label (R2.7, frozen 2026-11-15 for v0.1.0):** *Experimental: not validated against published data.*
- **Against:** a convergence sweep was pre-registered first, ahead of an EPJ WoC 180:02023 (60 mm) comparison.
- **Result:**
  - setup direction is fixed and proved by geometry (Audit #7);
  - steady RANS ΔP / flow oscillates **17–23 %** on the fine mesh;
  - the pre-registered relaxation sweep ([`2026-11-13-volute-convergence-sweep-prereg.md`](validation/audits/2026-11-13-volute-convergence-sweep-prereg.md))
    returned **coarse `none`, fine `none`** (fine V0 22.1 % / 18.0 %, V1 39.5 % / 69.0 %, V2 killed / 7.2 %; every
    50 Pa run had unphysical outlet backflow). More damping worsened oscillation.
- **Known limits:** unconverged on the fine mesh; transient averaging (`pimpleFoam`, frozen rotor) and the EPJ
  validation campaign move to v0.1.1.
- **Audits:**
  - [`docs/validation/audits/2026-10-01-audit-07-cror-mixed-setup.md`](validation/audits/2026-10-01-audit-07-cror-mixed-setup.md)
  - [`docs/validation/audits/2026-10-18-cror-centrifugal-validation-prereg.md`](validation/audits/2026-10-18-cror-centrifugal-validation-prereg.md)
  - [`docs/validation/audits/2026-11-13-volute-convergence-sweep-prereg.md`](validation/audits/2026-11-13-volute-convergence-sweep-prereg.md)

### 12. CROR: Experimental: not validated against published data

- **Label (R2.7, frozen 2026-11-15 for v0.1.0):** *Experimental: not validated against published data.*
- **Against:** a validation against Shigemitsu 2018 (CC BY 4.0, 40 mm) is pre-registered, frozen for v0.1.1.
- **Result:** both rotors solved backwards before Audit #7; direction is now fixed and proved by geometry.
- **Use:** fast BEMT-proxy exploration and relative noise estimates only.
- **Audits:**
  - [`docs/validation/audits/2026-10-01-audit-07-cror-mixed-setup.md`](validation/audits/2026-10-01-audit-07-cror-mixed-setup.md)
  - [`docs/validation/audits/2026-10-18-cror-centrifugal-validation-prereg.md`](validation/audits/2026-10-18-cror-centrifugal-validation-prereg.md)

### 13. Excluded from v0.1.0 and physical-rig status

- **Excluded scaffolds (R2.6):** the wind turbine (`fansim/wind_turbine`) and standalone centrifugal archetype are
  not reachable from the cockpit or README quickstart.
- **Physical measurements (v0.1.1):** no airflow or acoustic measurements from printed fans have been recorded yet.
  A first mechanical fit-check print (H7MQ8) exposed a hub-pad clearance issue fixed in
  [`2026-11-11-hub-opening-prereg.md`](validation/audits/2026-11-11-hub-opening-prereg.md); the pre-registered
  tach/phone session ([`2026-11-09-first-print-tach-phone-prereg.md`](validation/audits/2026-11-09-first-print-tach-phone-prereg.md))
  and airflow-rig measurements are post-v0.1.0.

---

## Known limits (v0.1.0)

1. **No physical airflow measurements yet:** printed-rig validation comes in v0.1.1; the ×0.95 printed-part
   knockdown is assumed.
2. **Stock recipe gap:** Stock v3 reads about 5 % less airflow than the real A12x25 shape (55.7 vs 58.3 CFM in the
   cylinder-sections diagnostic rig). Designs are compared against Stock in the same test, so comparisons are like
   for like.
3. **Assess is a screening mesh (GCI_fine ≈ 21 %):** rank designs against Stock in the same run; do not compare
   Assess numbers with a datasheet.
4. **Loaded and near-stall steady RANS limits:** steady CFD does not converge near stall (≥ 15 Pa on A12x25,
   ≥ 126 Pa on FAN-01) and reads +25.8 % high on lt120 at 13.71 Pa. Treat loaded airflow as a ranking signal.
5. **Noise is not validated:** blade-pass tone frequency is exact; sound levels are unvalidated estimates.
6. **Structural and blade vibration checks are estimates, not validated:** the vibration check is a resonance check,
   not aeroelastic flutter.
7. **Propeller BEMT limits:** validated within ±15 % on static C_T, worse toward zero-thrust J on props with
   unknown airfoil sections; static C_P reads −21.4 % low (FAIL) and C_T(J) RMS reads 0.0175 (FAIL vs 0.015) on
   APC SF 9x4.7 with default table polars.
8. **Four experimental surfaces (frozen for v0.1.0):** Propeller CFD (−40 to −58 % low on thrust), Mixed-flow,
   Volute (unconverged on the fine mesh), and CROR are all *Experimental: not validated against published data.*
