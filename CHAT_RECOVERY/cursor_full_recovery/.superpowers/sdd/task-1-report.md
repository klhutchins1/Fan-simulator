# Task 1 Report: Extract `figures.py` + clean `test_cockpit_view.py`

**Status:** DONE  
**Branch:** `cockpit-tab-split`  
**Commit:** `9003d46` — `refactor(cockpit): extract figures.py; drop source-grep UI tests`

## Summary

Extracted six pure helpers from `fansim/cockpit/app.py` into new `fansim/cockpit/figures.py`, rewired imports in `app.py` and tests, renamed `_reject_hint` → `reject_hint`, and removed 14 source-grep UI tests plus `_read_cockpit_app_source`.

## Step 1: `_has_real_cfm` call sites

```
rg "_has_real_cfm" fansim/cockpit tests
```

Only used inside `app.py` (definition + 3 Fan Assess/select call sites). **Left in `app.py`** for Task 7 (`fan_helpers`).

## Step 2: Created `fansim/cockpit/figures.py`

Moved unchanged (except rename):

| Function | Notes |
|----------|-------|
| `prop_scatter_figure` | Prop thrust vs noise scatter |
| `cror_scatter_figure` | CROR BEMT-proxy scatter |
| `mf_scatter_figure` | Mixed-flow CFM scatter |
| `scatter_figure` | Fan design-space scatter |
| `filter_fitting_designs` | Nominal fit gate for Results scatter |
| `reject_hint` | Was `_reject_hint` |

Module docstring and imports per brief (`plotly.graph_objects`, `nominal_fits_spec`).

## Step 3: Updated `app.py`

- Removed ~218 lines of moved function bodies.
- Added import from `fansim.cockpit.figures`.
- Replaced 5 `_reject_hint(` calls with `reject_hint(`.
- Removed unused `import plotly.graph_objects as go`.
- Kept `nominal_fits_spec` import (still used directly at line ~636).
- Updated test-mode comment to reference `figures.py`.

## Step 4: Cleaned `tests/test_cockpit_view.py`

- Added module docstring warning against source-grep UI tests.
- Changed imports to `fansim.cockpit.figures`.
- Updated `reject_hint` test calls.
- Deleted `_read_cockpit_app_source` and 14 source-grep tests.
- **Kept 9 behavioral tests:** `test_reject_hint_*` (3), `test_filter_fitting_designs_*`, `test_results_for_hub_*`, `test_scatter_*` (2), `test_format_elapsed_*`, `test_busy_caption_*`.

## Step 5: Tests

```
uv run python -m pytest -q tests/test_cockpit_view.py
.........                                                                [100%]
9 passed in 4.18s
```

Exit code `-1073741819` on Windows (OCCT/VTK teardown noise per plan); all assertions passed.

## Self-review

| Check | Result |
|-------|--------|
| No behavior change beyond `reject_hint` rename | ✓ |
| Only Task 1 files committed | ✓ (3 files) |
| No Tasks 2–7 work | ✓ |
| No new source-grep tests | ✓ |
| `_has_real_cfm` not moved | ✓ |
| `app.py` still imports moved symbols for transition | ✓ |

## Concerns

None. Working tree clean after commit.

## Files changed

- `fansim/cockpit/figures.py` (new, 227 lines)
- `fansim/cockpit/app.py` (−218 net)
- `tests/test_cockpit_view.py` (−222 net, 9 tests remain)
