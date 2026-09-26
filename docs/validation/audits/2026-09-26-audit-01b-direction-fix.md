# Audit #1b: rotor direction fix verified (2026-09-26)

Follow-up to `2026-09-25-audit-01-flow-direction.md` · Spec:
`docs/superpowers/specs/2026-09-25-rotor-direction-fix-design.md` · Plan:
`docs/superpowers/plans/2026-09-25-rotor-direction-fix.md` · `CFD_VERSION` 3

## Plain-language verdict

**The direction is fixed and proven.** Production CFD now solves the A12x25 rotor in its designed
rotation: the CFD copy is flipped 180° about X, spin is −1, and air is delivered toward +Z. The bias-free
CFD matrix confirms it on the Stock recipe (**convention verdict PASS**).

**Free-air airflow now matches the real fan:** 58.7 CFM against Noctua's 60.1 CFM, a 2% difference.
Before the fix the reversed rotor gave 44.6 CFM, which is 26% low.

**The pressure side is now the weak point.** In the designed rotation, the steady CFD loses pressure early
under load. It predicts a shut-off pressure of 9.5 Pa against the published 22.9 Pa, and the loaded solves
oscillate strongly (11–17%). Steady RANS is known to struggle near stall, where the flow is unsteady.
This is a fidelity limit, separate from the direction question: the next lever is a transient (URANS)
check of the loaded points.

The old reversed-rotation curve looked healthy under load (about 24 Pa shut-off), but it was the wrong
machine.

The §19.1 freeze on spin and flow is lifted.

## 1. Direction matrix (free air, 2000 rpm, tip gap 0.5 mm, 1500 iters, 16 procs)

Convergence is judged by rule A: tail-mean shift < 2%. Oscillation is reported separately.

**Stock** (`direction_cfd_stock.json`, saved copy `direction_cfd_stock_fix_iters1500.json`)

| run | body sense | CFM | P shaft | converged (shift / osc) |
|---|---|---|---|---|
| as_built, spin −1 | −1 (reversed) | +49.0 | 0.869 W | yes (0.4% / 1.3%) |
| as_built, spin +1 | +1 | −80.2 | 0.974 W | yes (1.7% / 3.3%) |
| **flipped, spin −1** (production) | **+1 (designed)** | **+62.2** | 1.020 W | yes (1.1% / 2.1%) |
| flipped, spin +1 | −1 | −63.0 | 1.020 W | yes (0.1% / 0.3%) |

- Matrix verdict **PASS**: the designed sense +1 wins its proper run by 27% (62.2 vs 49.0 CFM) and on CFM
  per watt (61.0 vs 56.4).
- The power sign is physical on every proper run.
- It agrees with the geometric proof (ω +1, pump −1).
- **Convention verdict PASS:** production `{flipped, −1}` equals the recommended run.
- Measured BC bias (improper − proper |CFM|): +18.0 for the designed sense and +14.0 for the reversed one.

**Close-ref STL** (`direction_cfd_reference_stl.json`, saved copy `…_fix_iters1500.json`)

| run | body sense | CFM | P shaft | converged |
|---|---|---|---|---|
| as_built, spin −1 | −1 | +51.5 | 0.383 W | yes |
| as_built, spin +1 | +1 | −70.7 | 0.432 W | yes |
| **flipped, spin −1** | **+1** | **+56.6** | 0.424 W | yes |
| flipped, spin +1 | −1 | −63.3 | 0.363 W | yes |

The designed sense still wins, by 10%, but that is below the preset 20% bar. The verdict is
**INCONCLUSIVE**, the same as in Audit #1, and it is reported as-is; the threshold was not loosened.
This STL is not the production recipe.

All proper runs converged under rule A this time. In Audit #1 the same designed-direction runs had
4–10% peak-to-peak and failed the old rule.

## 2. Stock P–Q, before and after (`runs/validate_a12x25_dirfix/validation.json`)

