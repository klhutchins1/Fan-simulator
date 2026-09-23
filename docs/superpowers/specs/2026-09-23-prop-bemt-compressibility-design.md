# §4.4 step 1: Call compressibility from BEMT analyze

**Date:** 2026-09-23  
**Status:** approved (2026-09-23)  
**Approach:** A — call the existing helper inside the element iteration  
**Parent:** roadmap §4.4 (steps 2 and 3 stay open)  
**Related:** `fansim/propeller/bemt.py` (`_compressibility_cl_cd`), `fansim/prop_spec.py` (`C_AIR`)

## Plain language

The propeller screener already knows a compressibility correction. It never uses it. Every design at Mach 0.35–0.58 is still scored as incompressible air. This slice turns that correction on inside the blade-element loop. It does not run CFD and it does not change the correction formula.

## Goal

1. `analyze` applies `_compressibility_cl_cd` to every station, on every fixed-point iteration, before thrust and torque are accumulated.
2. Local Mach is the element's relative speed divided by the same 343 m/s the rest of the prop path already uses (`prop_spec.C_AIR`). The spoken "340 m/s" was that sea-level air; do not add a second constant.
3. Existing BEMT band tests still describe a physical propeller. If a band fails only because lift rose with Mach, update that assertion and say why. Do not turn the correction off to keep the old number.
4. Roadmap §4.4 step 1 is marked done. Steps 2 and 3 stay unchecked. The §4.4 box stays open.

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | After `_cl_cd`, and before `dT` / `f_theta`, the loop sets `mach = sqrt(W2) / C_AIR` and replaces `(cl, cd)` with `_compressibility_cl_cd(cl, cd, mach)` |
| 2 | The helper body is unchanged: Prandtl–Glauert on Cl, wave-drag rise only for Mach > 0.7, Mach clamped to [0, 0.95] |
| 3 | A test on `fpv_5inch` at 30000 RPM records every Mach passed into the helper. The set is not constant. The maximum is at least 0.45 (tip speed is about Mach 0.58; stations sit inboard of the tip) and at least 1.5× the minimum |
| 4 | A test shows that, on `fpv_5inch` at 30000 RPM, thrust with the real helper is greater than thrust with the helper replaced by the identity `(cl, cd)` |
| 5 | `tests/test_bemt.py` and `tests/test_prop_fwh_compress.py` pass |
| 6 | CFD fixtures, AMI code, and `run_prop_study` objectives are untouched |

## Non-goals

- Changing `_compressibility_cl_cd` (no Karman–Tsien, no critical-Mach model, no stall cutoff)
- `MeshResolution.for_blade`, prism layers, or any Docker solve (roadmap §4.4 step 2)
- AMI timestep, signed thrust, or another sliding-mesh run (roadmap §4.4 step 3)
- Mission presets, noise as an objective, endurance, or range (roadmap §14.7)
- A flag to disable compressibility. It is on for every `analyze` call
- Retuning NSGA bounds or rewriting stored study results

## Approach choice

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A (chosen)** | Call the existing helper inside the fixed-point loop, Mach = relative speed / `C_AIR` | Induced velocity sees the corrected lift. One constant, already in the prop path |
| B | Apply the helper once after the iteration converges | The inflow was solved with the wrong lift |
| C | Replace the helper with a fuller compressibility model in the same change | Mixes "turn it on" with "change the physics." Out of this slice |

## Physics

Relative speed is already `sqrt(W2)` with `W2 = Vax² + Vt²` (axial inflow plus tangential speed after swirl). Local Mach is that speed over `C_AIR = 343` m/s. Tip Mach on `PropSpec` uses the same constant, so a station at the tip is in the same Mach family as `tip_mach`. BEMT density stays 1.225 kg/m³. Do not switch the screener to the CFD thermo state (300 K, 1.174 kg/m³).

The helper divides Cl by `sqrt(1 − M²)` and, only above Mach 0.7, adds a soft wave-drag term. Below 0.7, drag is unchanged and lift rises. On a 5-inch prop at 30000 RPM the tip is about Mach 0.58, so this slice mostly raises lift. Wave drag is present in the formula and will not show up on the registry props at their current RPM caps.

Figure of merit, grams per watt, and propulsive efficiency keep their current formulas. They move only because thrust and power move.

## Architecture

| Piece | Change |
|-------|--------|
| `fansim/propeller/bemt.py` | Import `C_AIR` from `fansim.prop_spec`. One call inside the iteration. One-line docstring note that `analyze` applies this correction |
| `tests/test_prop_fwh_compress.py` | Add the two success-criteria tests (call shape, and high-RPM thrust rises) |
| `tests/test_bemt.py` | Change only if a band no longer holds, and comment the new bound |
| `docs/roadmap.md` | Mark §4.4 step 1 done in the existing bullet. Leave the checkbox open |

`_cl_cd` stays the incompressible polar. Compressibility is a correction after the polar, which is what the helper's signature already is.

## Error handling

`W2` is a sum of squares, so Mach is finite. The helper already clamps Mach into [0, 0.95]. No new exception path.

## Testing

CI only. No Docker. No new fixture files. The identity-helper test must monkeypatch `_compressibility_cl_cd` in `fansim.propeller.bemt`, not a copy.
