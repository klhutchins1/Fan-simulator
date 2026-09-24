# obj_2 shaft power is a datasheet mismatch

**Date:** 2026-09-23  
**Status:** approved (2026-09-23)  
**Approach:** Record the mismatch. No new solve.

## Plain language

The wall solve's 2163 W is the pressure moment of a radial impeller. The 388 W it was compared with is an FPV 5×4.3×3 datasheet scaled by rpm³. Those are different machines. This slice writes that down. It does not rerun CFD.

## Facts

- `validation/reference/drone_radial/obj_2_ccw.stl` comes from `radial+impeller_stls`. Hub radius 30.4 mm, tip radius 45.4 mm (hub/tip 0.67, blade span 15 mm), axial depth 28 mm, watertight.
- Wall stamp `obj_2_ccw_wall.json`: 1131 g, 2163 W, figure of merit 0.139. Iteration 400 moment 0.818 N·m = 0.812 pressure + 0.006 viscous.
- `scripts/run_prop_obj2_wall.py` calls `datasheet_compare` with `get_prop_spec("fpv_5inch")` (1850 g and 650 W at 30 000 rpm, hub diameter 12 mm). At 25257 rpm that power scales to 388 W. `within_2x` checks thrust only, so the stamp can say `within_2x: true` at a power ratio of 5.58.
- Forces use the compressible density on the impeller patch about the origin. Net thrust is 11.1 N. A reference-pressure leak on this closed body would not leave an 11 N thrust and a 0.8 N·m moment. Viscous moment is under 1%, so another wall mesh cannot close a 5.6× ratio.
- Ideal actuator-disk power for the wall thrust on this disk is about 300 W. Figure of merit 0.14 means this disk is a poor hover prop.

## What lands

1. One paragraph in the wall section of `docs/validation/drone_radial_open_air_cfd.md`.
2. §4.4 step 4 on `docs/roadmap.md`, marked done. The §4.4 checkbox stays open because AMI stays parked. §4.3's "next CFD work is why obj_2 shaft power is ~2 kW" sentence is updated to point at step 4.
3. §14.8 open items for the prop cockpit: stop, project-drive load, randomize, and a wiring audit.

## Non-goals

- Editing `obj_2_ccw_smoke.json`, `obj_2_ccw_refine.json`, `obj_2_ccw_gci.json`, or `obj_2_ccw_wall.json`
- Another mesh, an AMI retry, or a new `fpv_5inch` CFD smoke
- Checking §4.4
