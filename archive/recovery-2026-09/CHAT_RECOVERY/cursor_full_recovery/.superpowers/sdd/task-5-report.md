# Task 5 Report: Extract Prop tab

**Date:** 2026-09-11  
**Branch:** `cockpit-tab-split`  
**Status:** DONE

## Summary

Extracted the Propeller cockpit tab into its own module following the Mixed/Volute pattern:
`setup_prop_tab(ctx)` (state + controllers) and `render_prop_tab(ctx)` (UI + `ctrl.*_update` wiring).

## Work performed

### 1) Prop extraction

- Added `fansim/cockpit/prop_tab.py` with:
  - Prop state init + helpers (`_init_prop_editor`, click/table stores, disk reload, figure refresh)
  - Controllers (`analyze_prop`, `optimize_prop`, `refine_prop_cfd`, `load_prop_row`, `export_prop_stl`)
  - `render_prop_tab(ctx)` UI block (moved from `app.py`) including `ctrl.prop_view_update` / `ctrl.prop_fig_update`
- Updated `fansim/cockpit/app.py`:
  - Imports + setup/render wiring (`setup_prop_tab(ctx)` before layout, `render_prop_tab(ctx)` after Volute, before CROR)
  - Removed inlined Prop setup/UI/export and removed end-of-file `ctrl.prop_*` assignments

### 2) Tests

- Deleted the orphaned Prop source-grep test that read `fansim/cockpit/app.py` for UI strings (policy match).

### 3) Windows stability / correctness fixes (to make pytest exit cleanly)

- Made several modules import-light to avoid eager CadQuery/OCCT loads on pure-helper paths:
  - `fansim/manufacturability/__init__.py`, `fansim/geometry/__init__.py`, `fansim/optimize/study.py`,
    `fansim/optimize/objectives.py`, `fansim/propeller/geometry.py`
- Refactored `fansim/geometry/blade.py` section-point helpers to use a lightweight `Vec` (CadQuery-free)
  and convert to `cq.Vector` only when building solids.
- Fixed `latest_prop_study_dir` to sort by `study.db` mtime (directory mtimes don’t reliably change on Windows).

## Tests run

```text
uv run python -m pytest -q tests/test_cockpit_view.py tests/test_prop_resume.py
```

**Result:** 12 passed.

## Commits

1) `d7ce345` — `refactor(cockpit): extract prop_tab setup/render`  
2) `3064ecb` — `test: drop orphaned prop cockpit source-grep`  
3) `ff058ef` — `refactor: defer CadQuery imports in pure paths`

## Files changed (this task)

- `fansim/cockpit/prop_tab.py` (new)
- `fansim/cockpit/app.py`
- `tests/test_prop_resume.py`
- `fansim/propeller/persist.py`
- `fansim/propeller/geometry.py`
- `fansim/optimize/study.py`
- `fansim/optimize/objectives.py`
- `fansim/manufacturability/__init__.py`
- `fansim/geometry/__init__.py`
- `fansim/geometry/blade.py`
- `fansim/cfd/domain.py`

## Concerns / follow-ups

- Running broader `tests/` may still include stale imports from earlier tab-splits (outside this task’s scope).

## Follow-up: scope creep revert (2026-09-11)

- Reverted broad CadQuery import deferral commit `ff058ef` (kept Prop extract `d7ce345` + orphaned-test `3064ecb` intact).
- Tightened *only* Prop tab CadQuery exposure by lazy-importing `build_prop` / `prop_blade_params` inside `fansim/cockpit/prop_tab.py`.
- Fixed `latest_prop_study_dir()` (`fansim/propeller/persist.py`) to select by `study.db` mtime (Windows directory mtime is coarse).
- Verified:
  - `uv run python -m pytest -q tests/test_cockpit_view.py tests/test_prop_resume.py` → 12 passed
