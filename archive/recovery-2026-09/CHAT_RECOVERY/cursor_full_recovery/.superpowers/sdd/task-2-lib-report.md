# Task 2 Report: Editor-only Fit/Scale apply helper

## Status

**Complete.** TDD RED → GREEN, committed on `library-browse-preview`.

## TDD Evidence

### RED (Step 2)

```
uv run python -m pytest tests/test_library_view.py::test_apply_fit_does_not_mutate_parent_or_invent_a_trial -v
```

```
ImportError: cannot import name 'apply_library_recipe' from 'fansim.cockpit.library_view'
```

Exit code: 2 (collection error, 0 tests run).

### GREEN (Step 4)

```
uv run python -m pytest tests/test_library_view.py -v --tb=short
```

```
tests/test_library_view.py::test_missing_params_is_no_geometry PASSED
tests/test_library_view.py::test_row_copy_uses_original_size_not_envelope_jargon PASSED
tests/test_library_view.py::test_oversized_is_not_titled_as_fits_a12x25 PASSED
tests/test_library_view.py::test_apply_fit_does_not_mutate_parent_or_invent_a_trial PASSED
tests/test_library_view.py::test_apply_refuses_empty_params PASSED
tests/test_library_view.py::test_apply_scale_unplaced_on_zero_tip PASSED

6 passed in 3.04s
```

## Commit

- **SHA:** `03f2fde`
- **Subject:** Apply library Fit and Scale in the editor without creating a row.

## Deliverables

- `LibraryApply` frozen dataclass (`ok`, `message`, `flat`, `parent_id`, `place_op`, `fit_status`, `leftover`) — no `trial` / `design_id` fields.
- `apply_library_recipe(flat, spec, op, parent_id)` delegates to `fit_envelope` / `scale_to_hub`; never mutates input `flat`.
- Refuses missing hub/tip with exact message: `This recipe has no blade numbers to Fit.`
- Scale with `fit_status == "unplaced"` returns `ok=False`, `flat=None`.

## Files Changed

- `fansim/cockpit/library_view.py` — added `LibraryApply`, `apply_library_recipe`, `NO_PARAMS_MSG`
- `tests/test_library_view.py` — 3 new apply tests (Task 1 tests unchanged)
