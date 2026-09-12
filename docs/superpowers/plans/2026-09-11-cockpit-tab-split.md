# Cockpit Tab Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `fansim/cockpit/app.py` into a thin shell plus one module per top tab, extract shared figures/busy helpers, and remove source-grep UI tests.

**Architecture:** Approach B from `docs/superpowers/specs/2026-09-11-cockpit-tab-split-design.md`. Each tab exports `setup_*_tab(ctx)` (state + controllers, called before `SinglePageLayout`) and `render_*_tab(ctx)` (UI, called inside layout under existing `v_show="active_tab === …"` Div/Row). Shared Plotly/filter helpers move to `figures.py`; Trame busy chrome to `busy_ui.py`; `CockpitCtx` in `context.py`.

**Tech Stack:** Python 3.12, Trame/Vuetify3, PyVista, Plotly, pytest via `uv run python -m pytest`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-11-cockpit-tab-split-design.md`
- Roadmap item: §9.4 only (do not implement §9.5 archetype registry).
- **No behavior change** — same state keys, controller names, tab order, Assess/Optimize flows.
- Top-tab order locked: Fan → Mixed → Volute → Prop → CROR. Prop tab **value** is `"propeller"` (not `"prop"`).
- **Do not add** source-grep UI tests (`read_text` / `assert "label" in src`).
- **Do not commit** unless the user explicitly asks; leave the working tree dirty between tasks.
- Prefer `uv run python -m pytest …`. Windows OCCT teardown exit codes may be noisy; trust assertion outcomes.
- Tabs must not import `fansim.cockpit.app`. `app.py` imports tabs.

## Settled design choices (from spec §10)

1. **Two-phase API** (not single `register_*`): layout today uses `v_show` Divs/Rows (not `VWindowItem`). Controllers are defined **before** `with SinglePageLayout`. Therefore each tab module exports:
   - `setup_<tab>_tab(ctx: CockpitCtx) -> None`
   - `render_<tab>_tab(ctx: CockpitCtx) -> None` (must run inside open layout content)
2. **No `widgets.py`** unless a second tab needs `_slider` / `_help_switch`; keep those Fan-local in `fan_tab.py` / `fan_helpers.py`.
3. **Public rename:** `_reject_hint` → `reject_hint` in `figures.py` (tests import the public name).

## File map

| File | Role |
|------|------|
| `fansim/cockpit/context.py` | `CockpitCtx` dataclass |
| `fansim/cockpit/figures.py` | Plotly builders + `filter_fitting_designs` + `reject_hint` + `_has_real_cfm` |
| `fansim/cockpit/busy_ui.py` | Factories for busy_expr / busy_bar / spawn_busy_ticker |
| `fansim/cockpit/fan_helpers.py` | Fan-only pure helpers (blade extent, assessed load, depth drivers) |
| `fansim/cockpit/fan_tab.py` | Fan setup + render |
| `fansim/cockpit/mixed_tab.py` | Mixed setup + render |
| `fansim/cockpit/volute_tab.py` | Volute setup + render |
| `fansim/cockpit/prop_tab.py` | Prop setup + render |
| `fansim/cockpit/cror_tab.py` | CROR setup + render |
| `fansim/cockpit/app.py` | Thin shell: bootstrap, plotters, ctx, setup*, layout chrome, render* |
| `tests/test_cockpit_view.py` | Behavioral tests only; delete source-grep block |
| `docs/roadmap.md` | Mark §9.4 done when finished |

### Current `app.py` line anchors (approximate — re-find markers after each edit)

| Chunk | Lines (approx) | Destination |
|-------|----------------|-------------|
| Module scatter/filter/reject | ~365–590 | `figures.py` |
| Blade/assess helpers | ~592–705 | `fan_helpers.py` |
| `_busy_*` inside `build_server` | ~746–787 | `busy_ui.py` factories |
| Fan controllers (majority) | ~789–2954 | `fan_tab.setup_fan_tab` |
| Prop state banner | ~2955–3031 | `prop_tab` (setup start) |
| Mixed controllers | ~3032–3405 + `load_mf_trial` ~3708–3745 | `mixed_tab` |
| Prop controllers | ~3406–3707 + `export_prop_stl` ~4185–4225 | `prop_tab` |
| Volute controllers | ~3746–3930 | `volute_tab` |
| CROR controllers | ~3931–4184 | `cror_tab` |
| Layout tabs chrome | ~4232–4247 | stay in `app.py` |
| Fan UI | ~4248–4894 | `fan_tab.render_fan_tab` |
| Mixed UI | ~4895–4979 | `mixed_tab.render_mixed_tab` |
| Volute UI | ~4980–5033 | `volute_tab.render_volute_tab` |
| Prop UI | ~5034–5141 | `prop_tab.render_prop_tab` |
| CROR UI | ~5142–end widgets | `cror_tab.render_cror_tab` |

**Interleaving warning:** Mixed and Prop controller defs are interleaved today. When cutting, gather by name — do not cut one contiguous Mixed block and leave `prop_editor_*` behind in Mixed.

---

### Task 1: Extract `figures.py` + clean `test_cockpit_view.py`

**Files:**
- Create: `fansim/cockpit/figures.py`
- Modify: `fansim/cockpit/app.py` (remove moved defs; re-import for any remaining callers during transition)
- Modify: `tests/test_cockpit_view.py`

**Interfaces:**
- Produces:
  - `prop_scatter_figure(pareto, user_points=()) -> go.Figure`
  - `cror_scatter_figure(rows) -> go.Figure`
  - `mf_scatter_figure(designs) -> go.Figure`
  - `scatter_figure(study_designs, user_designs=(), stock_ref: dict | None = None) -> go.Figure`
  - `filter_fitting_designs(designs, spec) -> list`
  - `reject_hint(reason: str) -> str`  # was `_reject_hint`
  - `_has_real_cfm(d: Design) -> bool` (keep private if only Fan uses it; or move with Fan in Task 7 — if Fan-only, skip moving it here and leave for `fan_helpers`)
- Consumes: `plotly.graph_objects`, `fansim.cockpit.data.Design`, `fansim.cockpit.placement.nominal_fits_spec`

- [ ] **Step 1: Confirm `_has_real_cfm` call sites**

Run: `rg "_has_real_cfm" fansim/cockpit tests`

If only Fan Assess/select uses it → leave in `app.py` for Task 7 (`fan_helpers`). Do not put Fan-only helpers in `figures.py`.

- [ ] **Step 2: Create `fansim/cockpit/figures.py`**

Move the bodies of `prop_scatter_figure`, `cror_scatter_figure`, `mf_scatter_figure`, `scatter_figure`, `filter_fitting_designs`, and `_reject_hint` (renamed `reject_hint`) unchanged except the rename. Module docstring:

```python
"""Plotly design-space figures and pure filter/hint helpers (no Trame/VTK)."""
```

Imports needed at top of `figures.py`:

```python
from __future__ import annotations

