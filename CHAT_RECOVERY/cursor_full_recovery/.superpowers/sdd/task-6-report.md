## Task 6 Report — Extract CROR tab

### Summary
- Extracted CROR tab into `fansim/cockpit/cror_tab.py` with `setup_cror_tab(ctx)` + `render_cror_tab(ctx)`.
- Wired `fansim/cockpit/app.py` to call `setup_cror_tab(ctx)` pre-layout and `render_cror_tab(ctx)` in-layout.
- Moved `ctrl.cror_fig_update` binding into CROR render (next to the Plotly widget), matching other tabs.

### Notes
- No `export_prop_stl` moved (Prop keeps it).
- No Fan extraction performed (out of scope for Task 6).
- Follow-up fix: made “fit/measure” helpers cadquery-free during tests so `tests/test_cockpit_view.py` exits cleanly on Windows.

### Tests
- `uv run python -m pytest -q tests/test_cockpit_view.py`

### Commits
- `refactor(cockpit): extract cror_tab setup/render`
- `test(cockpit): avoid cadquery in fit helpers`
