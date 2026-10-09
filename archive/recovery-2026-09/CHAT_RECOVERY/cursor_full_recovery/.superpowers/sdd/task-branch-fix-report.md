# hub-first-cockpit: whole-branch fix report

Branch: `hub-first-cockpit`

## Changes by finding

### C1/C2 — `nominal_fits_spec` matches built geometry (tip + depth)
- Updated `fansim/cockpit/placement.py`:
  - Added `measure_flat(flat) -> (built_tip_dia, built_depth, hub_radius) | None` using `blade_from_flat(..., Features())`, `blade_max_dia`, `blade_z_extent`.
  - Updated `nominal_fits_spec(flat, spec, measured=None)` to:
    - Use `measured or measure_flat(flat)` and return `False` on failure.
    - Enforce hub mount minimum (`mount_min_hub_radius`) when defined.
    - Enforce `spec.hub_dia_mm` range.
    - Enforce `tip_dia <= spec.tip_dia_mm[1]` AND `depth <= spec.depth_mm[1]`.
- Updated `fansim/catalog.py`:
  - `classify_entry` measures once via `measure_flat(p)` and passes `measured=` into each spec check.
- Tests:
  - `tests/test_placement.py`: ensured a `fit_envelope(...).fit_status == "fits"` result implies `nominal_fits_spec(...)` is true.
  - `tests/test_placement.py`: added an over-depth case that passes the old tip-radius proxy but exceeds built depth and is rejected.
  - `tests/test_catalog.py`: added a deep blade that does not classify onto `a12x25`.

### I3 — do not promote `over_spec` to `fits`
- Updated `fansim/catalog.py`:
  - For placed designs, only promote to `"fits"` when `placed_on` is in the computed `fitted` list.
- Tests:
  - `tests/test_catalog.py`: added `placed_on=a12x25`, `fit_status=over_spec`, non-fitting params ⇒ remains `over_spec` after `classify_entry`.

### I4 — `fansim.catalog` must not import optuna via cockpit `__init__`
- Updated `fansim/cockpit/__init__.py` to be import-light (TYPE_CHECKING-only import of `Design/load_designs`).
- Tests:
  - `tests/test_catalog.py`: added a smoke test asserting importing `fansim.catalog` does not load `optuna`, and that importing `fansim.cockpit.placement` does not import `fansim.cockpit.data`.

### I5 — Library list click must set `library_sel`
- Updated `fansim/cockpit/app.py`:
  - Added `select_library_design(...)` to set `state.library_sel` then call `load_catalog_design`.
  - Wired `select_library_design` into both the `VSelect` `update_modelValue` and the `VListItem` click handler.

### I7 — restore dropped validation TODOs
- Updated `docs/known-issues.md`:
  - Restored the two validation TODO bullets (P–Q/shutoff + hub bore cap; grid convergence).

### M11 / M12 — lint
- Updated `fansim/cockpit/placement.py`: removed unused `rf` in `fit_envelope`.
- Updated `tests/test_labels.py`: removed unused `Path` import.

## Commands run (and output)

### Tests
```text
uv run python -m pytest tests/test_placement.py tests/test_catalog.py tests/test_cockpit_view.py tests/test_labels.py -q -m "not docker and not slow" --tb=short
............................                                             [100%]
28 passed in 7.03s
```
Note: Windows teardown exit code can be non-zero (observed `-1073740940`), but assertions all passed.

### Optuna import smoke check
```text
uv run python -c "import fansim.catalog; import sys; print('optuna' in sys.modules)"
False
```

## Commits
- `1b478ab` Classify hub fit from built tip and depth, not a tip-radius proxy.
- `6bee6de` Restore P-Q and grid-convergence TODOs in known-issues.
