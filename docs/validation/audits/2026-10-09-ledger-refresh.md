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

## Command evidence

```
uv run pytest -q -m "not docker" tests/audit/test_stock_handedness.py tests/test_blade_golden.py \
  tests/test_a12x25_reference_geometry.py tests/test_tip_trim.py tests/audit/test_prop_builder_direction.py
22 passed in 273.08s
```
