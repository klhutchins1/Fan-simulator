# r21 B: draft `docs/VALIDATION.md` (R3.8), written from the audits and data, not the board

QA bot, 2026-10-25. Master **5063a65**. Prereg **956b8ff** §B: a board mismatch is a difference beyond printed
rounding, or a different condition. Numbers marked "recomputed" were rechecked from the source tables for this draft.
This is a **draft for Cursor and Claude**. Claude still checks the numbers (R3.8). Proposed final path: `docs/VALIDATION.md`.

## Board mismatches found (list only, not fixed)

| # | board / user text | audits / data say | kind |
|---|---|---|---|
| M1 | README:52 "Stock recipe v2 … −5.5 %" | shipping Stock is v3: **55.7 vs 58.3 CFM, −4.46 %** recomputed (`2026-10-12-cylinder-sections.md:222,252`). Board R1.4's "−4.5 %" matches; the README is stale | stale value |
| M2 | `a12x25-reference.md:24` "validated on Stock: 59.8 vs 60.1" | 59.8 is the **close-ref STL** (audit-02, pq_report v5), not Stock | different object |
| M3 | close-ref STL "59.8 CFM" (audit-02, README) vs "58.3 CFM" (R1.4 wording) | same STL in **different rigs**: 59.8 is the full v5 setup (layers, matched surface level 3–4); 58.3 is the cylinder-sections diagnostic rig (`--base-cell 0.005 --iters 1000 --with-frame`). The 2.5 % difference is mesh/rig. R1.4's "in the same test" is correct, but VALIDATION.md must not put 58.3 beside 60.1 without saying which rig | different condition |
| M4 | `design-rules.md:43`, `adversarial-review.md:237` "~3–5 % discretization" | GCI_fine ≈ **21 %** on the Assess screening mesh (`2026-10-07-assess-speed.md:89`) | stale value |
| M5 | R1.4 "Where it goes" links "the `wrapped-sections` audit numbers" | no file named `wrapped-sections` in `docs/validation/audits/`. The numbers live in `2026-10-12-cylinder-sections.md` | dead link target |
| M6 | cockpit `fan_assess.py:409` "vs stock free 60 CFM" | 60 is the Noctua **datasheet**, not Stock. Stock's own Assess score is ≈ 49.6 (how-scores) | different object |
| M7 | cockpit `prop_tab.py` "CFD … ~35-45 % low" | audit-08 static −44 % C_T / −40 % C_P. R2.2b B2: −40 / −45 / **−58 %** at J 0.20 / 0.30 / 0.43. The range holds only near static | different condition |
| M8 | `figures.py:399` "CFD under-predicts static ~2×" | v5 shut-off 20–21 vs 22.9 Pa (−9 to −13 %) | no source |
| M9 | `fan_copy.py:129` BEM "~0.6×" | audit-04:80: stale (+2.7 % v2) | stale value |

No mismatch (all recomputed within printed rounding):
- −0.5 % (59.8/60.1 = −0.50 %); FAN-01 +2.6 % / +3.1 % (+2.55 % / +3.05 %);
- v2 −5.5 / −5.1 / −2.0 % (−5.52 / −5.14 / −1.95 %); STL −3 % vs datasheet (58.3/60.1 = −2.99 %);
- how-scores 49.6 (49.62), λ 0.954 (0.9536), 1907 rpm;
- board R2.1 C_T −13 % (audit-03 −12.8 %) and C_P −21 % (−21.3 %); board R2.5 17–23 % (audit-07:112).

---

## Draft text

# Validation: what each number is checked against

Every number links to its audit. "Verification" means the code does what the equations say. "Validation" means the
result matches a real measurement. Only validated surfaces are compared with real fans; everything else is a ranking
or an estimate and is labelled so in the app.

### 1. Fan CFD method (axial, CFD v5): validated
- **Against:** the Noctua NF-A12x25 datasheet (60.1 CFM free air, 22.9 Pa shut-off, 2000 rpm), run on a close-reference
  STL; and FAN-01, an external benchmark with exact published CAD and measured P–Q.
- **Tolerance:** free air ±10 % (interim), shut-off ±5 Pa (`docs/a12x25-reference.md:24`). FAN-01 is per the audit.
- **Result:**
  - close-ref free air **59.8 vs 60.1 CFM (−0.5 %)**, converged, all physics checks PASS;
  - 5 / 10 Pa: 52.5 / 41.0 CFM, converged;
  - FAN-01 **+2.6 % at 7 Pa and +3.1 % at 64 Pa**, converged.
- **Known limits:**
  - 15 Pa (oscillation 16 %) and 20 Pa (oscillation 41 %, mass balance FAIL) do not converge, because steady RANS
    cannot settle near stall;
  - shut-off ≈ 20–21 Pa is interpolated from unconverged points, and the automated proxy (28.0 Pa) is a formal FAIL;
  - one fan family, one speed;
  - a second published axial case (lt120, R1.1) is pending.
