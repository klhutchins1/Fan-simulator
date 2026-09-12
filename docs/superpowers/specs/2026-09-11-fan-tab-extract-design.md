<!-- EXTRACTED-FROM-CURSOR-TRANSCRIPT 2026-09-12 -->
# Fan tab further split (post §9.4)

**Date:** 2026-09-11  
**Status:** implemented  
**Roadmap:** `docs/roadmap.md` §9.4 follow-up  
**Approach:** Extract focused Fan modules behind unchanged `setup_fan_tab` / `render_fan_tab`.

## Problem

After the cockpit tab split, `fan_tab.py` remains ~3600 lines (~5× other tabs). Assess, Optimize, viz, and fan-model CRUD are still one nested-closure monolith.

## Goals

1. Thin coordinator: `fan_tab.py` owns session init, editor/fit/library/measurement, and `render_fan_tab`.
2. Extract `fan_session`, `fan_copy`, `fan_widgets`, `fan_models`, `fan_assess`, `fan_optimize`, `fan_viz`.
3. **No behavior change** — same `ctx.fan_*` attrs, state keys, and CFD flows.
4. Keep Fan `_slider` / `_help_switch` Fan-local (no cross-tab `widgets.py` this pass).

## Non-goals

- UI redesign, state-key renames, typed `CockpitCtx.fan_*` fields.
- Deduping sliders across Mixed/Prop/Volute.
- Changing Assess/Optimize CFD logic.

## Module contract

`FanSession` holds shared locks, proc holders, and aliases (`state`, `ctrl`, design lists). Each `bind_*(session)` attaches callables on the session; `expose_to_ctx` copies the public set onto `ctx`.

Public API for `app.py`: unchanged `setup_fan_tab(ctx)` / `render_fan_tab(ctx)` (`render_fan_tab` lives in `fan_ui.py` and is re-exported from `fan_tab`).

## Layout (post-extract)

| Module | Role |
|--------|------|
| `fan_session.py` | Shared bag + `expose_to_ctx` |
| `fan_copy.py` / `fan_widgets.py` | Tooltips + sliders |
| `fan_models.py` | Fan-model CRUD |
| `fan_viz.py` | Preview / glyphs / airflow |
| `fan_assess.py` | Assess + Sweep + cancel |
| `fan_optimize.py` | Optimize subprocess + cancel |
| `fan_ui.py` | Trame layout |
| `fan_tab.py` | Setup orchestrator (editor / library / measurement) |
