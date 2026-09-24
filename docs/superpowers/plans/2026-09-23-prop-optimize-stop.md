# Prop Optimize stop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Stop button that ends a prop Optimize study after the trial already running and keeps the Pareto rows written so far.

**Architecture:** `run_prop_study` takes an optional `threading.Event`. A callback calls `study.stop()` once that event is set. The cockpit holds one event for the live study, sets it from Stop, and reloads the saved front the same way a finished study does.

**Tech Stack:** Python 3.12, Optuna, Trame Vuetify buttons, pytest, PowerShell here-strings for commits.

## Global Constraints

- `run_prop_study(..., stop_event: threading.Event | None = None)` returns `(study, pareto)` and still calls `save_prop_pareto` when `out_dir` is set.
- Stop is enabled only while the prop Optimize study is running (`prop_opt_running`). Analyze and CFD refine do not enable it.
- The click sets the event. It does not kill the process.
- After a stop, `prop_msg` names the finished trial count and the run directory, `prop_busy` clears, and the figure reloads from the saved front.
- A test sets the event before `run_prop_study(..., n_trials=20)` and asserts fewer than 20 trials. No Trame process.
- Do not move `study.db`, add randomize, stop CFD refine, or check the §14.8 checkbox.
- On Windows, pytest may exit `-1073741819`, `-1073740940`, or `3221226356` after a printed pass line. Treat the pass line as success.
- PowerShell: do not chain commands with `&&`.
- Commit only the files a task lists. Do not stage `.superpowers/sdd/progress.md`, `catalog/catalog.db`, or `runs/`.

---

## File map

| File | Responsibility |
|---|---|
| `fansim/propeller/optimize.py` | `stop_event` argument and the Optuna callback |
| `tests/test_prop_optimize.py` | Early-stop test, no UI |
| `fansim/cockpit/prop_tab.py` | Stop button, event, message, and figure reload |

---

### Task 1: Stop the study from an event

**Files:**
- Modify: `fansim/propeller/optimize.py` (`run_prop_study` and its `study.optimize` call)
- Test: `tests/test_prop_optimize.py`

**Interfaces:**
- Consumes: existing `run_prop_study(spec, n_trials=..., seed=..., out_dir=..., ...) -> (study, pareto)`.
- Produces: keyword `stop_event: threading.Event | None = None`. When the event is set, `study.stop()` runs from an Optuna callback after the current trial. `out_dir` still saves the Pareto front.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_prop_optimize.py`:

```python
import threading

from fansim.prop_spec import get_prop_spec
from fansim.propeller.optimize import run_prop_study


def test_stop_event_ends_the_study_early():
    spec = get_prop_spec("fpv_5inch")
    event = threading.Event()
    event.set()
    study, _pareto = run_prop_study(spec, n_trials=20, seed=0, stop_event=event)
    assert len(study.trials) < 20
```

If `threading` or `get_prop_spec` is already imported in that file, do not import it twice.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_optimize.py::test_stop_event_ends_the_study_early -q --tb=line`

Expected: FAIL. `run_prop_study` does not accept `stop_event` (`TypeError`).

- [ ] **Step 3: Honor the event**

Add `import threading` to `fansim/propeller/optimize.py`.

Add the keyword to `run_prop_study`, after `min_hover_minutes`:

```python
                   stop_event: threading.Event | None = None):
```

Replace `study.optimize(objective, n_trials=n_trials)` with:

```python
    def _stop_after_trial(study, trial):
        if stop_event is not None and stop_event.is_set():
            study.stop()

    study.optimize(objective, n_trials=n_trials, callbacks=[_stop_after_trial])
```

Leave the `save_prop_pareto` call that already follows `study.optimize` where it is.

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run python -m pytest tests/test_prop_optimize.py::test_stop_event_ends_the_study_early -q --tb=line`

Expected: PASS, with fewer than 20 trials.

- [ ] **Step 5: Commit**

```powershell
git add -- fansim/propeller/optimize.py tests/test_prop_optimize.py
git commit -m @"
feat(prop): stop a prop study from an event

"@
```

---

### Task 2: Stop button on the Optimize card

**Files:**
- Modify: `fansim/cockpit/prop_tab.py` (`setup_prop_tab` state, `optimize_prop`, the Optimize button row)

**Interfaces:**
- Consumes: `run_prop_study(..., stop_event=event)` from Task 1.
- Produces: state field `prop_opt_running` and `ctx.stop_prop_optimize`.

This task does not start Trame and does not add a test. The stop behavior is covered by Task 1.

- [ ] **Step 1: Add the running flag and the shared event**

Next to `state.prop_busy = False` inside `setup_prop_tab`:

```python
    state.prop_opt_running = False
```

Inside `setup_prop_tab`, before `def optimize_prop`, create one event the button and the worker share:

```python
    import threading
    opt_stop = threading.Event()

    def stop_prop_optimize():
        if not state.prop_opt_running:
            return
        opt_stop.set()
        state.prop_msg = "⏹ Stopping after the current trial…"
        state.flush()
```

If `threading` is already imported at module level, use that import and do not import it again inside the function.

Assign it beside the existing `ctx.optimize_prop = optimize_prop` line:

```python
    ctx.stop_prop_optimize = stop_prop_optimize
```

- [ ] **Step 2: Pass the event and report a stop**

At the start of `optimize_prop`, after the mission-kwargs early return and before `async def task`:

```python
        opt_stop.clear()
        state.prop_opt_running = True
```

Change the executor call to:

```python
                study, pareto = await loop.run_in_executor(
                    None,
                    lambda: run_prop_study(
                        base,
                        n_trials=trials,
                        max_power_w=cap,
                        out_dir=out_dir,
                        prop_model=str(state.prop_model),
                        stop_event=opt_stop,
                        **mission_call["kwargs"],
                    ),
                )
```

In the `except` branch, set `state.prop_opt_running = False` next to `state.prop_busy = False`.

After the existing reload (`_reload_prop_from_disk`, the pareto merge, and `_refresh_prop_figure`), replace the success `prop_msg` assignment with:

```python
            if opt_stop.is_set():
                state.prop_msg = (
                    f"⏹ Stopped after {len(study.trials)} trials "
                    f"({mode} → {out_dir.name})."
                )
            else:
                cap_txt = f" ≤{cap:.0f} W" if cap else ""
                state.prop_msg = (
                    f"✓ {len(pareto)} designs on the thrust↔efficiency front{cap_txt} "
                    f"({mode} → {out_dir.name}). Click a point (or row) to load it."
                )
            state.prop_busy = False
            state.prop_opt_running = False
```

Keep a single pair of `state.prop_busy = False` and `ticker.cancel()` on that success path. Do not leave a second copy below the new branch.

- [ ] **Step 3: Add the button**

Immediately after the Optimize `VBtn`, still inside that `VRow`:

```python
                        v3.VBtn(
                            "Stop",
                            color="error",
                            size="small",
                            click=(getattr(ctx, "stop_prop_optimize"),),
                            disabled=("!prop_opt_running",),
                            classes="ml-2",
                        )
```

- [ ] **Step 4: Commit**

```powershell
git add -- fansim/cockpit/prop_tab.py
git commit -m @"
feat(prop): stop prop Optimize after the current trial

"@
```

---
