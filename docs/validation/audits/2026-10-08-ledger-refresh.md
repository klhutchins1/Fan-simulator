# Ledger refresh — 2026-10-08

Change-driven re-audit after the §23 QA fixes landed new fingerprints on four PROVEN units.

## Method

Same as `2026-09-30-ledger-refresh.md`: `scripts/audit_status.py` → re-run each CHANGED unit's
registered `checks` (no Docker) → on green, `record_pass` with the new fingerprint and this report.

## Results

| Unit | Change | Checks | Verdict |
|------|--------|--------|---------|
| `optimize.search_space_handedness` | §23.1: flat dicts carry the full station recipe (`stations` / `station_slots`); slot edits apply as interpolated deltas. Stock now builds all 7 stations through the cockpit/print-ready path instead of 3. | `tests/audit/test_search_space_handedness.py` | **PASS** — handedness unaffected; carriage is additive for 3-station designs |
| `fan.bem_prescreen` | §23.4: `pq_curve` returns free delivery 0 + `free_status="no_rise"` when static rise is never positive (was: sweep max flow); hub ≥ tip / 0 blades return early. `bem_screen_cfm` returns (0, 0) then. | `tests/audit/test_fan_bem_audit.py`, `tests/test_math_consistency.py` | **PASS** — Stock unchanged (58.2 CFM, 38.87 Pa); Audit #4 ranking set never hits `no_rise`, so its ρ = 0.714 stands |
| `geometry.stock_handedness` | §23.3: `build_impeller` / `build_impeller_preview` call `validate_blade_params` (n ≥ 2, 0 < hub < tip, finite stations, chord/thickness > 0, blade-angle count). | `tests/audit/test_stock_handedness.py` | **PASS** — validation only rejects impossible inputs |
| `audit.direction_geometry` | §23.6: `motor_side` accepts a root radius only if the loop count holds 1 % of tip further out (a cut on a centre-bore wall gave spurious loops; Linux float landed exactly on it). New test forces that case. | `tests/audit/test_direction_geometry.py` | **PASS** (incl. the forced bore-wall case, ±1) |

AFFECTED dependants (`cfd.archetype_direction`, `cfd.cfm_from_outlet_flow`,
`cfd.flow_direction_convention`, `propeller.cfd_setup`, `propeller.thrust_sign`) return to PROVEN
once their parents re-pass; none of their own code changed.

Stock golden (`validation/reference/a12x25_blade_golden.json`) regenerated deliberately for §23.1:
volume −0.21 %, tip radius and depth unchanged, bounds ≤ 0.05 mm, tip-section samples ≤ 0.94 mm
(the tip now follows the real r/R 0.84 and 1.0 stations). The close-ref envelope check still passes.

## Second pass (same day)

| Unit | Change | Checks | Verdict |
|------|--------|--------|---------|
| `geometry.stock_handedness` | §23.31 `_root_axial_span` takes the innermost station by `r_frac` (was `stations[0]`); §23.32 `_trim_blade_to_tip_cylinder` raises instead of returning an untrimmed blade; §23.34 chord-measure hub cutoff derived from the design's hub (A12x25 unchanged: 0.4697 vs 0.47). | `tests/audit/test_stock_handedness.py` | **PASS** — Stock geometry unchanged (stations already ordered; trim never failed; no station near the cutoff) |

Not kept (both reverted, see roadmap §23.5): a Viterna–Corrigan post-stall extension in
`propeller.polars` (broke `test_prandtl_factor_bounded_and_inflow_iteration_converges` at J = 0) and a
profile-drag loss in `fan_bem` (Audit #4 ρ 0.714 → 0.126). Neither was recorded.

## Third pass (same day)

| Unit | Change | Checks | Verdict |
|------|--------|--------|---------|
| `geometry.stock_handedness` | §23.17 `build_blade_solid(_trim_tip=False)` for chord-measurement builds only (measured radii ≤ 0.99·tip, where the trim removes nothing); realised loft chords within 0.029 mm of before on 5 designs (limit 0.05, set before measuring). §23.32 follow-up: a blade already inside the tip cylinder (rounded tip) is returned instead of raising. | `tests/audit/test_stock_handedness.py` + golden | **PASS** |

## Command evidence

```
uv run pytest -q tests/audit/test_direction_geometry.py tests/audit/test_stock_handedness.py \
  tests/audit/test_fan_bem_audit.py tests/test_math_consistency.py \
  tests/audit/test_search_space_handedness.py
66 passed in 122.21s
```
