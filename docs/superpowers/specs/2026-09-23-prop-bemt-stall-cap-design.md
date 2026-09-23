# BEMT stall cap on Prandtl–Glauert lift

**Date:** 2026-09-23  
**Status:** approved (2026-09-23)  
**Approach:** A — skip the lift factor at or past stall, and cap attached lift at the polar peak  
**Parent:** roadmap §4.4 step 1 follow-up. Unblocks §14.7. Does not close §4.4.  
**Related:** `fansim/propeller/bemt.py` (`_compressibility_cl_cd`, `_cl_cd`), `fansim/propeller/polars.py`

## Plain language

Prandtl–Glauert currently divides every section lift by `sqrt(1 − M²)` after the polar has already stalled. On `fpv_5inch` at 30000 RPM the table polar is in use and station angles run from about 5° to about 64°, so stalled lift is inflated by about 23% near Mach 0.58. This slice applies that factor only on the attached part of the polar, then stops at the polar's peak lift. A mission search that runs before this fix would reward high-RPM stalled sections.

The obj_2 wall solve already showed where the CFD kilowatt sits. At iteration 400 the shaft moment is 0.818 N·m: 0.812 N·m pressure, 0.006 N·m viscous. This slice records that split. It does not run another mesh.

## Goal

1. Attached lift still rises with Mach. Lift at or past stall does not. Attached lift cannot pass the incompressible polar's peak.
2. Wave drag past Mach 0.7 is unchanged, including on stalled sections.
3. `analyze` still calls the helper inside the fixed-point loop with `mach = sqrt(W2) / C_AIR`.
4. Roadmap §4.4 stays unchecked. Step 3 stays parked. §14.7 stays unchecked.

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | `_compressibility_cl_cd(cl, cd, mach, *, stalled=False, cl_cap=None)` keeps today's body when both new arguments are left at the default: Cl divided by `sqrt(1 − M²)`, Mach clamped to [0, 0.95], wave drag only for Mach > 0.7 |
| 2 | `stalled=True` returns the incoming Cl unchanged at every Mach. At Mach 0.85, Cd still takes the existing wave-drag increment |
| 3 | `stalled=False` with `cl_cap` set returns `cl / beta`, then clamps the absolute value to `cl_cap`. A case that would pass the cap returns exactly `±cl_cap` |
| 4 | A table section is stalled when its angle is at or past the first angle where that curve's Cl reaches its maximum. It is also stalled when `min(Cl) < 0` and its angle is at or below the last angle where Cl reaches that minimum. Otherwise it is attached. The cap is the maximum Cl when the incompressible Cl is ≥ 0, and the absolute minimum Cl when it is < 0. Alpha outside the table is compared with those angles directly; the table-edge clamp does not move the stall angle |
| 5 | For a Reynolds blend, blend each neighbor's positive stall angle, negative stall angle, maximum Cl, and minimum Cl with the same log10-Re weight the Cl blend already uses. Then apply criterion 4 to the queried angle using those blended limits and the blended incompressible Cl |
| 6 | The analytic polar is stalled when `alpha` in degrees is greater than `stall_deg`, or when the unclamped linear Cl has absolute value ≥ `cl_max`. The cap is `cl_max`. The post-stall soft drop still runs first and its Cl is then left unchanged |
| 7 | `analyze` takes stall and cap from the same branch `_cl_cd` uses (table when `cl_cd_table` returns a point, otherwise analytic) and passes them into the helper |
| 8 | On `fpv_5inch` at 30000 RPM, thrust with the real helper remains greater than thrust with the helper replaced by the identity `(cl, cd)` |
| 9 | `tests/test_bemt.py` and `tests/test_prop_fwh_compress.py` pass. If the RPM-doubling ratio in `test_thrust_scales_with_rpm_squared` falls, lower the ceiling to the new measured ratio plus a small margin and comment that the stall cap removed post-stall lift inflation. Do not raise the ceiling above 5.0 |
| 10 | The validation wall section and roadmap §4.4 step 2 each gain one sentence: iteration 400 moment is 0.818 N·m, of which 0.812 N·m is pressure and 0.006 N·m is viscous. Step 1 gains a sentence pointing at this spec once the code lands |

## Non-goals

