# lt120 as a fansim BladeParams design (round 7, Task C; build-only, no CFD)

- **Pre-registration:** `prereg/PREREG_R7.md` in my clone, branch `prereg/round7` (commit 2073315), sha256 `c163f1d7eaa6b4763871b2542d1b18e3ca5d34f6562e7878db35686cf52d0e6e`. It was committed before the build.
- **Files:** `docs/qa/benchmarks/lt120/fansim_params.json` (7 blades), `docs/qa/benchmarks/lt120/built_vs_table.json`, and the scripts `handoff/2026-10-11_from-qa-7/scripts/lt120_to_params.py` and `lt120_variant.py`.
- **Code:** master 5980677.
- **Build:** the measurement build used **2 blades** (the validator minimum) instead of 7, to keep fuse memory low on the shared box. Each blade's sections are identical either way.

## Plain-language verdict
- The builder can hold this fan, but a cylinder-cut check doesn't reproduce the table yet.
- **Blade angles: match.** Within 0.75° at every radius.
- **Chord: short.** Measured chord is 0.5 % short at the root and 16 % short at the tip.
- **Camber: low.** It reads 0.030 instead of 0.040 everywhere.
- **Thickness ratio:** reads 1–19 % high, but only because the chord is short. Absolute thickness agrees (tip 2.48 mm vs 2.50 mm).
- **The cause is how sections are defined, not a builder bug.** fansim lofts each table row as a **flat (planar) airfoil** that touches the cylinder at radius r: at the tip it spans r = 56.5 → 59.0 mm. A cylinder cut at r therefore sees a shorter, flatter slice once chord / r is large. lt120's chords are long (41.6 mm at 56.5 mm), so it shows the effect strongly.
  - On its own, the planar section is within 1.7 % of the requested chord.
  - Switching `cylindrical_tip` off or `chord_basis` to `loft` changes nothing.
- **Open question:** the paper doesn't say whether its table means planar CAD sections (the usual CAD workflow, which would make our build the faithful one) or cylindrical sections. Either way, the CFD pre-registration should say which reading it tests.

## 1. Conversion and the stagger convention
- **Station placement:** `r_frac = (r − r0)/(tip − r0)` with **r0 = hub_radius − root_embed**. The builder lofts from r0, not from the hub (`blade.py`, `r_root = hub_radius − root_embed`). The brief's (r − hub)/(tip − hub) would shift every station.
  - With hub 25 mm and root_embed 2 mm, r0 = 23.0 mm, which is exactly table row 1. So all 10 rows map to r_frac 0 … 0.905 with no clamping, and the 23.0 mm row lands in the embedded root.
- **Section values:** stagger_deg = the published setting angle. NACA 44xx gives max_camber 0.04, camber_pos 0.4, thickness xx/100. `section_family = "naca"`.
- **Evidence that the setting angle is measured from the rotation plane** (our `stagger_deg` convention):
  1. **Twist direction.** The paper says the setting angle *decreases* hub → tip (39.9° → 36.0°). Measured from the plane, that is normal fan twist. Measured from the axis, it would mean the blade gets steeper toward the tip, which is backwards for a fan.
  2. **Velocity triangle at the 60 CFM, 2000 rpm design point.** The inflow angle from the plane is about 35° at the root and about 14° at the tip. Setting angles of 36–40° from the plane give positive incidence; 50–54° (the from-axis reading) would put the tip far into stall.
  3. **Fig. 2b** draws the stagger θ between the chord and a horizontal line, which is the rotation plane in that view.
- **Contrary evidence:** the paper's text defines the *added* stagger θ as the angle "between the chord line and the fan's axial-flow direction". **Confidence: moderate-high** for from-plane. I take the text to be loose wording.

