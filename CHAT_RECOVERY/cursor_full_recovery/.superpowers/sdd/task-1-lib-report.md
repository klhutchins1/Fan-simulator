# Task 1 Report: Library row formatter

## Status

**Complete.** TDD RED → GREEN, committed on `library-browse-preview`.

## TDD Evidence

### RED (Step 2)

```
uv run python -m pytest tests/test_library_view.py -v --tb=short
```

```
ERROR tests/test_library_view.py
ModuleNotFoundError: No module named 'fansim.cockpit.library_view'
```

Exit code: 2 (collection error, 0 tests run).

### GREEN (Step 4)

After implementing `fansim/cockpit/library_view.py` and adjusting the copy-test clickable assert:

```
tests/test_library_view.py::test_missing_params_is_no_geometry PASSED
tests/test_library_view.py::test_row_copy_uses_original_size_not_envelope_jargon PASSED
tests/test_library_view.py::test_oversized_is_not_titled_as_fits_a12x25 PASSED

3 passed in 3.25s
```

Process exit code: `-1073741819` (CadQuery teardown on Windows). All assertions green per brief guidance.

## Commit

- **SHA:** `2d34c4ff7f3479dd4e8d4550978ad1ffe1dfcbcd`
- **Subject:** Describe library recipes in blades, size, and original CFM.

## Files

| File | Action |
|------|--------|
| `fansim/cockpit/library_view.py` | Created — `fit_hint`, `library_list_items`, hint constants |
| `tests/test_library_view.py` | Created — 3 unit tests |

Not modified: `fansim/cockpit/app.py` (Task 3), `catalog/catalog.db`, `.superpowers/` (except this report).

## Tests

1. **`test_missing_params_is_no_geometry`** — entry with only `n_blades` returns `"no geometry yet"`.
2. **`test_row_copy_uses_original_size_not_envelope_jargon`** — group title from `run_label`, row title with blade count and hub/tip diameters (2× radius), subtitle with CFM at original size, no "original envelope" jargon.
3. **`test_oversized_is_not_titled_as_fits_a12x25`** — full blade params that exceed a12x25 frame never get `"fits this hub"` (CadQuery path via `nominal_fits_spec`).

## Self-review

- Implementation matches the task brief verbatim for `library_view.py`.
- Hub/tip displayed as diameters: `round(2 * radius)` → `33 mm` / `118 mm` for radii 16.5 / 59.0.
- Group dict shape: `{"role": "group", "title", "caption"}`.
- Row dict shape: `{"role": "row", "value", "title", "subtitle", "clickable"}`.
- `clickable` is `False` only when hint is `HINT_NONE`.

## Concerns

1. **Failed measure → `"too big"` not `"no geometry yet"`.** When `hub_radius`/`tip_radius` are present but `measure_flat` returns `None` (incomplete blade params), `nominal_fits_spec` returns `False` and `fit_hint` returns `HINT_BIG` with `clickable=True`. The brief anticipated an `Exception` path to `HINT_NONE`; actual behavior differs. Copy test uses the brief's flexible `clickable is False or "too big" in subtitle or "fits this hub" in subtitle` assert instead of strict `clickable is False`.
2. **CadQuery teardown exit code** on Windows is non-zero after tests pass; CI should judge by pytest assertions, not process exit code.
3. **Task 3 integration** will wire `library_list_items` into `app.py` and retire `library_items_from_catalog`.

## Fix: unmeasurable recipes → no geometry yet

**Change:** `fit_hint` now calls `measure_flat(p)` before `nominal_fits_spec`. When measurement returns `None` (hub/tip present but incomplete blade params), returns `HINT_NONE` instead of `HINT_BIG`. Copy test asserts `"no geometry yet"` and `clickable is False`.

**Command:**
```
uv run python -m pytest tests/test_library_view.py -v --tb=short
```

**Output:**
```
tests/test_library_view.py::test_missing_params_is_no_geometry PASSED
tests/test_library_view.py::test_row_copy_uses_original_size_not_envelope_jargon PASSED
tests/test_library_view.py::test_oversized_is_not_titled_as_fits_a12x25 PASSED

3 passed in 3.10s
```

**Commit:** `a1d8445` — Treat unmeasurable library recipes as no geometry yet.
