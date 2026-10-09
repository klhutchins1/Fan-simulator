# New lead (from QA, 2026-10-08): get static pressure from the blade's axial force, not "Euler work minus swirl"

**Verdict: this is the real fix for QA-4, and it is worth proposing next. It still needs recalibration, so no patch yet.**

## Why
- `fan_bem.operating_point` sets static rise = ρ·U·(SLIP·vθ) − ½ρ(SLIP·vθ)² − friction.
- Swirl from blade *drag* therefore counts as useful pressure. A paddle or a reversed blade that just churns air gets credited with a positive pressure rise and about 55 % efficiency.
- Adding post-stall drag (as in lead #9) makes this worse: paddle free CFM goes from 62.5 to 95.8.
- The physical static rise across a rotor is set by the blades' **axial** force, B·½ρW²c·(cl·cosφ − cd·sinφ), per unit area. Drag and negative lift lower it.

## Prototype
Code: `proto/bem_variants.py`, `axial_force=True`, with and without the post-stall polar `ps`. Same SLIP, leak and friction knobs; **not recalibrated**.

| case | base: free / shut-off / peak η | axial force + post-stall |
|---|---|---|
| Stock (7-station) | 58.2 / 38.9 / 0.536 | 53.4 / 5.4 / 0.29 |
| top 5 / S03681 | 61–64 / 40–42 / ~0.54 | 57–59 / 7.5–8 / 0.21–0.27 |
| paddle 89° | 62.5 / 38.9 / 0.549 | **8.0 / 0.3 / 0.002** |
| reversed −45° | 7.6 / 38.0 / 0.528 | **no free delivery, −6.6 Pa** |
| 0 blades | none | none |

Both exploits disappear. Shut-off is now far too low (5 Pa), so the loss knobs need recalibrating against the 60.1 CFM / 22.9 Pa references. Combining this with the Koch cap and Carter's rule is the natural next step.

## Effort and next steps
- Effort: M, including recalibration and re-running Audit #4.
- First, track it as its own lead.