- **Audits:**
  - `docs/validation/audits/2026-09-28-audit-02-cfd-method-validation.md`;
  - `docs/validation/a12x25_pq_report.md` (v5 table);
  - `docs/validation/fan01/fan01_report.md:23-24`.

### 2. Assess (the cockpit's screening mesh): ranking, not absolute
- **Against:** the same solver on finer meshes (grid study) and repeat meshes of the same designs.
- **Result:**
  - GCI_fine ≈ **21 %**, so absolute CFM is not grid-converged;
  - Stock's score is mesh-robust to **±1 %** (free 52.45–53.58, loaded 42.77–43.66);
  - design-vs-Stock differences spread about 4 %;
  - wall time is about 21–24 min per Assess.
- **Use:** rank designs against Stock in the same Assess. Do not compare an Assess number with a datasheet.
- **Known limits:** no prism layers. Shown scores include the motor-power derate, a two-point fan line and an
  **assumed** ×0.95 printed-part knockdown, which has not been measured (`docs/how-scores-are-computed.md`).
- **Audits:**
  - `2026-10-07-assess-speed.md:89`;
  - `2026-10-15-stock-flow-mesh-repeats-prereg.md:64`;
  - `2026-10-16-design-flow-mesh-repeats-prereg.md`.

### 3. Stock (the parametric A12x25 recipe): known gap, stated
> Stock is rebuilt from a parametric recipe and reads about 5 % less airflow than the real A12x25 shape (55.7 vs 58.3
> CFM in the same test). Designs are compared with this Stock, so comparisons are like for like.

- **Against:** the close-ref STL in the same rig (cylinder-sections diagnostic rig, tip gap 0.5 mm, frame on).
- **Result:**
  - v3 (wrapped sections, refit under the clip correction) **55.7 vs 58.3 CFM (−4.5 %)**;
  - v2 (planar) 54.5 (−6.5 %);
  - in that rig the STL reads −3 % against the 60.1 datasheet.
- **Known limits:** loaded 5/10 Pa for the refit v3 (48.0 / 37.5) were not re-run. Kimball's decision (2026-10-21):
  state the gap and ship, with no more fitting for v0.1.0.
- **Audits:** `2026-10-12-cylinder-sections.md` (tables at lines 150–158 and 220–225; refit at 250–253).

### 4. Blade geometry: verified
- **Against:**
  - the designed sections, read back by cylinder cuts of the built STL (`fansim/validation/section_compare.py`);
  - the lt120 published table (r21 C pre-check).
- **Tolerance:** chord within 3 % of the slider; camber ±0.005 and stagger ±1.5° of the wrapped no-lean section read by
  the same estimator (`tests/test_hub_hang.py:155-157`).
- **Result:**
  - Stock and the worst allowed hangs pass after the clip correction;
  - lt120 built without the clip: 9/9 cuttable radii PASS, worst 0.11 % chord, 0.06° stagger, 0.0006 camber
    (`docs/qa/notes/r21-C-lt120-reference-precheck.md`).
- **Known limits:**
  - the estimator reads a wrapped 4 % camber as about 0.03, and stagger about +0.45° high; compare only against the
    same-estimator reference;
  - a hub-face clip trims chord by up to 2.3 % outboard.
- **Audits:**
  - `2026-10-12-cylinder-sections.md`;
  - `2026-10-20-r18-hang-two-stage.md` (print-hang refusal, stage 1 at 1.75 × designed, stage 2 built ≤ 2 mm).

### 5. BEM pre-screen (Fan Optimize): coarse ranking only
- **Against:** CFD on 7 designs, and on the top 5 of a BEM screen.
- **Result:**
  - Spearman ρ **0.714** (PASS as a ranking, but fragile);
  - Stock BEM 58.0 vs CFD 56.5 (+2.7 %);
  - within the top 5, BEM order carries no information, and it mis-rates high-camber recipes.
- **Known limits:** not absolute CFM; cannot separate close designs.
- **Audits:** `2026-09-29-audit-04-fan-bem.md`, `2026-10-09-bem-screen-top5.md`, `2026-10-09-station-mapping.md`.

### 6. Propeller BEMT: validated at static, with limits
- **Against:** UIUC propeller database (APC SF 9x4.7, E 9x6).
- **Tolerance:** C_T ±15 %, C_P ±20 %.
- **Result:**
  - SF static C_T **−12.8 % PASS**; C_P **−21.3 % FAIL**;
  - C_T error grows with J: −15 / −20 / −29 % at J 0.20 / 0.30 / 0.43.
- **Release wording (R2.1):** "±15 % at static; worse toward zero-thrust J on props with unknown sections".
- **Audits:** `2026-09-29-audit-03-prop-bemt-uiuc.md:112-154`; R2.2b results in `2026-10-17-prop-cfd-fix-prereg.md`.

