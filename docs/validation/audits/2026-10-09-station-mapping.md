# One station→radius mapping for builders and analyses (§23.35) — pre-registered 2026-10-09

Written before any of the change's numbers were computed.

## The defect

Every geometry builder (`fansim.geometry.blade`, `fit`, `placement`, `chord_realisation`) places a
station at `r = r0 + r_frac·(R − r0)` with `r0 = hub_radius − root_embed` (the blade root sinks
`root_embed` mm into the hub for a clean fuse). The analyses place the same station at
`r = hub_radius + r_frac·(R − hub_radius)`:

- `fan_bem._interp_geometry` (BEM pre-screen, Audit #4), `propeller.bemt._interp_geom` (Audit #3),
- `geometry.blade.blade_solidity` (the `--loadcap` floors, printability score),
- `optimize.meanline` (cockpit meanline seed),
- `propeller.geometry.prop_blade_params` (pitch twist computed at hub-mapped radii, lofted at
  builder radii: ~0.5° at mid on a 5×4.3).

So the analyses describe a blade ~1 mm (mid) to 2 mm (root) outboard of the one that is built.

Found while fixing it (added before any post-change number was computed): the builders interpolate
between stations with `span_interp` (Stock and Stock v1 use `pchip`), but `fan_bem` and
`propeller.bemt` always interpolate linearly. Same defect class — the analysis is not reading the
built blade — so it is fixed in the same change: one station-interpolation helper shared by the
builders' `_interp_stations` and both analyses.

## The fix

Direction: **the analyses follow the builders**. Geometry is what gets printed and what CFD sees; moving
the builders would change the validated Stock geometry and need new CFD. One shared helper
(`station_root_radius` / `radius_at_r_frac` / `r_frac_at_radius` in `fansim.geometry.blade`); analyses
keep integrating over the exposed span `hub_radius … tip_radius` and read the geometry at each physical
radius through the builder mapping. Structural span (`tip − hub`) and the CFD spanwise post-processing
already use physical radius and are unchanged.

## Pass criteria (fixed now)

| id | check | rule |
|---|---|---|
| G1 | fan geometry | golden + reference-geometry tests pass unchanged (refactor only; no tracked reference STL changes) |
| G2 | prop twist | at each prop station, stagger = pitch angle at the radius the loft places it, within 0.01° |
| B1 | Audit #4 tests | `tests/audit/test_fan_bem_audit.py` passes (Stock v2 free air within ±25 % of CFD; slope order; v1 > v2) |
| B2 | Audit #4 ranking | Spearman ρ (BEM free vs CFD free, `scripts/audit_bem_vs_cfd.py`) ≥ 0.6 (the registered floor) **and** not more than 0.05 below the value recomputed on the unchanged code just before the change |
| P1 | Audit #3 | `propeller.bemt` registered checks pass at their registered tolerances |
| L1 | load-cap floors | report Stock `blade_solidity` hub/mid/tip before and after; FAIL if any guided-space design in the BEM screen's shortlist flips across a floor *and* the change in its solidity exceeds 3 % (would mean the floors need re-tuning first) |
| R1 | audit ledger | every unit `scripts/audit_status.py` marks CHANGED/AFFECTED re-runs its registered checks green before `record_pass` |

Any FAIL → do not merge; report. No threshold is changed after seeing data.

## Result (2026-10-09) — **FAIL (B2, P1). Not merged**; kept on branch `station-mapping-23-35`.

| id | verdict | evidence |
|---|---|---|
| G1 | PASS | golden + reference-geometry + LE-leads tests green; no tracked reference STL changed |
| G2 | PASS | `tests/test_station_mapping.py::test_prop_twist_matches_pitch_at_the_lofted_radius` |
| B1 | PASS | `tests/audit/test_fan_bem_audit.py` green (Stock v2 BEM free 57.8 vs CFD 56.5) |
| B2 | **FAIL** | ρ 0.714 (unchanged code) → **0.429** (< 0.6 floor; −0.29) |
| P1 | **FAIL** | `test_uiuc_apcsf_ct_j_attached_rms_within_reregistered_tolerance`: worst C_T RMS **0.0203** > 0.020 |
| L1 | PASS | 0 of 30 BEM-screen shortlist designs cross a load-cap floor; max mid/tip change 3.9 %. Stock 1.079/0.806/0.846 → 1.073/0.827/0.846 |
| R1 | not run | nothing recorded (FAIL) |

Audit #4 rows, BEM free CFM before → after (CFD): stock_v2 58.2 → 57.8 (56.5), stock_v1 61.9 → 59.5
(77.4), t9000 57.6 → 57.5 (51.7), t9005 58.4 → 57.7 (67.2), t9006 60.7 → 60.3 (52.5), t9008 61.1 → 61.3
(55.1), t9012 39.1 → 39.1 (27.4).

**Diagnostic, after the verdict (does not change it):** splitting the change on the Audit #4 set —

| variant | ρ |
|---|---|
| unchanged (linear interpolation, hub mapping) | 0.714 |
| builder radius mapping only | 0.714 |
| builders' pchip interpolation only | 0.429 |
| both (this change) | 0.429 |

Reading Stock v1's pchip loft correctly lowers its BEM free air 61.9 → 58.4 CFM (CFD 77.4), which
reorders the near-tied 57–61 CFM cluster. The BEM's 0.714 therefore partly rested on it reading the
blade differently from how it is built; its ranking skill on these 7 designs is weak either way
(consistent with QA-4 / roadmap §23.5). Any retry is a new pre-registration — e.g. mapping-only — and
must say it was chosen after seeing this split.
