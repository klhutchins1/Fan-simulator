# Cockpit `app.py` tab split (§9.4)

**Date:** 2026-09-11  
**Status:** approved design (not yet implemented)  
**Roadmap:** `docs/roadmap.md` §9.4  
**Approach:** **B** — extract one module per top tab + clean shared seams (not a full tab-plugin framework).

## 1. Problem

`fansim/cockpit/app.py` is a ~4939-line `build_server()` monolith (Fan + Mixed + Volute + Prop + CROR). Hard to review, easy to regress, and `tests/test_cockpit_view.py` has grown **source-grep UI tests** that only assert label strings / markers exist in `app.py` — locking the monolith in place.

Existing good pattern: pure helpers already live outside (`library_view.py`, `placement.py`, `busy.py`, `score_caption.py`).

## 2. Goals

1. Thin shell: `app.py` owns server bootstrap, shared plotters, top-level `VTabs` chrome, and calls `register_*`.
2. One module per top tab with controllers + layout for that archetype.
3. Pull shared pure/UI helpers out of `app.py` so tabs do not re-import a fat shell.
4. Delete source-grep UI tests; keep/move **behavioral** unit tests onto extracted helpers.
5. **No behavior change** — same state keys, controllers, tab order, Assess/Optimize flows.

## 3. Non-goals

- Archetype registry / propeller stub (§9.5).
- Deduping isolated-subprocess helpers across geometry packages.
- UI redesign, Trame migration, or rewriting Assess/CFD logic.
- Full plugin API (`Tab` ABC, dynamic discovery) — deferred unless a third-party tab appears.

## 4. Module layout (`fansim/cockpit/`)

| Module | Responsibility |
|--------|----------------|
| `app.py` | `build_server`: get_server, quiet ConnectionReset, create plotters, shared state that crosses tabs (if any), top `VTabs`/`VWindow`, call each `register_*` in order |
| `context.py` | `CockpitCtx` dataclass: `server`, `state`, `ctrl`, `runs_root`, `run_dir`, plotters (`plotter`, `prop_plotter`, `mf_plotter`, `volute_plotter`), and bound busy helpers |
| `busy_ui.py` | Trame-facing `_busy_expr`, `_busy_bar`, `_spawn_busy_ticker` (depends on `busy.py` captions) |
| `figures.py` | Pure Plotly builders + filter helpers: `scatter_figure`, `prop_scatter_figure`, `mf_scatter_figure`, `cror_scatter_figure`, `filter_fitting_designs`, `_reject_hint`, `_has_real_cfm` |
| `fan_helpers.py` | Fan-only pure helpers currently in `app.py`: `_blade_z_extent`, `_blade_max_dia`, `_depth_drivers`, `_load_assessed_designs`, control-image loading, shared slider/`_opt_section`/`_help_switch` widgets if used by Fan Optimize only (or keep widgets in `fan_tab` if not shared) |
| `fan_tab.py` | `register_fan_tab(ctx)` — Fan state, Library/Design/Results, Assess/Sweep/Optimize/export, Fan layout |
| `mixed_tab.py` | `register_mixed_tab(ctx)` |
| `volute_tab.py` | `register_volute_tab(ctx)` |
| `prop_tab.py` | `register_prop_tab(ctx)` |
| `cror_tab.py` | `register_cror_tab(ctx)` |

Leave as-is (already split): `library_view.py`, `placement.py`, `busy.py`, `data.py`, `labels.py`, `score_caption.py`.

### 4.1 Tab registration contract

```python
@dataclass
class CockpitCtx:
    server: Any
    state: Any
    ctrl: Any
    run_dir: Path
    runs_root: Path
    plotter: Any          # Fan
    prop_plotter: Any
    mf_plotter: Any
    volute_plotter: Any
    busy_bar: Callable
    busy_expr: Callable
    spawn_busy_ticker: Callable
    # Fan-specific session stores may stay closed over in fan_tab after register
```

Each `register_<tab>(ctx) -> None`:

1. Initializes that tab’s `state.*` defaults.
2. Defines controllers (closures over local stores + `ctx.state`).
3. Builds UI into the **already-open** `VWindowItem` / parent provided by the shell **or** builds the window item itself if that keeps nesting simpler.

**Preferred nesting (match today):** shell opens `VTabs` + `VWindow` and one `VWindowItem` per tab; each `register_*` receives the item context via building UI as a callback, **or** each register creates its own `VWindowItem` while the shell only creates `VTabs` labels. Pick whichever preserves Trame parent-context with the least churn; document the choice in the implementation plan.

### 4.2 Top-tab order (locked)

Fan → Mixed → Volute → Prop → CROR  
(labels: `"Fan"`, `"Mixed"`, `"Volute"`, `"Prop"`, `"CROR"`; values unchanged).

### 4.3 Pytest / headless import

