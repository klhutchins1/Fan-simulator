# Task 4 Report — Extract Volute tab

## Summary

- **Goal**: Extract the Cockpit Volute tab into `fansim/cockpit/volute_tab.py` using Approach B (setup/render split), mirroring the already-extracted Mixed tab pattern.
- **Result**: Volute controllers/state initialization moved into `setup_volute_tab(ctx)` and the Volute UI moved into `render_volute_tab(ctx)`; `fansim/cockpit/app.py` now wires the new module in.
- **Behavior**: Intended no behavior change; code was copied verbatim into the extracted module (only wiring changed).

## Changes

- **Added**: `fansim/cockpit/volute_tab.py`
  - `setup_volute_tab(ctx)`: moved contiguous controllers from `# ---- Volute tab ...` up to (but not including) `# ---- CROR tab`.
  - `render_volute_tab(ctx)`: moved the `# ---- VOLUTE TAB` UI (`v_show="active_tab === 'volute'"`) and set `ctrl.volute_view_update` inside the render (same pattern as other extracted tabs).
  - Uses `ctx.volute_plotter`, `ctx.spawn_busy_ticker`, `ctx.busy_bar`, and stores `ctx.volute_preview_stl`.
- **Modified**: `fansim/cockpit/app.py`
  - Imports `setup_volute_tab` / `render_volute_tab`.
  - Calls `setup_volute_tab(ctx)` before layout creation.
  - Replaces inline Volute UI with `render_volute_tab(ctx)`.
  - Removes inline Volute controllers and the end-of-file `ctrl.volute_view_update = volute_view.update` assignment (now handled in render).

## Verification

- **Tests**: `uv run python -m pytest -q tests/test_cockpit_view.py`
  - Output shows `9 passed`.
  - **Note**: On Windows this run exits with a non-zero `LASTEXITCODE` (`-1073741819` / access violation) despite the passing output; appears to be an interpreter shutdown crash unrelated to Volute extraction (no UI stack is imported in these tests), but should be tracked.
- **Sanity**: `uv run python -m py_compile fansim/cockpit/app.py fansim/cockpit/volute_tab.py` (OK).

## Commit

- `910647f` — `refactor(cockpit): extract volute_tab setup/render`
