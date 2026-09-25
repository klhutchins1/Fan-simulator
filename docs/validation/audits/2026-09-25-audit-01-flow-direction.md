# Audit #1: flow direction & sign conventions (2026-09-25)

Spec: `docs/superpowers/specs/2026-09-24-physics-audit-design.md` · Plan:
`docs/superpowers/plans/2026-09-24-physics-audit-foundation.md` · Roadmap §19.1

## Plain-language verdict

**Production CFD spins the A12x25 rotor the wrong way.** Both rotor models (the Stock recipe and the
close-ref STL) are shaped to turn **counter-clockwise seen from +Z** and push air toward **−Z**. That
matches the real Noctua exactly: the user's photo shows it turning counter-clockwise seen from the
intake, with the tips leading and air flowing toward the motor struts. The motor cup sits on −Z, the
exhaust side.

Production runs the rotor as built with `spin = −1`, which is clockwise seen from +Z. That is the
reverse of the designed rotation, so every stored axial-fan CFD number so far was solved with the
rotor running backwards.

- **Geometry proof: conclusive.** Five independent readings agree on both rotors; see Proof 1.
- **CFD matrix: INCONCLUSIVE under the rules set in advance.** In every comparison it ranks the
  designed rotation higher: +24% airflow on Stock, +10% on the close-ref. However, the designed-direction
  solve never settles (drift 3.8–9.8% against the 2% bar), and the close-ref margin is below the 20% bar.
  The rules were not loosened after the fact.
- **Unit `cfd.flow_direction_convention`: FAIL** (the convention is proven wrong by geometry and the
  real-fan observation). The fix plan must be re-verified by CFD after it lands.
- **Freeze stays in place** until the follow-up fix plan lands and its CFD check passes.

## Results

| Unit | Claim | Method | Measured | Expected | Tolerance | Verdict | Evidence |
|---|---|---|---|---|---|---|---|
| audit.direction_geometry | the proof reads known fans correctly | synthetic oracle + real-mesh pin | all known-answer cases pass | pass | exact | **PASS** | tests/audit/test_direction_geometry.py |
| geometry.stock_handedness | Stock rotor designed ω_z=+1, pump −Z, real handedness, tips lead | geometric proof on a fresh CadQuery build | (+1, −1, χ −1), tips +1 | same | exact | **PASS** | tests/audit/test_stock_handedness.py (slow) |
| cfd.flow_direction_convention | production solves the designed rotation pumping +Z | geometry + contract tests + 2×2 CFD | production = as_built, spin −1 (ω_z −1); designed ω_z +1 | as_built with the designed spin | exact | **FAIL** (geometry); CFD INCONCLUSIVE | direction_geometry.json, direction_cfd_*.json |
| cfd.cfm_from_outlet_flow | CFM = signed Σφ on the +Z outlet × 2118.882, never abs() | contract tests | pinned | — | exact | **AFFECTED** (depends on the failed convention) | tests/audit/test_cfd_direction_contract.py |
| physics.air_properties | room-temperature sea-level air | ideal gas, Sutherland, no-fork guard | ρ 1.2/1.225, c₀ 343, μ 1.81e-5, ν 1.5e-5 | first principles | 0.5–3% | **PASS** | tests/audit/test_air_properties.py |
| optimize.reject_dead_designs | dead or reversed designs are rejected, never scored | unit test | raises `free-delivery CFM must be positive` | raise | exact | **PASS** | tests/audit/test_dead_design_guard.py |
| propeller.thrust_sign | the sign comes from geometry, not from flipping spin | code review | `normalize_metrics_sign` flips spin until thrust > 0 | geometry-derived | — | **FAIL** (masking) | fansim/propeller/calibrate.py |

Suite: `uv run pytest tests/audit -q` gives **110 passed**.

## Evidence

### Proof 1: geometry (`docs/validation/audits/direction_geometry.json`)

The rotor is cut with cylinders at 0.55–0.85·tip, giving 36 blade sections per rotor. The concave
(pressure) face of each section gives the designed rotation and delivery direction. Every one of the
36 sections agrees (agreement 1.0).

| Rotor | designed ω_z | delivery | chirality χ | tip lead | motor cup |
|---|---|---|---|---|---|
| Stock (fresh build) | **+1** (CCW from +Z) | **−Z** | −1 (= real fan) | +1 (tips lead the rotation) | undetected (None, fails safe) |
| close-ref STL | **+1** | **−Z** | −1 (= real fan) | +1 | −Z (exhaust side) |

Checks for both rotors:
- `real_handedness` ✅ and `tips_lead` ✅ on both.
- `motor_on_exhaust`: ✅ on the close-ref; unknown on Stock.
- `cfd_spin_matches` ❌ on both: production spin is −1.
- `cfd_pumps_plus_z` ❌ on both: as built, the rotor pumps −Z.

How independent these checks are:
- χ only checks consistency. It does not depend on the camber sign that decides the rotation.
- `motor_rotation_consistent` is algebraically the same test as `motor_on_exhaust`.
- The genuinely independent checks of rotation are camber, tip lead, and the user's observation of
  the real fan. All three agree.

### Proof 2: contract tests (`tests/audit/test_cfd_direction_contract.py`)

These pin what the code means today:
- The MRF axis is (0 0 1) with ω = spin·|ω|, right-handed.
- The inlet patch is at min Z and the outlet at max Z.
- Free-air BCs are a total-pressure inlet and a static outlet, i.e. **asymmetric**.
- `outletFlow` is the signed Σφ on the outlet.
- `moment_z_nm` is the signed z-moment, while `torque_nm` = |Mz|.

### Proof 3: CFD matrix (2000 rpm, free air, 0.5 mm tip gap, no frame)