Keep the existing `_RUNNING_TESTS` guard so importing figure/helpers does **not** require VTK/Trame. Prefer: `figures.py` and `fan_helpers.py` never import PyVista/Trame. Tab modules may import Trame; tests that only need figures import `figures`, not `app`.

`app.py` may still stub Trame under pytest if anything imports `build_server` in tests; prefer not requiring that.

## 5. Extraction map (from current `app.py` markers)

| Approx lines / marker | Destination |
|----------------------|-------------|
| Module-level scatter / filter / reject (~365–590) | `figures.py` |
| Blade extent / depth / load assessed (~592–705) | `fan_helpers.py` |
| `_busy_*` inside `build_server` (~746–787) | `busy_ui.py` (factories taking `v3`/`asynchronous`) |
| Fan block through end of Fan UI / before Prop banner (~707–2954, excluding later tabs) | `fan_tab.py` + thin shell leftovers |
| `# PROPELLER ARCHETYPE` / prop init before Mixed (~2955–3031) + Prop UI later | `prop_tab.py` |
| `# ---- Mixed-flow tab` (~3032–3745) | `mixed_tab.py` |
| `# ---- Volute tab` (~3746–3930) | `volute_tab.py` |
| `# ---- CROR tab` (~3931–end of CROR) | `cror_tab.py` |
| Layout `# ---- FAN TAB` / MIXED / VOLUTE / PROP / CROR markers | respective `*_tab.py` |

Shared control images / `_slider` / `_help_switch`: move with Fan if Fan-only; if Prop/Mixed reuse, put in `widgets.py` (only create that file if ≥2 tabs share them).

## 6. Tests

### Keep / re-home (behavioral)

| Test | New import home |
|------|-----------------|
| `test_reject_hint_*` | `fansim.cockpit.figures` (or public `reject_hint` without leading `_`) |
| `test_filter_fitting_designs_*` | `figures` |
| `test_scatter_*` | `figures` |
| `test_results_for_hub_*` / library list | unchanged (`catalog`, `library_view`) |
| `test_format_elapsed_*` / `test_busy_caption_*` | unchanged (`busy`) |

Optional: drop leading underscores on `reject_hint` when exporting from `figures` (tests import the public name).

### Delete (source-grep UI)

Delete from `tests/test_cockpit_view.py` (and do **not** reintroduce):

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
- Helper `_read_cockpit_app_source`

Provenance / export / Assess behavior remains covered by dedicated unit tests elsewhere where they exist (`test_placement`, export helpers, etc.). Gaps are accepted over re-locking UI strings.

### Add (lightweight)

- Import smoke: `figures`, `busy_ui` factories (if pure), each `register_*` module import under pytest without calling Trame layout (or call only if stubs allow).
- No new “string in source file” assertions.

## 7. Success criteria

- [ ] `app.py` ≪ ~1000 lines (stretch: ~500–800).
- [ ] Each of Fan/Mixed/Volute/Prop/CROR lives in its own `*_tab.py`.
- [ ] Shared figures/filters/reject-hint live outside `app.py`.
- [ ] Zero source-grep UI tests in `test_cockpit_view.py`.
- [ ] `uv run python -m pytest -q -m "not docker"` green (Windows OCCT teardown noise OK).
- [ ] Manual: cockpit launches; top tabs switch; Fan Assess/Library still wired (smoke by user if needed).
- [ ] Roadmap §9.4 checked done with date.

## 8. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Closure / late-binding bugs when moving controllers | Move one tab at a time; keep Fan last or first but land Mixed/Volute/Prop/CROR first (smaller) |
| Circular imports (`app` ↔ tabs) | Tabs import `context` + helpers only; `app` imports tabs; no tab imports `app` |
| Trame parent context broken if UI built outside `with` block | Register functions run **inside** the shell’s layout `with` nesting |
| Pytest still imports fat `app` | Re-home figure tests; avoid importing `build_server` in unit tests |
| Missed symbol after cut | Run full non-docker suite after each tab extract |

## 9. Implementation order (high level)

1. Extract `figures.py` + re-home/delete tests (green).
2. Extract `busy_ui.py` + `context.py`.
3. Extract `mixed_tab` → `volute_tab` → `prop_tab` → `cror_tab` (smaller than Fan).
4. Extract `fan_helpers.py` + `fan_tab.py`; shrink `app.py` to shell.
5. Mark roadmap §9.4 done; note “no new source-grep UI tests” in known-issues or test file docstring.

## 10. Open implementation choices (settle in plan, not blockers)

1. Exact Trame nesting API (`register` builds `VWindowItem` vs shell provides open context).
2. Whether `_slider` / `_help_switch` warrant `widgets.py` or stay Fan-local.
3. Public rename `reject_hint` vs keep `_reject_hint` re-export for one release.
