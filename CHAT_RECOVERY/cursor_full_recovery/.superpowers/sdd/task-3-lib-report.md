# Task 3 — Persistent 3D column and Library click — Report

## Status
- Implemented persistent 3D column + Library click-to-Fit and Scale button.

## Commit
- `18f3fe0` — Keep 3D visible and Fit a library recipe on click.

## Key changes
- `fansim/cockpit/app.py`
  - Library tab uses `library_list_items(...)` + `apply_library_recipe(...)` and applies on click (Fit) without creating a placed row or switching tabs.
  - Removed `_place_library` and removed the Library dropdown (`VSelect`).
  - After successful apply: `_init_editor(...)`, `_set_baseline()`, then `do_preview()`.
  - `refresh_library()` now describes click-to-Fit behavior and counts only `role == "row"` items.
  - 3D plot (`plotter_ui(plotter)`) is no longer gated by `fan_subtab === 'design'` (single instance).
  - `_assess(...)` adds `parent_id/place_op/placed_on/cfd_stale=False` when `state.library_parent_id` is set.
- `tests/test_cockpit_view.py`
  - Updated to assert on `library_list_items(...)` rows (role == "row").

## TDD evidence

### Step 1/2 — updated unit test
Command:
```bash
uv run python -m pytest tests/test_cockpit_view.py -v --tb=short
```

Output:
```text
tests/test_cockpit_view.py::test_results_for_hub_hides_foreign_envelope PASSED [ 50%]
tests/test_cockpit_view.py::test_scatter_colorbar_not_capped_at_22 PASSED [100%]
============================= 2 passed in 17.37s ==============================
```

### Step 4 — required suite
Command:
```bash
uv run python -m pytest tests/test_library_view.py tests/test_cockpit_view.py tests/test_placement.py tests/test_catalog.py tests/test_labels.py -q -m "not docker and not slow" --tb=short
```

Output:
```text
34 passed in 5.06s
```

Note: On this Windows environment, pytest prints PASS but the process exits with a non-zero NTSTATUS (`-1073741819`), suggesting a native shutdown crash unrelated to assertions.
Additional evidence: running individual files sometimes exits `-1073740940` even when tests pass.

## Grep checks (per brief)
- `plotter_ui(plotter)` count in `fansim/cockpit/app.py`: **1**
- `_place_library` in `fansim/cockpit/app.py`: **0**
- `Library (all recipes)` in `fansim/cockpit/app.py`: **0**
- `original envelope` in `fansim/cockpit/app.py`: **0**

## Notes / concerns
- `catalog/catalog.db` left modified but **not committed** (per instruction).
