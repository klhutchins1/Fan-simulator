# Fast-suite baseline (2026-09-14, refreshed)

**Date:** 2026-09-14  
**Commit:** (see git after this note lands) — follow-on to `4fa70ed` baseline.

## Original failing nodeids (4fa70ed)

| Nodeid | Status after refresh |
|--------|----------------------|
| `tests/test_cockpit_view.py::test_results_for_hub_hides_foreign_envelope` | **PASS** (hub_models restore) |
| `tests/test_des_fwh.py::test_apply_des_transient_writes_pimple_and_faces` | **PASS** (DES templates restored) |
| `tests/test_fan_curve.py::test_point_row_eta_total` | **PASS** (`FanMetrics.eta_total`) |
| `tests/test_problem.py::test_stub_archetype_fails_loudly` | **PASS** (stub class; centrifugal is MixedFlow) |
| `tests/test_prop_noise.py::test_more_blades_lower_loading_term` | **PASS** |
| `tests/test_search_rpm.py::test_cli_declares_search_rpm_and_bounds` | **PASS** |

## New math guards

`tests/test_math_consistency.py` — §10.3 / 10.7 / 10.8 / 10.9 / 10.10 smoke checks (CFM factor, ρ=1.2, BEM Q→0 shut-off, no Prandtl on ducted BEM, screening GCI stamp, circular inlet helper).

## Process exit note

On Windows, OpenCascade (OCCT) teardown can exit with `0xC0000374` / `3221225477` (or similar non-zero codes such as `-1073741819`) **after** pytest prints a green assertion summary. Those exit codes are **not** treated as test failures when the pytest summary line reports passes.
