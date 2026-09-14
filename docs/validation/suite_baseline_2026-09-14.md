# Fast-suite baseline (2026-09-14)

**Date:** 2026-09-14  
**Commit:** `4fa70ed102afc7b5467d347a451264e54ef6f614`

## Command

```powershell
uv run --extra optim --extra viz --extra surrogate --extra dev `
  python -m pytest -m "not docker and not slow" -q --tb=no `
  | Tee-Object docs/validation/_suite_raw.txt
```

## Counts

| Outcome | Count |
|---------|------:|
| Passed  | 602 |
| Failed  | 6 |
| Skipped | 4 |
| Deselected | 10 |

Pytest summary: `6 failed, 602 passed, 4 skipped, 10 deselected` in ~812s.

## Failing nodeids

- `tests/test_cockpit_view.py::test_results_for_hub_hides_foreign_envelope`
- `tests/test_des_fwh.py::test_apply_des_transient_writes_pimple_and_faces`
- `tests/test_fan_curve.py::test_point_row_eta_total`
- `tests/test_problem.py::test_stub_archetype_fails_loudly`
- `tests/test_prop_noise.py::test_more_blades_lower_loading_term`
- `tests/test_search_rpm.py::test_cli_declares_search_rpm_and_bounds`

## Process exit note

On Windows, OpenCascade (OCCT) teardown can exit with `0xC0000374` / `3221225477` (or similar non-zero codes such as `-1073741819`) **after** pytest prints a green assertion summary. Those exit codes are **not** treated as test failures when the pytest summary line reports the pass/fail/skip counts above.
