# RV-3 findings log

Module-by-module review (`docs/review/2026-11-24-review-plan.md`, RV-3). Each module gets the plan's checklist:
are equations sourced, are units and signs right, are failures swallowed, are constants defined once, are there
numeric tests, is it in the audit ledger, is anything over-long. "Fixed" means the change is on branch
`claude/rv3-review`, with a test that fails on the old code.

## 1. `fansim/optimize/objectives.py` (`evaluate_candidate`), reviewed 2026-11-24

| # | severity | finding | status |
|---|---|---|---|
| O1 | **high** | The structural gates (centrifugal stress ∝ rpm², resonance vs blade-pass ∝ rpm) ran **before** `params.rpm = target_rpm`, so they judged the stale `params.rpm` (BladeParams default 2000). For the 3900 rpm Delta AFC1212DE model, stress was under-stated by about 3.8× and blade-pass by 2× (300 Hz, not 585 Hz, which is above Stock's ~400 Hz first bending mode), so resonant designs went unflagged (`flutter_report` stamps `vibration_warning`, not a hard reject). A12x25 `--search-rpm` (450–2000) was conservative. It also mutated the caller's params. | fixed `e349624` + `0a0baa9` (`tests/test_objectives_gate_rpm.py`, #47) |
| O2 | medium | A BEM pre-screen crash was `pass`ed: the design went to CFD with no trace. | fixed `d6097c4` (`raw.bem_prescreen_error`) |
| O3 | medium | A sanity-check crash became `[]`, and the status read `SKIP`, the same as "never ran". | fixed `d6097c4` + `0a0baa9` (status `ERROR`, `raw.sanity_error`, preserves `SANITY_FAIL` in `reason`) |
| O4 | low | "solve failed" dropped the exception message. | fixed `d6097c4` |
| O5 | low | The free-air salvage failure was `pass`ed. | fixed `d6097c4` + `0a0baa9` (`raw.free_salvage_error` + test) |
| O6 | low | If trimesh cannot read the STL volume, the weight gate is skipped with no stamp (`weight_g = None`). | fixed by Cursor, PR #80 (`0e1ccd7`, `raw.weight_error`, #52) |
| O7 | low | The loading-noise proxy uses free-air thrust at **rated** rpm; it is not derated with the motor (thrust ∝ λ²). It is ranking-only, so the order holds within one derate, but a motor-limited design reads louder than it runs. | fixed in PR #81 (`4a73960`, #53) |
| O8 | code health | `evaluate_candidate` is ~490 lines: gates, pre-screens, geometry, CFD, scoring. | RV-5 (split into stages) |

PR #84 review follow-up (`0a0baa9`) also removed the redundant silent `tip_deflection_mm` `except` in `apply_print_penalty` (reusing `defl.tip_deflection_mm` from the FSI gate) and stamped `raw.proudman_error` on Proudman noise read failure.

Checked and fine: derate (flow ∝ λ, power ∝ λ³, probe pressure ∝ λ²); signed CFM is never `abs()`-ed (a reversed
probe reads as a stall); system-curve failure reasons; the surrogate pre-screen already refuses rather than falling
through to CFD (§9.6).

## 2. `fansim/fan_bem.py`, reviewed 2026-11-25

No new defects. Checked line by line:
- Euler ΔP₀ = ρ·U·ΔV_θ, mass-weighted.
- Tangential blade force ½ρW²cB(c_l sinφ + c_d cosφ), with φ from the rotation plane (the geometry's stagger
  convention).
- Angular momentum V_θ = F_θ/(ρV_x·2πr).
- Shaft power dm·U·V_θ uses the full swirl, so SLIP counts as lost work and η ≤ 1 by construction.
- Static rise = total − exit swirl head − friction; with a stator the swirl is recovered.
- The axial-force model's units (N/m·m ÷ area → Pa) and its energy cap.
Previously filed, now fixed on `master`: rounding inside the maths (#50, PR #63 / `9ee2f99`), `NU_AIR` literal
(#48, PR #62 / `2b08ccf`). The loss constants (SLIP, K_FRICTION, K_TIP_LEAK) are empirical fits to Stock,
documented by Audit #4.

## 3a. `fansim/cfd/metrics.py`, reviewed 2026-11-25

No new defects. Checked:
- force.dat/moment.dat column layout after paren-stripping (`[t, total xyz, pressure xyz, viscous xyz]`, so
  index 3 = total z);
- signed outlet φ sum;
- static rise = (p_out − p_in)·ρ for kinematic pressure;
- static η = Q·ΔP/(|M_z|ω);
- tail mean and convergence use the same 25 % tail;
- QA-39 time-folder order (pinned by the new contract test).
Note: torque is `abs(M_z)`, so a windmilling rotor shows positive power; `cfd.sanity` `power_sign` flags it, and
it is not silent.

## 3b. `fansim/cfd/flow_report.py`, `flow_verdicts.py`, reviewed 2026-11-26

Merged in PR #92 (`67806aa`) with RV-5 follow-ups in PR #114 (`929d2c9`, closes `#89`):
- Removed dead threshold constants (`BACKFLOW_MARGIN`, `SWIRL_FACTOR`, `DEAD_MARGIN`, `TIP_FACTOR`), fixed `_dead`
  tip-ratio ≤ 0 and `better_tip` text, fixed `overall_line` edge cases, and reused `slab_half_width` in `spanwise.py`.
- Added `rho`/`rhoInf` mismatch `UserWarning` and documented CROR equal-`|\omega|` precondition in `metrics.py`.
- Open `math` issues requiring pre-registration: `#86`, `#87`, `#88`, `#90`.

## 4. `fansim/geometry/airfoil.py`, `blade.py`, reviewed 2026-11-26

Full report: `docs/review/2026-11-26-rv3-geometry.md`. Merged in PR #119 (`ad7eb8a`):
- Verified NACA 4-digit closed-TE thickness/meanline, `rounded_plate`, 3-D stagger/LE-leads mirror, and cylinder-wrap
  kinematics from first principles.
- Fixed lazy CadQuery/OCCT isolation (`blade.py`, `export.py`), falsy-zero `_thick_scale_kw`, dropped `_trim_tip`,
  unchecked shroud fuse, 4 swallowed/unchained `except` blocks, and invalid-input guards (`tests/test_rv3_geometry.py`).
- Re-proved `geometry.stock_handedness` with zero RV-1 drift.
- Open issues: `#116` (`math`), `#117` (`math`), `#118` (`review`).

## 5. `fansim/propeller/bemt.py`, `polars.py`, reviewed 2026-11-26

Full report: `docs/review/2026-11-26-rv3-propeller.md`. Merged in PR #115 (`818e42e`); `#113` (`C_AIR` single-sourcing
in `prop_spec.py` and `pythrust_export.py`) closed in PR #121 (`5771dcd`):
- Single-sourced `C_AIR` from `fansim/physics/air.py`, fixed custom-`rho` Reynolds viscosity scaling and `rpm=0`
  phantom thrust, tightened input and CSV validation, cached polar curve limits, and widened `mypy` to 10 source files
  (`tests/test_rv3_propeller.py`, `tests/test_c_air_single_source.py`).
- Re-proved `propeller.bemt` and `propeller.polars` with zero RV-1/RV-2 drift.
- Open `math` issues requiring pre-registration: `#109` (high), `#110` (high), `#111` (med), `#112` (low).

## 6. `fansim/optimize/search_space.py`, reviewed 2026-11-26

Full report: `docs/review/2026-11-26-rv3-search-space.md`. Merged in PR #130 (`b1d3f34`):
- Fixed `tip_radius_cap_mm` double-subtracting `shroud_mm`, spurious `1e-14` cylinder-wrap step, and magic `20.0 mm`
  floor; single-sourced `TIP_CAP_CLEARANCE_MM` from `OPTIMIZER_TIP_GAP_MM`; fixed `blade_to_flat` / `blade_from_flat`
  falsy-zero and explicit-`None` serialization bugs and `suggest_params` bounds/replay guards (`tests/test_rv3_search_space.py`).
- Re-proved `optimize.search_space_handedness` with zero RV-1 drift.
- Open issues: `#127` (`review`), `#128` (`math`).

## 7. `fansim/structural/*`, `fansim/acoustics/*`, reviewed 2026-11-26

Full report: `docs/review/2026-11-26-rv3-structural-acoustics.md`. Merged in PR #131 (`f5f0f27`); `proxies.py`
`k >= 0`/`omega >= 0` clamps landed in PR #114 (`929d2c9`):
- Eliminated silent-pass `NaN` traps in structural stress/deflection/flutter, fixed triangle-inequality non-convergence
  in `balance.py`, fixed OpenFOAM scientific-notation time-dir discovery in `case.py`, normalized `r_hat`, forwarded
  `n_blades`/`rpm` in `fwh.py`, and hardened input validation across all 13 modules (`tests/test_rv3_structural_acoustics.py`).
- Re-proved all affected structural/acoustics ledger units with zero RV-1 drift.
- Open issues: `#122` (`math` high — `loading.py` `c1 = -74.4`), `#123` (`math` med), `#124` (`math` med), `#125` (`math` low), `#126` (`review` low).

## 8. `fansim/cockpit/*`, reviewed 2026-11-26

Full report: `docs/review/2026-11-26-rv3-cockpit.md`. Merged in PR #132 (`2eea9d6`):
- Verified zero duplicated physical constants across all 54 cockpit modules and audited every `except` block.
- Fixed `placement.py:_blade_z_bounds` to reuse `_thick_scale_kw(params)` and forward `te_face`/`le_face`, fixed
  `fan_assess.py:spec_status` to log and warn on unreadable preview STLs instead of silently returning `(True, "")`,
  hid idle `⏹ Cancel viz` behind `airflow_busy`, and added `EXPERIMENTAL_LABEL` to the Mixed Design card
  (`tests/test_rv3_cockpit.py`).
- Follow-up fix in PR #137: kept `placement.py:impeller_z_extent` purely analytic for shrouded cylindrical-tip designs
  so `fit_envelope` / `on_scale_to_hub` never invoke OCCT `prepare_loft_chords` lofts.

Carried in from earlier work (see the plan) — all four now fixed and merged on `master`:
- CFM factor single source (`#49`, PR #61 / `08cab17`);
- stop rounding inside BEM/BEMT maths (`#50`, PR #63 / `9ee2f99`);
- derive `NU_AIR = MU_AIR / RHO_AMCA` (`#48`, PR #62 / `2b08ccf`);
- PLA yield 60 MPa vs PETG 50 MPa (`#51`, PR #64 / `2f11e35`).