## 2. Built vs table (cylinder cuts at the table radii, `fansim.validation.section_compare.measure_sections`)
| r mm | stagger Δ° | chord Δ % | camber built (table 0.040) | t/c Δ % |
|---|---|---|---|---|
| 26.7 | +0.33 | −3.2 | 0.030 | +3.6 |
| 30.4 | +0.28 | −0.5 | 0.029 | +1.1 |
| 34.2 | −0.02 | −3.3 | 0.030 | +3.9 |
| 37.9 | −0.22 | −6.4 | 0.030 | +7.4 |
| 41.6 | −0.48 | −9.0 | 0.030 | +11.0 |
| 45.3 | −0.64 | −11.3 | 0.031 | +14.1 |
| 49.1 | −0.75 | −13.2 | 0.031 | +19.3 |
| 52.8 | −0.75 | −14.8 | 0.030 | +16.5 |
| 56.5 | −0.73 | −15.6 | 0.029 | +17.6 |

**Pre-registered verdicts:**
- **C1 stagger ≤ 1.5°: PASS.**
- **C2 chord ≤ 3 %: FAIL** (6 of 9 stations).
- **C3 camber ≤ 0.005: FAIL** (all stations, −0.009 to −0.011).
- **C4 t/c ≤ 10 %: FAIL** (5 of 9 stations).

Every station read the right direction (ω +1).

**Camber cross-check: the measuring tool reads NACA camber low by itself.** I applied the same quadratic camber estimator
(`measure_sections` / `prove_direction`) to *exact* analytic NACA 4420, 4412 and 4406 sections. It reads 0.034, 0.037 and 0.038, not
0.040. So 0.002–0.006 of the camber shortfall comes from the estimator, not the builder.
- Against an estimator-consistent target, the built blade (0.030) is still 0.004–0.008 low. That is borderline against the
  0.005 band. The pre-registered C3 verdict stands as FAIL.
- **For the CFD case:** compare built-vs-table by passing the table sections through the same estimator. A raw 0.040 target overstates the gap.


## 3. What we can't represent exactly
- **Section family:** NACA 4-digit is supported (`naca`), but sections are planar at radius r. A cylindrical-section blade needs the fit loop (`scripts/fit_recipe_to_stl.py`-style iteration toward cylinder-cut targets), as was done for Stock.
- **23.0 mm root below the 25 mm hub:** no gap. It lands exactly in the 2 mm root embed.
- **56.5 vs 60 mm tip:** stations stop at r_frac 0.905. `np.interp` holds row 10 (chord 41.6, 36.0°) constant over the last 3.5 mm.
  - The table's 3.7 mm spacing suggests the rows are strip centres, with a blade edge near 58.35 mm.
  - The tip radius is a real uncertainty: either 60 (published diameter) or about 58.4 (strip edge).
- **Tip gap / duct:** not reported. fansim's default is 0.5 mm.
- **Blade count:** 7 is fine (the validator only needs ≥ 2).

## 4. Proposed CFD comparison (for Claude to pre-register and run)
- **Model:** the 7-blade `fansim_params.json` at 2000 rpm, tip_radius 60.
  - Run a **sensitivity copy with tip_radius 58.4** and report it, but do not use it for pass/fail.
  - Use our standard ducted open-inlet domain with a 0.5 mm tip gap. The rig standard is unknown; AMCA 210-style static pressure is the likely one.
  - Pressure: **static** rise, compared like for like.
- **Points:** all 5 measured points (8.0, 32.0, 40.0, 60.0, 84.0 CFM → 34.0, 17.1, 14.7, 13.7, 6.9 Pa).
  - Primary: the design region, 40 and 60 CFM.
  - The 8 CFM point (and probably 32 CFM) sits on the stall hump. Report it, but don't score it.
- **Pass band to pre-register:**
  - Static pressure at 40 and 60 CFM within **±20 %** each.
  - Flow at 6.9 Pa (the 84 CFM point) within **±15 %**.
  - This mirrors the Stock evidence: −2 % free air on the close-reference STL, mid-curve within about 20 %.
- **Report separately:** BEM gave −5 % / +35 % (euler / axial_force) at 40 CFM (round-6 library).
- **Section-reading caveat:** a FAIL would be ambiguous between solver error and the planar-vs-cylindrical section question. If budget allows, also build a cylinder-cut-fitted variant via the fit loop and run it as a second geometry.