- Karman–Tsien, a critical-Mach model, or any change to the wave-drag formula
- Changing `cl_max`, `stall_deg`, the post-stall drop, or vendored polar CSV values
- A flag to disable compressibility
- Another Docker solve, a finer `SURF_LEVEL_MAX`, or an AMI retry
- Mission presets, noise as an objective, endurance, or range (roadmap §14.7)
- Rewriting `obj_2_ccw_smoke.json`, `obj_2_ccw_refine.json`, `obj_2_ccw_gci.json`, or `obj_2_ccw_wall.json`

## Approach choice

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A (chosen)** | Helper takes `stalled` and `cl_cap`. The polar reports both. Attached Cl is `cl / beta` capped at the peak. Stalled Cl is unchanged | Matches the table polar `analyze` actually uses, including angles past the last table row |
| B | Cap `|cl / beta|` at the peak and do not track stall | A post-stall Cl of 0.83 still climbs toward the peak. That is the bug |
| C | Apply the factor inside the analytic slope only | Most 30000 RPM stations take the table. Those would stay inflated |

## Physics

Relative speed and `C_AIR = 343` m/s stay as they are. BEMT density stays 1.225 kg/m³.

The incompressible polar already contains stall: the analytic path clamps at `cl_max` and then soft-drops past `stall_deg`; a vendored table flattens and then falls (NACA 4412 at Re 8e4 peaks at 1.04017 from 8° through 11°, then declines). Prandtl–Glauert is a linear correction. It may steepen the attached slope. It may not lift a section that is already on the plateau or on the declining side, and it may not create a peak above the incompressible one.

Cd is the polar Cd plus the existing wave-drag term. Stall does not change that term.

Figure of merit, grams per watt, and propulsive efficiency keep their formulas.

## Architecture

| Piece | Change |
|-------|--------|
| `fansim/propeller/bemt.py` | Keyword-only `stalled` and `cl_cap` on the helper. One internal section lookup returns `(cl, cd, stalled, cl_cap)` for the analytic branch and, when the table hits, for the table branch. `_cl_cd` stays a 2-tuple wrapper. `analyze` passes `stalled` and `cl_cap` into the helper on every iteration |
| `fansim/propeller/polars.py` | A function that, given `(alpha, camber, re, thickness)`, returns `(stalled, cl_cap)` for the same curve `cl_cd_table` would use. Returns `None` when the table path returns `None` |
| `tests/test_prop_fwh_compress.py` | Helper tests for criteria 2 and 3. The Mach spy accepts the new keyword arguments. Criterion 8 stays |
| `tests/test_bemt.py` | Ceiling edit only if the measured RPM ratio moves, per criterion 9 |
| `docs/validation/drone_radial_open_air_cfd.md` | One sentence on the iteration-400 moment split in the wall section |
| `docs/roadmap.md` | One sentence on step 1 pointing here. One sentence on step 2 with the moment split. The §4.4 checkbox, step 3, and §14.7 stay open |

Stall tolerance on a table curve is `1e-4` in Cl. The positive stall angle is the smallest alpha whose Cl is at least `max(Cl) - 1e-4`. The negative stall angle exists only when `min(Cl) < 0`, and it is the largest alpha whose Cl is at most `min(Cl) + 1e-4`. A queried angle past the last row or before the first row is compared with those angles directly.

Reynolds blend: if `w` is the existing log10 weight from the low neighbor toward the high neighbor, blend positive stall angle, negative stall angle, maximum Cl, and minimum Cl as `(1 - w) * lo + w * hi`. If either neighbor has `min(Cl) >= 0`, the blended curve has no negative stall gate. Criterion 4 then runs once, using the blended incompressible Cl to pick the cap.

`cl_cap` passed into the helper is a positive magnitude. `stalled=True` ignores `cl_cap`.

## Error handling

Mach handling stays inside the helper. No new exception. A table miss still falls through to the analytic polar, which always has a finite `cl_max`.

## Testing

CI only. No Docker. No new fixture files. The identity-helper test continues to monkeypatch `_compressibility_cl_cd` in `fansim.propeller.bemt`. The existing Mach spy must accept `stalled` and `cl_cap` or it will fail when `analyze` passes them.