import plotly.graph_objects as go

from fansim.cockpit.placement import nominal_fits_spec
```

(`Design` only if `_has_real_cfm` moves here.)

- [ ] **Step 3: Update `app.py` to import from figures**

Delete the moved function bodies from `app.py`. Add:

```python
from fansim.cockpit.figures import (
    cror_scatter_figure,
    filter_fitting_designs,
    mf_scatter_figure,
    prop_scatter_figure,
    reject_hint,
    scatter_figure,
)
```

Replace every `_reject_hint(` call in `app.py` with `reject_hint(`.

- [ ] **Step 4: Rewrite imports + delete source-grep tests in `tests/test_cockpit_view.py`**

Change top imports to:

```python
from fansim.cockpit.figures import filter_fitting_designs, reject_hint, scatter_figure
```

Update tests that called `_reject_hint` to call `reject_hint`.

**Delete** these tests and `_read_cockpit_app_source` entirely:

- `test_library_card_shows_preview_msg`
- `test_non_library_entrypoints_clear_library_provenance`
- `test_apply_library_success_path_does_not_clear_provenance`
- `test_export_fit_envelope_switch_in_cockpit`
- `test_assess_hose_picker_in_cockpit`
- `test_assess_refine_op_switch_in_cockpit`
- `test_assess_wall_ks_switch_in_cockpit`
- `test_assess_cancel_in_cockpit`
- `test_fan_optimize_card_in_cockpit`
- `test_prop_and_mixed_optimize_resume_in_cockpit`
- `test_cror_tab_in_cockpit`
- `test_volute_tab_in_cockpit`
- `test_cockpit_ui_cohesion_approach1`
- `test_busy_helpers_and_indeterminate_bars_are_shared`

Add a short module docstring note:

```python
"""Cockpit unit tests for pure helpers (figures, busy captions, library list).

Do not add source-grep UI tests that assert label strings exist in app.py / tab modules.
"""
```

Keep: `test_reject_hint_*`, `test_filter_fitting_designs_*`, `test_results_for_hub_*`, `test_scatter_*`, `test_format_elapsed_*`, `test_busy_caption_*`.

- [ ] **Step 5: Run tests**

Run: `uv run python -m pytest -q tests/test_cockpit_view.py`

Expected: all remaining tests PASS.

---

### Task 2: `CockpitCtx` + `busy_ui` factories

**Files:**
- Create: `fansim/cockpit/context.py`
- Create: `fansim/cockpit/busy_ui.py`
- Modify: `fansim/cockpit/app.py` (use factories; build `CockpitCtx`)

**Interfaces:**
- Produces `CockpitCtx` fields: `server`, `state`, `ctrl`, `run_dir`, `runs_root`, `plotter`, `prop_plotter`, `mf_plotter`, `volute_plotter`, `busy_bar`, `busy_expr`, `spawn_busy_ticker`
- Produces:
  - `make_busy_expr() -> Callable[..., str]`
  - `make_busy_bar(v3) -> Callable[..., None]`
  - `make_spawn_busy_ticker(state, asynchronous) -> Callable[..., tuple]`

- [ ] **Step 1: Create `fansim/cockpit/context.py`**

```python
"""Shared cockpit session handle passed into tab setup/render."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class CockpitCtx:
    server: Any
    state: Any
    ctrl: Any
    run_dir: Path
    runs_root: Path
    plotter: Any
    prop_plotter: Any
    mf_plotter: Any
    volute_plotter: Any
    busy_bar: Callable[..., None]
    busy_expr: Callable[..., str]
    spawn_busy_ticker: Callable[..., tuple]
```

- [ ] **Step 2: Create `fansim/cockpit/busy_ui.py`**

Move the logic of `_busy_expr`, `_busy_bar`, `_spawn_busy_ticker` from `build_server` into factories so they close over Trame modules only when the UI stack is loaded:

```python
"""Trame busy chrome helpers (progress bar + elapsed ticker)."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from fansim.cockpit.busy import busy_caption


def make_busy_expr() -> Callable[..., str]:
    def busy_expr(*flags: str) -> str:
        return " || ".join(flags)
    return busy_expr


def make_busy_bar(v3: Any, busy_expr: Callable[..., str]) -> Callable[..., None]:
    def busy_bar(*flags: str, color: str = "primary") -> None:
        v3.VProgressLinear(
            indeterminate=True,
            height=6,
            color=color,
            rounded=True,
            classes="mt-2 mb-1",
            v_if=busy_expr(*flags),
        )
    return busy_bar


def make_spawn_busy_ticker(state: Any, asynchronous: Any) -> Callable[..., tuple]:
    def spawn_busy_ticker(
        *,
        action: str,
        msg_attr: str,
        busy_attr: str,
        note: str = "",
        hint_fn=None,
        interval: float = 1.0,
        skip_when=None,
    ):
        t0 = time.time()

        async def _tick():
            while bool(getattr(state, busy_attr)):
                if skip_when is not None and skip_when():
                    await asyncio.sleep(interval)
                    continue
                hint = hint_fn() if hint_fn else ""
                setattr(
                    state,
                    msg_attr,
                    busy_caption(action, time.time() - t0, hint=hint, note=note),
                )
                state.flush()
                await asyncio.sleep(interval)

        return asynchronous.create_task(_tick()), t0

    return spawn_busy_ticker
```

- [ ] **Step 3: Wire factories in `build_server`**

After `state, ctrl = server.state, server.controller` and plotter creation:

```python
from fansim.cockpit.busy_ui import make_busy_bar, make_busy_expr, make_spawn_busy_ticker
from fansim.cockpit.context import CockpitCtx

busy_expr = make_busy_expr()
busy_bar = make_busy_bar(v3, busy_expr)
spawn_busy_ticker = make_spawn_busy_ticker(state, asynchronous)

ctx = CockpitCtx(
    server=server,
    state=state,
    ctrl=ctrl,
    run_dir=run_dir,
    runs_root=runs_root,
    plotter=plotter,
    prop_plotter=prop_plotter,
    mf_plotter=mf_plotter,
    volute_plotter=volute_plotter,
    busy_bar=busy_bar,
    busy_expr=busy_expr,
    spawn_busy_ticker=spawn_busy_ticker,
)
```

Delete nested `_busy_expr` / `_busy_bar` / `_spawn_busy_ticker` defs. Replace callsites `_busy_bar(` → `busy_bar(`, `_spawn_busy_ticker(` → `spawn_busy_ticker(`, `_busy_expr(` → `busy_expr(` (if any).

Keep `ctx` in `build_server` even before tabs exist — later tasks use it.

- [ ] **Step 4: Smoke import + cockpit tests**

Run:

```bash
uv run python -c "from fansim.cockpit.context import CockpitCtx; from fansim.cockpit.busy_ui import make_busy_expr; print(make_busy_expr()('a','b'))"
uv run python -m pytest -q tests/test_cockpit_view.py
```

Expected: prints `a || b`; tests PASS.

---

### Task 3: Extract Mixed tab

**Files:**
- Create: `fansim/cockpit/mixed_tab.py`
- Modify: `fansim/cockpit/app.py`

**Interfaces:**
- Produces: `setup_mixed_tab(ctx: CockpitCtx) -> None`, `render_mixed_tab(ctx: CockpitCtx) -> None`
- Consumes: `ctx.state`, `ctx.ctrl`, `ctx.mf_plotter`, `ctx.runs_root`, `ctx.busy_bar`, `ctx.spawn_busy_ticker`, `mf_scatter_figure` from `figures`

- [ ] **Step 1: Create `mixed_tab.py` skeleton**

```python
"""Mixed-flow cockpit tab (Assess CFD + BEM Optimize)."""

from __future__ import annotations

from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.figures import mf_scatter_figure


def setup_mixed_tab(ctx: CockpitCtx) -> None:
    """Init mf_* state and controllers (call before SinglePageLayout)."""
    state, ctrl = ctx.state, ctx.ctrl
    # paste Mixed controller block here (see Step 2)


def render_mixed_tab(ctx: CockpitCtx) -> None:
    """Build Mixed UI (call inside layout content)."""
    # paste Mixed UI block here
```

- [ ] **Step 2: Move Mixed logic carefully**

From `app.py`, move into `setup_mixed_tab`:

1. Marker `# ---- Mixed-flow tab` through Mixed helpers (`_refresh_mf_figure`, `_mf_flat_from_state`, `_mf_busy`, `_show_mf_stl`, preview/export/assess/optimize/refine Mixed defs).
2. **Exclude** any `prop_*` / `_on_prop_model` / `prop_editor_*` / `analyze_prop` / `optimize_prop` / `refine_prop_cfd` / `load_prop_row` that currently sit between Mixed and Volute.
3. Include `load_mf_trial` (today after `load_prop_row`).

Move UI from `# ---- MIXED-FLOW TAB` through the Mixed `html.Div(v_show="active_tab === 'mixed'")` block into `render_mixed_tab`. Keep the outer `with html.Div(v_show=...):` inside `render_mixed_tab`.

Inside moved code, replace `_spawn_busy_ticker` → `ctx.spawn_busy_ticker`, `_busy_bar` → `ctx.busy_bar`, `mf_plotter` → `ctx.mf_plotter`, `runs_root` → `ctx.runs_root`. Import Trame/PyVista the same way as `app.py` (or import `html`, `v3`, `plotly_widgets`, `plotter_ui`, `asynchronous`, `pv` from the already-loaded modules — simplest: import inside functions from trame only when not testing, matching app’s pattern; if `render`/`setup` only run from live `build_server`, import at top of `mixed_tab.py` like non-test app imports).

**Practical import rule for tab modules:** import Trame/PyVista at module top the same as live `app.py` (tabs are only loaded from `build_server` after the pytest stub branch). Do **not** import tab modules from unit tests that must stay headless — Task 1 already removed those greps. Optional smoke: `import fansim.cockpit.mixed_tab` only outside pytest or after accepting VTK.

- [ ] **Step 3: Call from `app.py`**

Before `with SinglePageLayout`:

```python
from fansim.cockpit.mixed_tab import render_mixed_tab, setup_mixed_tab

setup_mixed_tab(ctx)
```

Inside layout, where Mixed UI was:

```python
render_mixed_tab(ctx)
```

Remove inlined Mixed code from `app.py`.

- [ ] **Step 4: Verify**

Run: `uv run python -m pytest -q tests/test_cockpit_view.py tests/test_placement.py -m "not docker"`

Expected: PASS. Manually optional: launch cockpit and open Mixed tab.

---

### Task 4: Extract Volute tab

**Files:**
- Create: `fansim/cockpit/volute_tab.py`
- Modify: `fansim/cockpit/app.py`

**Interfaces:**
- Produces: `setup_volute_tab(ctx)`, `render_volute_tab(ctx)`
- Consumes: `ctx.volute_plotter`, busy helpers, `ctx.runs_root`

- [ ] **Step 1: Create `volute_tab.py` with `setup_volute_tab` / `render_volute_tab`**

Move contiguous block from `# ---- Volute tab` through end of Volute controllers (before `# ---- CROR tab`) into setup. Move `# ---- VOLUTE TAB` UI `v_show="active_tab === 'volute'"` into render.

Wire `ctx` the same way as Mixed.

- [ ] **Step 2: Call `setup_volute_tab(ctx)` / `render_volute_tab(ctx)` from shell; delete inlined Volute**

- [ ] **Step 3: Run** `uv run python -m pytest -q tests/test_cockpit_view.py`

Expected: PASS.

---

### Task 5: Extract Prop tab

**Files:**
- Create: `fansim/cockpit/prop_tab.py`
- Modify: `fansim/cockpit/app.py`

**Interfaces:**
- Produces: `setup_prop_tab(ctx)`, `render_prop_tab(ctx)`
- Consumes: `ctx.prop_plotter`, `prop_scatter_figure`, busy helpers, `ctx.runs_root`

- [ ] **Step 1: Gather all Prop pieces into `prop_tab.py`**

Move into `setup_prop_tab`:

1. Banner `# PROPELLER ARCHETYPE` state init + `_init_prop_editor` / `_prop_click_store` / `_prop_table_rows` / `_refresh_prop_figure` / `_reload_prop_from_disk` (before Mixed marker).
2. Prop controllers currently between Mixed and Volute: `_prop_model_readout`, `_on_prop_model`, `prop_editor_spec`, `prop_editor_params`, `_draw_prop`, `_prop_perf_lines`, `analyze_prop`, `optimize_prop`, `refine_prop_cfd`, `load_prop_row`.
3. `export_prop_stl` (today after CROR controllers — move into Prop setup; call order among setups does not require CROR to run first).

Move Prop UI `# ---- PROPELLER TAB` / `v_show="active_tab === 'propeller'"` into `render_prop_tab`.

- [ ] **Step 2: Shell wiring**

```python
from fansim.cockpit.prop_tab import render_prop_tab, setup_prop_tab

setup_prop_tab(ctx)  # before layout; order vs other setups: Fan first later; among non-fan, any order OK if no cross deps
```

Inside layout: `render_prop_tab(ctx)` in the Prop position (after Volute render, before CROR render).

- [ ] **Step 3: Run** `uv run python -m pytest -q tests/test_cockpit_view.py`

Expected: PASS.

---

### Task 6: Extract CROR tab

**Files:**
- Create: `fansim/cockpit/cror_tab.py`
- Modify: `fansim/cockpit/app.py`

**Interfaces:**
- Produces: `setup_cror_tab(ctx)`, `render_cror_tab(ctx)`
- Consumes: `cror_scatter_figure`, busy helpers, `ctx.runs_root` (no dedicated CROR plotter today)

- [ ] **Step 1: Move `# ---- CROR tab` controllers + CROR UI into `cror_tab.py`**

Do **not** include `export_prop_stl` (already in Prop).

- [ ] **Step 2: Wire setup/render in shell; delete inlined CROR**

- [ ] **Step 3: Run** `uv run python -m pytest -q tests/test_cockpit_view.py`

Expected: PASS.

---

### Task 7: Extract Fan helpers + Fan tab; shrink shell

**Files:**
- Create: `fansim/cockpit/fan_helpers.py`
- Create: `fansim/cockpit/fan_tab.py`
- Modify: `fansim/cockpit/app.py` (thin shell)
- Modify: `docs/roadmap.md` (§9.4 done)

**Interfaces:**
- Produces in `fan_helpers.py` (pure, no Trame): `_blade_z_extent`, `_blade_max_dia`, `_depth_drivers`, `_load_assessed_designs`, and any other pure Fan helpers identified in Step 1 of Task 1 (`_has_real_cfm` if Fan-only).
- Produces: `setup_fan_tab(ctx)`, `render_fan_tab(ctx)`
- Shell `build_server` after this task should: load designs, create server/plotters, build `ctx`, `setup_fan_tab` + other setups, open layout, emit tab chrome, call `render_*` in order Fan→Mixed→Volute→Prop→CROR, bind `ctrl.*_update`, return server.

- [ ] **Step 1: Move pure Fan helpers to `fan_helpers.py`**

Move `_blade_z_extent`, `_blade_max_dia`, `_depth_drivers`, `_load_assessed_designs` (and `_has_real_cfm` if still in `app.py`). Import them from `fan_tab` / remaining `app` as needed.

- [ ] **Step 2: Move remaining Fan controllers + Fan UI into `fan_tab.py`**

Everything that remains Fan-specific inside `build_server` before the Prop banner (editors, Assess, Optimize, Library, glyphs, airflow, measurements, fan model manager, `_slider`/`_help_switch`/`_opt_section` if still module-level — move module-level Fan widget helpers into `fan_tab.py` or `fan_helpers` only if pure).

`setup_fan_tab` needs access to `study_designs`, `user_designs`, `by_trial`, `next_id`, `assess_dir` — extend `CockpitCtx` **only if needed**:

```python
# Add optional Fan session fields to CockpitCtx in context.py:
study_designs: list | None = None
user_designs: list | None = None
by_trial: dict | None = None
next_id: list | None = None  # mutable [int] box as today
assess_dir: Path | None = None
```

Populate these on `ctx` in `build_server` before `setup_fan_tab(ctx)`.

- [ ] **Step 3: Shell shape target**

`build_server` should look structurally like:

```python
def build_server(run_dir, study_name=None):
    # load designs, user_designs, by_trial, next_id, assess_dir, runs_root
    server = get_server(client_type="vue3")
    state, ctrl = server.state, server.controller
    _quiet_connection_reset(server)
    # create 4 plotters
    busy_expr = make_busy_expr()
    busy_bar = make_busy_bar(v3, busy_expr)
    spawn_busy_ticker = make_spawn_busy_ticker(state, asynchronous)
    ctx = CockpitCtx(...)
    setup_fan_tab(ctx)
    setup_mixed_tab(ctx)
    setup_volute_tab(ctx)
    setup_prop_tab(ctx)
    setup_cror_tab(ctx)
    with SinglePageLayout(server) as layout:
        layout.title.set_text("Fan-simulator Cockpit")
        state.trame__title = "Fan-simulator Cockpit"
        with layout.content:
            with v3.VContainer(fluid=True, classes="pa-2"):
                with v3.VTabs(v_model=("active_tab",), color="primary", classes="mb-3"):
                    # existing five VTab tooltips unchanged
                    ...
                render_fan_tab(ctx)
                render_mixed_tab(ctx)
                render_volute_tab(ctx)
                render_prop_tab(ctx)
                render_cror_tab(ctx)
    # ctrl.*_update bindings that today live at end of layout — keep in shell
    # if they reference widgets created inside render_*: either
    # (a) have each render_* assign ctrl.view_update = ... itself, or
    # (b) return widget handles from render_* 
    # Prefer (a): move each `ctrl.X_update = widget.update` into the tab that creates the widget.
    return server
```

Ensure `state.active_tab = "fan"` is set once (Prop setup currently sets it — keep a single assignment in shell or Fan setup, not duplicated conflicting defaults).

- [ ] **Step 4: Line-count check**

Run: `wc -l fansim/cockpit/app.py` (or PowerShell `(Get-Content …).Count`)

Expected: `app.py` well under 1000 lines (stretch 500–800).

- [ ] **Step 5: Full non-docker suite**

Run: `uv run python -m pytest -q -m "not docker"`

Expected: PASS (ignore Windows OCCT teardown noise).

- [ ] **Step 6: Mark roadmap §9.4 done**

In `docs/roadmap.md`, change §9.4 to checked with date `2026-09-11` (or today’s date) and one-line note: shell + per-tab modules; source-grep UI tests removed.

Update spec status line in `docs/superpowers/specs/2026-09-11-cockpit-tab-split-design.md` to `implemented`.

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Thin `app.py` shell | 7 |
| `context.py` / `busy_ui.py` / `figures.py` | 1–2 |
| `fan_helpers.py` + five `*_tab.py` | 3–7 |
| setup before layout / render inside | 3–7 (settled choice) |
| Tab order Fan→Mixed→Volute→Prop→CROR | 7 shell |
| Delete source-grep UI tests | 1 |
| Re-home behavioral figure tests | 1 |
| No new source-grep tests | 1 docstring + Global Constraints |
| Roadmap §9.4 done | 7 |
| Out of scope §9.5 | — (not scheduled) |

## Placeholder / consistency self-review

- No TBD steps; Trame nesting settled as setup/render + `v_show`.
- `reject_hint` name consistent across Task 1 and later.
- Prop tab value `"propeller"` called out.
- Interleaved Mixed/Prop cuts called out in Tasks 3 and 5.
- Commits omitted per user rule (explicit ask only).
