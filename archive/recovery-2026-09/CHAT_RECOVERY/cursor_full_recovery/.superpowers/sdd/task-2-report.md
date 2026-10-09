# Task 2 Report: CockpitCtx + busy_ui factories

## Status

**DONE**

## Summary

Extracted shared cockpit session context and busy-UI factories from nested helpers in `build_server`, per the cockpit tab-split plan (Approach B, Task 2).

## Changes

### New: `fansim/cockpit/context.py`

- `CockpitCtx` dataclass holding `server`, `state`, `ctrl`, `run_dir`, `runs_root`, four plotters, and busy UI callables (`busy_bar`, `busy_expr`, `spawn_busy_ticker`).

### New: `fansim/cockpit/busy_ui.py`

- `make_busy_expr()` — OR-joins Trame flag expressions.
- `make_busy_bar(v3, busy_expr)` — indeterminate progress bar widget factory.
- `make_spawn_busy_ticker(state, asynchronous)` — elapsed-caption ticker factory (uses `busy_caption` from `busy.py`).

### Modified: `fansim/cockpit/app.py`

- Imported factories and `CockpitCtx`.
- After plotter creation in `build_server`, wired factories and built `ctx`.
- Removed nested `_busy_expr`, `_busy_bar`, `_spawn_busy_ticker` definitions (~43 lines).
- Replaced 6 `_busy_bar(` and 20 `_spawn_busy_ticker(` callsites with module-level names.
- `ctx` is constructed but not yet passed to tabs (expected until Tasks 3–7).

## Verification

```bash
uv run python -c "from fansim.cockpit.context import CockpitCtx; from fansim.cockpit.busy_ui import make_busy_expr; print(make_busy_expr()('a','b'))"
# Output: a || b

uv run python -m pytest -q tests/test_cockpit_view.py
# 9 passed in ~4s
```

Note: pytest exit code `-1073741819` on Windows (known VTK/proactor shutdown crash); all 9 tests passed before exit.

## Commit

- `86fff61` — `refactor(cockpit): add CockpitCtx and busy_ui factories`

## Concerns

1. **Replace-all hazard**: Initial bulk replace of `_spawn_busy_ticker(` / `_busy_bar(` also mangled `make_spawn_busy_ticker(` → `makespawn_busy_ticker(` and `make_busy_bar(` → `makebusy_bar(` in the factory wiring lines. Fixed before commit; tests re-run green.
2. **`ctx` unused**: Intentional — tabs consume it in later tasks.
3. **Windows pytest exit code**: Pre-existing interpreter crash at shutdown; test results are valid.

## Out of scope (not done)

- Tab module extraction (Tasks 3–7).
- Source-grep UI tests.
- Behavior changes.
