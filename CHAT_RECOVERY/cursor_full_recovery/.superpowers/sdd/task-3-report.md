# Task 3 Report: Extract Mixed tab

## Status

DONE

## Implementation

- Extracted Mixed-flow tab into `fansim/cockpit/mixed_tab.py`:
  - `setup_mixed_tab(ctx)` owns all `mf_*` state + Mixed controllers/callbacks (Preview/Export/Assess/Optimize/CFD refine) and `load_mf_trial`.
  - `render_mixed_tab(ctx)` owns Mixed UI and binds `ctrl.mf_view_update` / `ctrl.mf_fig_update` at widget creation time.
- Updated `fansim/cockpit/app.py` to:
  - call `setup_mixed_tab(ctx)` (no Prop extraction),
  - replace the Mixed UI block with `render_mixed_tab(ctx)`,
  - remove end-of-file `ctrl.mf_*` bindings (now handled inside the Mixed tab renderer).
- Mixed busy helpers now use `ctx.spawn_busy_ticker` and `ctx.busy_bar`; Mixed preview uses `ctx.mf_plotter`; Mixed runs use `ctx.runs_root`, `ctx.state`, `ctx.ctrl`.

## Verification

- `uv run python -m pytest -q tests/test_cockpit_view.py` → `9 passed`
- `uv run python -m pytest -q tests/test_placement.py -m "not docker"` → `24 passed`

## Commit

- `7087ce0 refactor(cockpit): extract mixed_tab setup/render`

## Concerns

- `setup_mixed_tab` attaches per-session Mixed stores/callbacks onto `ctx` dynamically (works today; may be formalized when more tabs are extracted).
