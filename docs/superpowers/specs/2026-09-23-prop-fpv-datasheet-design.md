# fpv_5inch BEMT versus its own datasheet

**Date:** 2026-09-23  
**Status:** approved (2026-09-23). Plan: `docs/superpowers/plans/2026-09-23-prop-fpv-datasheet.md`.  
**Approach:** Record the existing static check. Do not retune BEMT.

## Plain language

`bemt_datasheet_report` already compares the 5-inch freestyle prop to its own datasheet. At the datasheet rpm the BEMT thrust and shaft power both sit near 0.9 of the published numbers. This slice writes those numbers down. It does not change the blade model to hit 1850 g or 650 W.

## Measured point

Command: `uv run python scripts/calibrate_prop_datasheet.py --spec fpv_5inch`  
Point: `fpv_5inch` at `ref_rpm` 30 000. No Docker.

| | BEMT | Datasheet | Ratio |
|---|---:|---:|---:|
| Thrust | 1654 g | 1850 g | 0.894 |
| Shaft power | 572.6 W | 650 W | 0.881 |
| Figure of merit | 0.648 | | |

`within_2x` is true. It checks thrust only. The CLI print line shows thrust and omits power; the JSON payload already has both ratios.

## What lands

1. One sentence on roadmap §4.3 pointing at this spec and the two ratios. §4.3 stays unchecked. This is a BEMT screening check, not the compressible CFD tier.
2. The CLI print line includes shaft power and `power_ratio`, matching the JSON.

## Non-goals

- Retuning camber, pitch, stall, or compressibility so the ratios become 1
- Any obj_2 CFD, mesh, or AMI run
- Comparing this prop to the radial-impeller stamps
- Checking §4.3 or §4.4
