# Fan-Simulator — recovery status (2026-09-12)

Two recoveries are in play; use them together:

- **`CHAT_RECOVERY/` + `RECOVERY_FROM_CACHE.md`** — Cursor's pack (chat-index architecture,
  module inventory, physics contracts, restore priorities). **These are Cursor's files — do
  not overwrite.** Start with `CHAT_RECOVERY/06_restore_priorities.md`.
- **This transcript reconstruction** — actual file *content* replayed from two Claude Code
  session transcripts that survived on `C:`. Every code/doc file I restored carries a
  `RECOVERED-FROM-CHAT` header.

## Honest status — this is an OLD, verbatim snapshot

My transcripts only span **Aug 26 – Sep 3**. The project kept growing until the drive died
(specs dated **09-04** and **09-11**; commit breadcrumbs **`b360dde`**, **`a110f76`**, local
master, push status unknown). So:

- **What I restored is real byte content, but ~10 days behind the drive-death state.**
- Where Cursor (or a later transcript) yields a real, newer copy of a file, **prefer it** and
  delete my `RECOVERED-FROM-CHAT` version. My files are the compiling fallback, not the truth.

## Recovered here (verbatim, marked RECOVERED-FROM-CHAT)

- **130 Python files compile clean**; ~174 files total: most of `fansim/` (geometry incl.
  `airfoil.py`, cfd incl. `templates.py`, optimize incl. `isolated_eval.py`, acoustics,
  propeller, manufacturability, structural, problem, motor, physics, analyze, **surrogate incl.
  `gp.py`**), **33 tests**, **34 scripts**, `docs/` (roadmap + some specs/plans), `validation/`,
  `config/`, `pyproject.toml`, plus `memory/` (10 Claude notes incl. the ~100 KB project log).
- Verified my late Sep-3 work is intact: frame-gap fix (`cockpit/placement.py`) and the
  winglet×shroud gate (`optimize/search_space.py`).

## MISSING here → recover from Cursor (or a later transcript)

Compiles ≠ imports: `objectives.py` imports `system_curve` and `cfd.frame`, so the tree won't
fully import until these land.

**Whole packages (never in my transcripts):**
`fansim/centrifugal/`, `fansim/volute/`, `fansim/cror/`, `fansim/wind_turbine/`

**Cockpit fan-tab extract (09-11 spec) + slices:**
`fansim/cockpit/` → `app.py` (see below), `fan_session.py`, `fan_copy.py`, `fan_widgets.py`,
`fan_models.py`, `fan_assess.py`, `fan_optimize.py`, `fan_viz.py`, `fan_ui.py`, `fan_tab.py`,
`library_view.py`, `busy.py`, `score_caption.py`  (`data.py`, `placement.py` are recovered)

**Other core modules:**
`optimize/system_curve.py`, `optimize/presets.py`, `optimize/design.py`, `cfd/frame.py`,
`cfd/stator.py`, `acoustics/fwh.py`, `isolated_job.py`, `uv.lock`

**Specs (09-04/09-11):** `fan-tab-extract`, `wind-turbine-scaffold`,
`boost-ensemble-surrogate`, `cockpit-opt-live-resume` (under `docs/superpowers/specs/`).

### Interface contracts (from recovered callers, to rebuild/validate the missing ones)

- `system_curve.py`: `score_operating_point(q_free_cfm, q_probe_cfm, p_probe_pa, eta_free,
  eta_load, load_pa)` → obj with `.q_op_cfm/.eta/.k/.p_op_pa`; const `REF_CFM` (=50); `SystemCurveError`.
- `cfd/frame.py`: `export_frame_stl(params, rig, out_path)` (four-bar strut STL).
- `cockpit/library_view.py`: `library_list_items(entries, spec)` → list of row dicts.
- `cockpit/app.py`: `build_server(run_dir, study_name=None)`, `scatter_figure(...)`,
  `_reject_hint(reason)`. ~2377 lines under Cursor; my transcript had only a 990-line Aug-30
  base, saved as `fansim/cockpit/app.py.INCOMPLETE_990base` (do NOT use). After recovering the
  real `app.py`, re-apply the newer edits in `CHAT_RECOVERY/app_py_edits_to_reapply.md`
  (223 edits, newest last — the recent ones are the frame-gap Preview surfacing, the
  `_reject_hint` frame-gap branch, the sweep "0 added" message, and the shroud caption).

## Permanently lost — regenerable (never in transcripts, not source)

`runs/**` OpenFOAM cases + Pareto outputs, `catalog/catalog.db` + generated STLs, `exports/**`,
`docs/control_images/*.png`. Re-created by re-running the pipeline.

## Suggested order

1. `git init` and commit THIS tree as the recovery baseline before merging anything.
2. Overlay Cursor's real files on top; delete the matching `RECOVERED-FROM-CHAT` versions.
3. Rebuild the missing modules/packages per `CHAT_RECOVERY/06_restore_priorities.md` and the
   contracts above; use the `RECOVERED-FROM-CHAT` files as reference.
4. `uv run python -m pytest -m "not docker and not slow"` once imports resolve.
5. Regenerate `catalog.db`/STLs by re-running the optimizer when Docker/OpenFOAM is back.
