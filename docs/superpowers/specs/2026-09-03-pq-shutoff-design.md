# Honest P–Q shut-off (stage 4)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Extract testable `free_delivery_cfm` / `shut_off_pa` / `curve_report` so the fan-curve script stops calling `max(static_pa)` shut-off. Interpolate static rise to Q=0 when the sweep actually got near zero flow. Stamp `eta_total` on CSV rows when metrics have it. Do not run a Docker sweep. Do not claim AMCA shut-off.  
**Roadmap:** §1.5 stage 4. Steady RANS near stall is known to under-read (~13 vs 22.9 Pa). This slice stops lying about what the sweep measured.

## Plain language

`run_fan_curve.py` already sweeps velocities and interpolates free delivery at ΔP=0. It then prints `shut-off dP ~ max(dp)`. Peak pressure in a velocity sweep is not Q=0. Stage 4 reports Q→0 only when the points support it, otherwise `None`, and writes `fan_curve.json` the same way the GCI script writes a report.

## Problem

```text
print(f"shut-off dP ~ {max(dp):.1f} Pa")   # not shut-off
free_delivery_cfm lives in the script, untested
CSV has efficiency_pct (static) only
```

## Goal

1. **`fansim/analyze/fan_curve.py`** (no Docker, no Trame):

```text
free_delivery_cfm(points) -> float | None     # move from the script; ΔP sign-change vs CFM
shut_off_pa(points, *, q_near_zero=5.0) -> float | None
  sort by cfm
  if min(cfm) > q_near_zero → None
  else linear interpolate/extrapolate static_pa to cfm=0 using the two lowest-Q points
  if the lowest point is already cfm≈0 → that static_pa
curve_report(points) -> dict
  free_delivery_cfm, shut_off_pa, peak_static_pa, n_points
```

`points` rows have `cfm` and `static_pa` (same as today’s CSV).

2. **Script** uses those helpers. Print:

```text
free delivery ~ X CFM
shut-off (Q→0 interp) ~ Y Pa     # only if shut_off_pa is not None
shut-off: not in sweep (need a point ≤ 5 CFM; do not use peak ΔP)
```

Write `fan_curve.json` = `curve_report` plus `"points": points`. Keep CSV + PNG. Peak ΔP may appear in the JSON as `peak_static_pa`; never label it shut-off.

3. **CSV** — add `eta_total` (fraction, or empty). `point_row(metrics, inlet_v)` fills today’s keys plus `eta_total` from `FanMetrics.eta_total` (None → omit / blank). Do not replace `efficiency_pct`.

4. **Do not** change duct length, BCs, `--layers`, NSGA, or published 22.9 Pa as a sim result.

## Tests (no Docker)

- Existing free-delivery crossing still works after the move (ΔP +10 at 40 CFM, −5 at 70 CFM → interp ~60).
- Two low-Q points 2 CFM / 20 Pa and 8 CFM / 15 Pa → `shut_off_pa` ≈ 21.67 (line through to Q=0).
- All points > 5 CFM → `shut_off_pa is None`.
- `curve_report` never sets `shut_off_pa` equal to `peak_static_pa` on a sweep whose min Q is 40 CFM.
- `point_row` copies `eta_total` when set, None when missing.

## Non-goals

- Running the OpenFOAM sweep
- Transient / LBM shut-off
- AMCA chambers, pressure-driven `--back-pressures` rewrite
- `--layers` on this script
- Replacing NSGA 2-point hose score with a full curve
