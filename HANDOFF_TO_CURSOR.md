# Handoff: Claude ⇄ Cursor recovery division of labor

**We were deadlocking by mutual deference.** This ends it. Claude's side is now fully
dumped and committed. Cursor was the last agent to work on the code (09-04 / 09-11), so
Cursor holds the newest context — **Cursor fills the gaps below.**

## Claude side — DONE (committed to `master`, tag/commit `Recovery baseline …`)

Reconstructed **verbatim** from two surviving Claude Code transcripts (Aug 26 – Sep 3),
every file marked `RECOVERED-FROM-CHAT`:

- 130 Python files (compile-clean) + 33 tests + 34 scripts + docs + `pyproject.toml` +
  `validation/` + `config/` + `memory/` (10 notes incl. the ~100 KB `fan-sim-status.md`).
- Partial but substantial: **`app.py`** — I have a 990-line base, **73% of the grown
  ~2377-line file across 99 read windows** (`CHAT_RECOVERY/fragments/app_py_all_read_windows.md`),
  and **all 223 edits** (`CHAT_RECOVERY/app_py_edits_to_reapply.md`).

**Rule for overlap:** where Cursor has a *newer real* copy of any file above, Cursor's wins —
replace the `RECOVERED-FROM-CHAT` file and delete the marker. Mine is the compiling fallback.

## Cursor side — PLEASE PROVIDE (Claude has ZERO source bytes for these)

I confirmed by scanning both transcripts: no definition of these ever appeared (not even via
Grep/Bash). I only have their **interface contracts** (below), inferred from the recovered
callers. These block imports today (`objectives.py` needs `system_curve` + `cfd.frame`).

### Single modules
- `fansim/optimize/system_curve.py` — `score_operating_point(q_free_cfm, q_probe_cfm,
  p_probe_pa, eta_free, eta_load, load_pa)` → obj with `.q_op_cfm/.eta/.k/.p_op_pa`;
  const `REF_CFM` (=50); exception `SystemCurveError`. (2-pt fan line ∩ ΔP=k·Q².)
- `fansim/cfd/frame.py` — `export_frame_stl(params, rig, out_path)` (four-bar strut STL).
- `fansim/optimize/presets.py` — `PRESETS` (dict: case≈8, heatsink≈20, radiator≈35 Pa @50 CFM)
  and `resolve_load(preset, load_pa)`; used by `scripts/run_optimization.py`.
- `fansim/optimize/design.py` — canonical `Design` dataclass (a `Design` also exists in the
  recovered `cockpit/data.py`; confirm which is source of truth).
- `fansim/cfd/stator.py`, `fansim/acoustics/fwh.py`, `fansim/isolated_job.py`
  (`run_worker_module`, `load_objective_result`), `uv.lock`.

### Cockpit fan-tab extract (09-11 spec) — all missing
`fansim/cockpit/`: `app.py` (recover full, then re-apply my 223 edits, newest last —
frame-gap Preview surfacing, `_reject_hint` gap branch, sweep "0 added", shroud caption),
`fan_session.py`, `fan_copy.py`, `fan_widgets.py`, `fan_models.py`, `fan_assess.py`,
`fan_optimize.py`, `fan_viz.py`, `fan_ui.py`, `fan_tab.py`, `library_view.py`
(`library_list_items(entries, spec)` → list of row dicts), `busy.py`, `score_caption.py`.
(`data.py`, `placement.py` are recovered.)

### Whole later packages — all missing
`fansim/centrifugal/`, `fansim/volute/`, `fansim/cror/`, `fansim/wind_turbine/`
(inventories in `CHAT_RECOVERY/02_module_inventory.md`).

### Specs (09-04 / 09-11)
`docs/superpowers/specs/`: `2026-09-11-fan-tab-extract-design.md`,
`2026-09-11-wind-turbine-scaffold-design.md`, `2026-09-04-boost-ensemble-surrogate-design.md`,
`2026-09-04-cockpit-opt-live-resume-design.md`.

## Suggested flow (no more waiting)

1. Cursor exports the ZERO-BYTE files above straight into this tree (overwriting nothing marked
   is impossible — those paths don't exist yet).
2. Cursor overlays newer copies of any `RECOVERED-FROM-CHAT` file it has; delete the marker.
3. Anyone: `git add -A && git commit` after each batch (baseline is already committed, so every
   step is a clean diff).
4. `uv run python -m pytest -m "not docker and not slow"` once `system_curve.py` + `cfd/frame.py` land.
5. Regenerate `runs/`, `catalog.db`, `*.stl` by re-running the optimizer.

Breadcrumbs (local master, push status unknown): commits `b360dde`, `a110f76`.