### 7. Propeller CFD: FAIL, direction and sanity only
- **Against:** UIUC APC SF 9x4.7 static.
- **Result:**
  - C_T 0.0667 vs 0.1192 (**−44 %**), C_P 0.0290 vs 0.0484 (**−40 %**);
  - with layers, −41 / −34 %;
  - in forward flight, −40 / −45 / −58 % at J 0.20 / 0.30 / 0.43 (shared generic-section limit with BEMT).
- **Use:** checks that air goes the right way; use the BEMT numbers. A diagnostic ladder is under way (R2.2).
- **Audits:** `2026-10-02-audit-08-prop-cfd.md:46-92`, `2026-10-17-prop-cfd-fix-prereg.md`.

### 8. Structural and blade vibration: verified, not validated
- **Against:** closed-form beam theory (deflection, centrifugal stress, first bending mode, balance).
- **Result:** verification PASS (one balance bug fixed).
- **Known limits:**
  - not checked against any real blade or FEA;
  - Euler–Bernoulli is out of regime for wide blades (aspect < 1.5; Stock tip ≈ 0.98);
  - the "flutter" check is a resonance gate (BPF vs first mode), not aeroelastic flutter.
- **Label:** "estimate, not validated" (R1.5).
- **Audit:** `2026-09-29-audit-05-structural.md`.

### 9. Acoustics: verified, not validated
- **Against:** closed forms (Curle dipole, BPF array factor, IEC 61672 A-weighting, Proudman).
- **Result:** verification PASS. Validation is **INCONCLUSIVE**: nothing shows the absolute dB(A) or the ranking is right.
- **Known limits:**
  - Stock's Proudman SWL moved about 36 dB across meshes, so the flow card does not judge it;
  - the tip-speed + airflow hint varies only with CFM at fixed rpm and radius (R0.4 ruling).
- **v0.1.0 claims:** no noise comparison. Every dB number is labelled relative.
- **Audits:** `2026-09-29-audit-06-acoustics.md`, `2026-10-16-flow-noise-mesh-robust-prereg.md`.

### 10. Mixed-flow: experimental
- **Against:** nothing published. No small CC-licensed mixed-flow data was found (grok r15).
- **Result:**
  - setup and direction fixed and proved by geometry (it was solved backwards before audit-07);
  - versus axial on the same case, a tie at the operating point (44.3 CFM; free air axial 54.4, mixed 67.0;
    `docs/validation/mixed_vs_axial_v5.md`).
- **Label (R2.4, Kimball 2026-10-17):** "Experimental: not validated against published data".
- **Audit:** `2026-10-01-audit-07-cror-mixed-setup.md`.

### 11. Volute / centrifugal: unconverged proxy
- **Against:** a validation is pre-registered against EPJ WoC 180:02023 (60 mm), but not run.
- **Result:**
  - the CFD ΔP oscillates **17–23 %** (steady RANS cannot settle the tongue/scroll), so the proxy is ±20 %;
  - setup direction is fixed (audit-07).
- **Known limits:** ranking only. Convergence fix R2.5a is pending.
- **Audits:** `2026-10-01-audit-07-cror-mixed-setup.md:112`, `2026-10-18-cror-centrifugal-validation-prereg.md`.

### 12. CROR: direction proof only
- **Against:** a validation is pre-registered against Shigemitsu 2018 (CC BY 4.0, 40 mm), but not run (R2.3).
- **Result:** both rotors were solved backwards before audit-07; this is fixed and proved by geometry.
- **Use:** fast BEMT-proxy estimate, relative noise only.
- **Audits:** `2026-10-01-audit-07-cror-mixed-setup.md`, `2026-10-18-cror-centrifugal-validation-prereg.md`.

### 13. Not in v0.1.0
- The wind turbine is a scaffold, and the centrifugal archetype has no tab (R2.6).
- Nothing has been printed and measured.

### Known limits (one list, for the README)
1. Stock reads about 5 % less airflow than the real A12x25 shape (55.7 vs 58.3 CFM in the same test). Comparisons are
   like for like.
2. Assess is a screening mesh (GCI ≈ 21 %): rank designs against Stock in the same run; do not compare with a datasheet.
3. Near stall (≥ 15 Pa on the A12x25) steady CFD does not converge.
4. Noise numbers are relative and unvalidated; there is no noise comparison in v0.1.0.
5. Structural and vibration checks are estimates, not validated.
6. Propeller: BEMT ±15 % at static, worse toward zero-thrust J; prop CFD reads about 40 % low.
7. Mixed-flow is experimental; volute is an unconverged ±20 % proxy; CROR is direction-checked only.
8. Printed-part knockdown (×0.95) is assumed; nothing has been printed and measured.
