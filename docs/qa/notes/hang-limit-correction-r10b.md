# Hang limit and clip correction (QA round 10b Task C) — FINAL

Prereg `26aa359`. Scripts: `handoff/2026-10-13_from-qa-10/scripts/{c1_hang,c2_measure,analyse_c2,c3_eval}.py`.

## C.1 Designed hang distribution (400 designs, all forced to cylinder wrap and clipped)
| set | hang > 0 | refused (> 2 mm) | median of the hangs | max |
|---|---|---|---|---|
| round-9 B.3 200 (seed 9011) | 39 | 8 | 1.55 mm | 7.15 mm |
| fresh 200 (seed 10012, shrouded allowed) | 29 | 11 | 1.63 mm | 5.52 mm |
| all 400 | 68 (17 %) | **19 (4.75 %)** | 1.56 mm | 7.15 mm |

- Claude's 39/200, 8/200 and 7.2 mm are reproduced exactly.
- `validate_blade_params` refuses if and only if the designed hang is > 2.0 mm on 400/400. It refused nothing else.
- On the round-9 200, my realised-loft hang is a median **1.65×** the designed hang (38 designs where both are > 0). Max
  realised 12.95 mm vs designed 7.15 mm. 1 design hangs as designed but not as realised; 2 hang as realised but not as designed.
- No shrouded design among the 400 hangs.

## C.2 Built vs sliders on every allowed hanging design: **PASS**
- 49 designs (48 NACA, 1 plate) and 105 stations, all readable. 0 errors.
- Readings: max |chord| 2.90 % (limit 3 %), max |camber gap net| 0.0048 (limit 0.005), max |stagger| 1.46° (limit 1.5°).
  0 stations fail.
- 46 stations are clip-reached and 47 were touched by the correction. On those, the maxima are 2.9 % / 0.0048 / 0.74°.
- QA-32 is **verified closed** on this population. The margins are thin, though: the worst chord and camber are at 97 % of
  the limit. The largest stagger error (1.46°) is on a station the clip does not reach.
- The bias was taken from each design's own section family (prereg).

## C.3 Optimizer treats refusal as infeasible: **PASS**
- S5_0209 → `feasible=False`, reason "geometry failed: ValueError: the blades hang 7.2 mm below the hub's motor face (limit
  2 mm): that part would be cut off and strike the frame struts. Reduce the stagger or sweep at the trailing edge, or make
  the hub taller". S4_0264 gives the same message at 4.4 mm.
- No mesh or CFD stub was called.
- The message is plain. The "geometry failed: ValueError:" prefix is developer-ish (cosmetic).
- 5 other refused designs never reach this gate: the tip-gap gate rejects them first (tip gap −1.5 mm).

## C.4 Misjudgements: none found
- All 19 refused designs have their lowest designed point at r 33.5–56.5 mm, which is outboard of the hub (r 18–26). No
  refusal comes from hub-embedded root material.
- No allowed design was distorted beyond the C.2 limits.
