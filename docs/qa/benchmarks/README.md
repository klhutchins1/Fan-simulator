# Small axial fan benchmark library (Task D, round 6)

**Target met:** 8 fans, 3 with full geometry. Built from cited numbers only; nothing invented or tuned.
- Rebuild the folders with `handoff/2026-10-09_from-qa-5/scripts/make_lib.py <this dir>`.
- Rerun BEM with `PYTHONPATH=<worktree at 31228d0> python run_bem.py <this dir> <worktree> bem_results.json`.
- Full per-point output is in `bem_results.json`.
- `axial_force` is present in `PRESSURE_MODELS` at 31228d0, so both models ran on master code. r4_axial was not needed.

| id | size | rpm | geometry | curve data | pressure | licence / MIT | BEM error (euler / axial_force) |
|---|---|---|---|---|---|---|---|
| nf-a12x25 | 120 mm frame, 109 mm rotor | 2000 | full, **derived** (repo Stock recipe fitted to user STL) | 2 endpoints (Noctua) + Cybenetics 8-pt table cited only (`terms_unclear`) | static | Noctua numbers cited. STL origin and licence unknown, so ask before MIT release | free air −3.1 % / −0.3 %; shutoff +75 % / −4 %; mid-curve (vs Cybenetics 31.5 CFM, derived) +22 % / +33 % |
| lt120 | 120 mm rotor | 2000 | full, published table (stagger reference assumed) | 5 measured points (Lin & Tsai, digitised from CC BY re-plot, vector) | static | CC BY 4.0, MIT-OK with citation | no free-air point (last point 84 CFM: −26 % / −22 %); mid-curve 40 CFM −5 % / +35 %; near shutoff (8 CFM) −18 % / −22 % |
| nv150 | 150 mm rotor | 3500 | full, published table (circular-arc plates) | 16 measured points + η (raster digitised) | total | **CC BY-NC-ND 4.0, NOT MIT-cleared** | no free-air point (last point −7 % / −7 %); mid-curve (0.039 m³/s) −29 % / −27 %; lowest flow −31 % / −13 % |
| delta-afb0412hhb | 40 mm | 8300 | curve_only | 2 endpoints | static | datasheet, numbers cited | n/a |
| delta-afb0612hhb | 60 mm | 4500 | curve_only | 2 endpoints | static | datasheet, numbers cited | n/a |
| delta-afb0812sh | 80 mm | 4000 | curve_only | 2 endpoints | static | datasheet, numbers cited | n/a |
| delta-afb0912vh | 92 mm | 3800 | curve_only | 2 endpoints | static | datasheet, numbers cited | n/a |
| delta-afb1212sh | 120 mm | 3400 | curve_only | 2 endpoints | static | datasheet, numbers cited | n/a |

How the errors are defined:
- Errors are (BEM − measured) / measured, comparing static to static and total to total, with BEM interpolated to the measured flow.
- "Mid-curve" is the measured point nearest half of the largest measured flow.
- Free-air error is only given where the source has a zero-pressure point.

## What it says, in plain words
- **Free air is the strong point.** On the one fan with a true free-air number (NF-A12x25), both models land within 3 %.
- **The middle of the curve is the weak point.** Errors are 5–35 % across the three fans, with no consistent sign:
  - the models over-predict pressure on the Noctua;
  - they under-predict it on the 150 mm research fan;
  - the 120 mm research fan is mixed.
- So the BEM is fine for ranking free-air flow. Any mid-curve pressure number should carry about ±30 %.
- **axial_force vs euler:**
  - axial_force fixes Euler's large shut-off over-prediction on the Noctua (+75 % → −4 %), and helps at the lowest flow on nv150.
  - On lt120 it is worse mid-curve (+35 % vs −5 %).
  - Neither model wins everywhere. Three fans is too few to choose between them.
- **Caveats:**
  - nf-a12x25 geometry is a fit to an STL of unknown origin, not OEM data.
  - The lt120 stagger reference is assumed.
  - nv150 is total pressure with ρ assumed to be 1.2 kg/m³.
