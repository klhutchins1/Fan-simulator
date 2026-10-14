# 25.10 near-stall flag — pre-registered 2026-10-14

Written **before** inspecting 9610 / 9604 / 9613 / 9608 / t9005 recipes. Thresholds are
literature + the BEM polar already in `fansim/fan_bem.py`, not fitted on the hold-out.

## Why

Q3 ranked 9610 #1 (~59 CFM load). Full Assess then sat near stall under the case hose
(37.1 CFM, unconverged). Q3’s CFM is the thing that missed it, so this flag must **not**
be “BEM load/free is small”. It looks at incidence and Lieblein loading at the BEM hose
operating point.

## Frozen inputs

| symbol | value | source |
|---|---|---|
| hose | case: 8 Pa @ 50 CFM, ΔP = k Q² | Assess default (`presets.PRESETS["case"]`) |
| RPM | 2000 | a12x25 rated |
| tip gap | BEM default (0.5 mm unless a full ring) | `fan_bem.DEFAULT_TIP_GAP_MM` |
| α_stall(Re) | `max(8, min(15, 10 + 3 log10(Re/20000)))` deg | `fan_bem._cl_cd_post_stall` |
| stall margin | **0.0°** | polar edge is stall; a 2° pre-stall band flags Stock |
| DF limit | **0.60** | Lieblein 1959; already `meanline.DF_LIMIT` |

## Rules (any one flags; never changes a score)

- **N1 incidence:** at the BEM hose operating point, any of 20 radial elements has
  **signed** `α ≥ α_stall(Re)` (positive α = overloaded / suction-side stall).
  Negative α is high-flow unloading, not the 9610 failure mode.
  **Ruling A:** first draft used `|α|`; Stock on the case hose has a station at α ≈ −7.6°,
  which is not stall.
  **Ruling B:** a 2° pre-stall band flags Stock (max α ≈ 7.5°, α_stall ≈ 9.1°). Margin
  is 0: flag at or past the polar edge. Both rulings used Stock as the specified
  negative control, **before** looking at 9610.
- **N2 no intersect:** BEM cannot put an operating point on this hose (already stalled /
  no rise).
- **N3 Lieblein:** max station DF at that OP `> 0.60`.

The optimizer objectives are unchanged. Assess may show a caption. CFD still runs.

## Hold-out (not used to pick the numbers)

After the code exists, run the same case hose on: **9610** (should flag), **9604**,
**9613**, **9608**, **Stock**, **t9005** (should not). If this fails, **do not widen or
tighten** the table above — record FAIL.

## Not in this flag

- CFD oscillation / unconverged probe (already in `objectives.py` after the run).
- Skipping CFD or returning INFEASIBLE.
