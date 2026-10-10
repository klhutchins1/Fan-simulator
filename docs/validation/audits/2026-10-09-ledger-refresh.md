# Ledger refresh — 2026-10-09

Change-driven re-audit after the QA-bot handoff fixes (branch `qa-fixes-2026-10-09`).

## Method

Same as `2026-10-08-ledger-refresh.md`: `scripts/audit_status.py` → re-run each CHANGED unit's
registered `checks` (no Docker) → on green, `record_pass` with the new fingerprint and this report.

## Results

| Unit | Change | Checks | Verdict |
|------|--------|--------|---------|
| `geometry.stock_handedness` | §23.32 `_trim_blade_to_tip_cylinder`: after the 4 plain retries, fallbacks (outer-ring cut, 0.1 µm fuzzy common, ShapeFix + common, each on a copy); every result, plain or fallback, must end within 0.1 mm of R, else RuntimeError. Fan blades take the first plain intersect, so Stock geometry is unchanged. | `tests/audit/test_stock_handedness.py` + golden/reference geometry + `tests/test_tip_trim.py` + `tests/audit/test_prop_builder_direction.py` | **PASS** — 22 passed; random prop flats that were left ~1 mm untrimmed now trim (8/8, ≤ 0.05 mm past R) |

AFFECTED dependants (`cfd.archetype_direction`, `cfd.cfm_from_outlet_flow`,
`cfd.flow_direction_convention`, `propeller.cfd_setup`, `propeller.thrust_sign`) return to PROVEN with
their parent; none of their own code changed.

Not recorded: §23.35 (one station→radius mapping) FAILED its pre-registered checks (Audit #4 ρ
0.714 → 0.429; Audit #3 APC C_T RMS 0.0203 > 0.020) — `2026-10-09-station-mapping.md`; code kept
unmerged on branch `station-mapping-23-35`.

The full registered-check suite was also run once with §23.35 applied (583 tests: 1 failed, the P1
check above); everything else, including the golden geometry, was green.

## Second pass (same day): prop efficiency (QA UI-5, §23.18)

| Unit | Change | Checks | Verdict |
|------|--------|--------|---------|
| `propeller.polar_coefficients` (**new**) | `nondim` / `advance_ratio` / `v_inf_from_j` were on the registry's *exempt* list ("scaffolding"), though `nondim` makes an equation claim — which is how the bug below escaped the audit. Registered now. Fix found by the QA bot: η = J·CT/CP (= T·V/P); the code divided by an extra 2π (the ω-based C_Q form), so every forward-flight η was 6.3× low (~6 % where APC publishes ~35 %). Fix written here after review (`docs/qa/patches/prop-solver-fix.diff` was not applied as-is). | `tests/test_prop_polar.py` (identity now also pinned to T·V/P) | **PASS** |
| `propeller.bemt` | No solver change; its audit test's efficiency bound `j·ct/(2π·cp)·2π < 1` simplified to `j·ct/cp < 1` (same value). | `tests/audit/test_prop_bemt_audit.py`, `tests/test_bemt.py`, `tests/test_bemt_catalog.py` | **PASS** |

Not taken from the QA patch (yet): its UIUC GWS 5×4.3 regression points (η 0.646 at J 0.572; static
CT0 0.149) — to be transcribed from the UIUC source files directly before they become a check.

## Third pass (same day): a measured-prop check for the BEMT

| Unit | Change | Checks | Verdict |
|------|--------|--------|---------|
| `propeller.bemt` | New registered check `tests/test_prop_uiuc_gws.py`: UIUC Propeller DB GWS Direct-Drive 5×4.3 (2 blades), read from the unmodified source files (sha256 verified against the QA bot's `SOURCES.md`; `tests/data/uiuc_gws_5x4.3/`). Tolerances proposed by the QA bot before this geometry was run. The source geometry includes the r/R 1.00 station (c/R 0.0176) that the QA transcription had dropped. | the unit's checks + the new file | **PASS** — η 0.606 vs measured 0.646 at J 0.572 (tol ±0.10); static CT0 0.1365 vs 0.149 at 7407 rpm (−8.4 %, tol ±15 %) |

## Fourth pass (same day): axial-force BEM + pre-CFD exploit guard (QA-4)

| Unit | Change | Checks | Verdict |
|------|--------|--------|---------|
| `fan.bem_prescreen` | Opt-in `pressure_model="axial_force"` in `operating_point` / `pq_curve` (QA bot's model, re-implemented after review, not applied as a diff). Default `euler` unchanged (Stock 58.2 CFM / 38.87 Pa, asserted). Reproduces the QA numbers exactly: Stock 59.8 / 22.08 Pa, paddle 89° 14.0 CFM η 0.9 %, reversed −45°/−60° no rise (−22.5 / −19.2 Pa). QA's pre-registered rule (c) on 16 CFD designs: ρ 0.809 (Euler 0.827) — PASS; it is not a better ranker. | unit checks + `tests/test_fan_bem.py` (new cases) | **PASS** |
| `optimize.reject_dead_designs` | New `bem_exploit_reason`: refuses a design before CFD when the axial-force BEM finds no pressure rise or peak η < 5 %. Always on in `evaluate_candidate` (`exploit_guard=True`). Threshold margin: paddle 0.9 %; lowest of 93 real designs (16 CFD-scored, every saved design, both QA shortlists) 28.8 %; none of the 93 has no rise. | `tests/audit/test_dead_design_guard.py`, `tests/test_bem_exploit_guard.py` | **PASS** |

## Axial-force energy bound (same day, branch `axial-force-bem`)

| Unit | Change | Checks | Verdict |
|------|--------|--------|---------|
| `fan.bem_prescreen` | axial_force static rise capped at shaft work per volume (air power ≤ shaft power). QA r4 found peak η up to 115 % on dense 11-blade editor designs; E_rand1396 111 % → 100 %. QA reference cases unchanged (Stock 59.8 / 22.08 Pa, paddle 14.0 CFM η 0.9 %, reversed no rise). | unit checks + `tests/test_fan_bem.py` | **PASS** |

## Command evidence

```
uv run pytest -q -m "not docker" tests/audit/test_stock_handedness.py tests/test_blade_golden.py \
  tests/test_a12x25_reference_geometry.py tests/test_tip_trim.py tests/audit/test_prop_builder_direction.py
22 passed in 273.08s
```