Each rotation sense is judged only on its *proper* run, the one pumping +Z through the proper BCs.
Body sense = spin as built, and −spin when flipped.

**Stock** (`direction_cfd_stock_iters1500.json`, `direction_cfd_stock_iters3000.json`)

| iters | sense | proper run | CFM | P shaft | CFM/W | converged (drift) | improper CFM |
|---|---|---|---|---|---|---|---|
| 1500 | **+1 (designed)** | flipped, spin −1 | **63.1** | 1.036 W | 60.9 | no (5.4%) | −83.4 |
| 1500 | −1 (production) | as_built, spin −1 | 48.9 | 0.865 W | 56.5 | no (2.1%) | −62.6 |
| 3000 | **+1 (designed)** | flipped, spin −1 | **60.7** | 1.008 W | 60.2 | no (9.8%) | −78.4 |
| 3000 | −1 (production) | as_built, spin −1 | 48.8 | 0.866 W | 56.3 | yes (1.7%) | −62.7 |

**Close-ref STL** (`direction_cfd_reference_stl_iters1500.json`, `direction_cfd_reference_stl_iters3000.json`)

| iters | sense | proper run | CFM | P shaft | CFM/W | converged (drift) | improper CFM |
|---|---|---|---|---|---|---|---|
| 1500 | **+1 (designed)** | flipped, spin −1 | **57.7** | 0.421 W | 137 | no (5.5%) | −70.7 |
| 1500 | −1 (production) | as_built, spin −1 | 51.9 | 0.386 W | 134 | yes (1.0%) | −61.5 |
| 3000 | **+1 (designed)** | flipped, spin −1 | **57.1** | 0.424 W | 135 | no (3.8%) | −70.8 |
| 3000 | −1 (production) | as_built, spin −1 | 51.7 | 0.387 W | 134 | yes (1.0%) | −63.2 |

Readings:
- **Direction.** In all four proper-run comparisons, and in all four improper ones, the designed
  rotation moves more air: +24% on Stock and +10% on the close-ref at 3000 iterations.
- **Power sign.** Every proper run has Mz·ω < 0, so the fluid resists the rotor, as it should. The JSON
  reports `power_sign_ok: false` only because the verdict returns early on convergence (see findings).
- **Why INCONCLUSIVE.**
  - The designed-direction solve **does not settle**. On Stock, doubling the iterations raised its drift
    from 5.4% to 9.8%, which looks like a steady-RANS limit cycle, not slow convergence.
  - The close-ref margin is 10%, under the 20% bar, and its CFM/W is a tie.
- **BC bias, measured.** Improper minus proper |CFM| is +14 to +20 CFM. So the 2026-09-24 spin A/B
  (42.4 vs −70.5 CFM) was dominated by BC bias, as suspected.
- **Absolute context** (not a validation claim). The designed-rotation mean is 60.7 / 57.1 CFM; the
  NF-A12x25 datasheet gives about 60 CFM at 2000 rpm. The production setup gives 48.8 / 51.7 CFM. The
  earlier "−26% free-air gap, plate-model ceiling" conclusion was drawn from reversed-rotation solves
  and must be re-derived once the fix lands.

### Findings

1. **Reversed rotor in production CFD.** This is the headline finding. It affects every axial-fan score
   in the catalog, `a12x25_pq_report.md`, and the "plate-model ceiling" memory note.
2. **The designed-direction steady solve limit-cycles.** It needs a transient check (URANS) or a
   convergence rule based on the stability of the tail mean before any number from it is trusted.
3. **Weak direction discrimination in the CFD.** Reversing the rotor costs only 10–24% of the airflow in
   this model. A real fan run backwards usually loses far more. This is worth a fidelity look (no frame,
   plate blades, steady RANS).
4. **Prop sign masking.** `propeller/calibrate.normalize_metrics_sign` flips spin until thrust is positive,
   which would hide exactly this class of bug.
5. **Air constants.** 19 local copies exist, including `scripts/evaluate_noise.py:C0`, which was found by
   the widened guard. All values agree today, and new copies are blocked.
6. **Verdict JSON cosmetics.** `power_sign_ok` reads False when `matrix_verdict` returns before computing
   it. It should be computed before the early returns.
7. **Stock `motor_side` undetected.** This fails safe. Stock's motor side comes from the authoring code
   (cup carved on −Z).

## Not checked

- Near-shutoff and loaded operating points.
- The frame or struts in the CFD domain.
- A transient (URANS) solve.
- CROR rear-rotor handedness; mixed-flow, volute and prop direction beyond the sign-masking review.
- BEM sign conventions.

## Follow-up plan inputs (NOT applied here; the freeze stays)

1. **Orientation.** As built, the rotor pumps −Z under its designed rotation, but the duct flows +Z.
   Either:
   - rotate the rotor 180° about X into the domain and keep `spin = −1`. This is exactly the matrix's
     proper designed run, `flipped, spin −1`; or
   - keep the rotor as built with `spin = +1`, and move the inlet to +Z and the outlet to −Z (touches
     templates, BCs and glyphs).

   The first option changes one thing (placement) and none of the solver setup.
2. Derive spin and orientation from the geometry proof (roadmap §19.2) rather than hard-coding them.
3. Fix `domain.py` / `openfoam_case.py` docstrings, roadmap §16.1, and the glyph direction.
4. Replace `normalize_metrics_sign` masking with a geometry-derived direction or an explicit error.
5. Bump `CFD_VERSION` so §18 quarantines every pre-fix score. Re-run the Stock P–Q and restate the gap in
   `a12x25_pq_report.md`. Correct the `a12x25-recipe-fidelity-limit` memory note.
6. Decide the CFD convergence rule for limit-cycling solves: URANS, or tail-mean stability across windows.
   Then re-run this matrix. That run is the one that can lift the freeze.