| back-pressure | before (reversed, 2026-09 `a12x25_shutoff_05`) | **after (designed, CFD v3)** | converged / osc |
|---|---|---|---|
| 0 Pa | 44.6 CFM | **58.7 CFM** | yes / 7.9% |
| 5 Pa | 30.5 | 21.6 | **no** (shift 7.1%) / 11.4% |
| 10 Pa | 18.5 | −6.2 | yes / 16.8% |
| 15 Pa | (14 Pa: 11.4; 16 Pa: 9.1) | −72.5 | yes / 0.8% |
| 20 Pa | — | −116.5 | no / 6.0% |

Against the published NF-A12x25 values (60.1 CFM free air, 22.9 Pa shut-off):
- **free air −2%, a PASS**;
- **shut-off 9.5 Pa (−13.4 Pa), a FAIL**, where the interim band is 17.9–27.9 Pa.

The large negative flows at 15–20 Pa are the stalled fan being overrun by the imposed back-pressure.
Under the asymmetric BCs, reverse flow is driven by the full pressure drop.

**Reading.**
- Free air is solved well in the designed rotation.
- Loaded operation is where this steady, frameless, plate-blade model breaks down.
- The strong oscillation (11–17%) at 5–10 Pa marks an unsteady, stall-dominated regime that steady RANS
  cannot represent.

Candidate levers, in order:
1. URANS at 5–15 Pa.
2. Include the frame and struts (`--with-frame`).
3. Prism layers.
4. Blade-recipe fidelity.

None of these are done here.

## 3. Units and ledger

`uv run python scripts/audit_status.py` after recording:

```
PROVEN    audit.direction_geometry
PROVEN    cfd.cfm_from_outlet_flow
PROVEN    cfd.flow_direction_convention
PROVEN    geometry.stock_handedness
PROVEN    optimize.reject_dead_designs
PROVEN    optimize.search_space_handedness
PROVEN    physics.air_properties
PROVEN    propeller.thrust_sign

PROVEN=8  CHANGED=0  AFFECTED=0  NEW=0  UNREGISTERED=317
```

Test evidence: `uv run pytest` gives 910 passed and 9 skipped (non-audit), and
`uv run pytest tests/audit -m "slow or not slow"` gives 155 passed.

| unit | verdict | evidence |
|---|---|---|
| cfd.flow_direction_convention | **PASS** | Stock convention verdict PASS; contract, orientation and placement tests |
| cfd.cfm_from_outlet_flow | **PASS** | contract tests + `tests/test_convergence_rule.py` (the direction unit it depends on now passes) |
| optimize.search_space_handedness | **PASS** | `tests/audit/test_search_space_handedness.py` |
| propeller.thrust_sign | **PASS** | thrust-sign, builder-direction and prop-handedness tests |
| audit.direction_geometry | **PASS** (re-recorded; code changed: section-quality guard, leaf `flip_about_x`) | known-answer + real-mesh pins |
| geometry.stock_handedness | **PASS** (re-recorded) | slow Stock handedness test |
| physics.air_properties, optimize.reject_dead_designs | unchanged | — |

## 4. Other findings from this fix

- **MRF zone and frame placement** (spec problem 2). The optimizer's MRF zone was ±5 mm around a rotor
  spanning −8.1 to +8.4 mm, and the frame struts started inside the blade band. Both are now fitted from the
  oriented STL, and `build_case` refuses any rotor outside its MRF zone or any overlapping frame or stator.
- **CROR:** the hub overhung the dual-MRF zone by 1 mm. Fixed with `fit_cror_to_stl`.
- **Props:**
  - Spin flipping is removed.
  - Direction comes from the builder for in-house geometry, and from the geometric proof for external STLs.
  - A section-quality guard stops the proof from reading thick or non-airfoil sections. All 8 drone STLs
    are now correctly INCONCLUSIVE.
  - Open follow-up: `run_cfd_polar` does not yet raise the `direction_suspect` backstop.
- **Cockpit:** CFD velocity arrows are mapped back to the as-built frame, so they agree with the preview rotor.

## Not checked

- URANS.
- The frame in the P–Q.
- A mesh ladder at CFD v3.
- Loaded-branch convergence.
- CROR and mixed-flow direction beyond the placement check.
- Re-scoring the optimizer catalog. All pre-v3 scores are stale by `CFD_VERSION`.
