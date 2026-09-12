# Wall ks + thickness-aware print η (stage 2)

**Date:** 2026-09-08  
**Status:** accepted  
**Approach:** Opt-in OpenFOAM `nutkRoughWallFunction` on printed walls; thickness-lerped algebraic η knockdown. Algebraic print CFM factor unchanged. Not FSI.  
**Roadmap:** §7.6 stage 2.

## Plain language

Stage 1 knocked reported CFM/η after smooth-wall RANS. Stage 2 adds the physics knob the papers talk about (sand-grain `ks` on the blade) as an **opt-in** case BC, and eases the η print factor when the tip is thick (published robustness lever). Default screening stays smooth + thin-tip 0.92 η.

## Goal

1. `fansim/cfd/wall_roughness.py`: `FDM_WALL_KS_MM = 0.10`, `nut_wall_bc`, `wall_ks_m`.
2. `build_case(..., wall_ks_mm=None)` → impeller + frame/stator rough when set; casing always smooth.
3. `evaluate_candidate` / mixed / Optuna / CLI `--wall-ks-mm` / cockpit Assess switch stamp `wall_ks_mm`.
4. `apply_print_penalty(..., tip_thickness=)` lerps η from 0.92 (t≤0.04) to 0.96 (t≥0.10); CFM stays ×0.95.
5. Score caption shows `wall ks … mm` when stamped.

## Non-goals

- Default-on roughness (would shift every historical campaign)
- FSI / blade deflection
- Fitting `ks` or print factors to one scraped table
- Rough prop open-air nut BC
- Dual-counting “fix” for roughness: algebraic print penalty still applies with ks (covers FSI/layers); turn penalty off in code for smooth-wall/resin escapes

## Tests (no Docker)

Case writer asserts rough impeller+frame / smooth casing; print η lerp; CLI argv; isolated job; cockpit switch string.
