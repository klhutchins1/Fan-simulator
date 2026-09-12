<!-- EXTRACTED-FROM-CURSOR-TRANSCRIPT 2026-09-12 -->
# Cockpit Optimize live plot + resume (stage 2)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** While the Optimize subprocess runs, periodically `load_designs(out)` and merge new complete trials into the scatter (same +20000 id offset). Optional **Resume opened run** writes into the cockpit’s `--run` folder so Optuna `load_if_exists` continues that study. Not in-process NSGA. Not live residual charts.  
**Roadmap:** §8.3 remaining.

## Plain language

Today Optimize only refreshes the plot when the process **exits**. A multi-hour study looks dead until it finishes. Stage 2 polls the run’s SQLite as trials complete and adds them live. A resume switch continues the opened study instead of always making `cockpit_opt_*`.

## Goal

1. **`fansim/optimize/cli_argv.py`** (keep argv helper; add merge helpers — no Trame):

```text
opt_out_path(*, resume: bool, run_dir: Path | str, stamp: str | None = None) -> Path
  resume True  → Path(run_dir)
  resume False → runs/cockpit_opt_{stamp or YYYYMMDD-HHMMSS}

merge_opt_designs(loaded, *, offset=OPT_TRIAL_OFFSET, source_run: str,
                  existing_keys: set[tuple[str,int]]) -> list[Design]
  For each loaded design: key = (source_run, orig_trial).
  Skip if key in existing_keys.
  Copy design, set extra orig_trial / source_run / source=cockpit_opt,
  trial = orig + offset. Return only NEW designs (caller appends).
```

2. **`optimization_argv`** — optional `study_name: str | None = None`. When set, append `--study-name`.

3. **Cockpit** — switch `opt_resume` (default off). Label: “Continue the opened run”. When on, `out = run_dir`, pass `study_name` if the opened study has one (else default `"fansim"`). Help text: no longer “does not change the opened study” when resume is on.

4. **Live merge** — in the Optimize wait loop, every ~5 s (or after log chunks), try `load_designs(out)`, `merge_opt_designs`, append new rows, `refresh_items` / `refresh_figure`. Track `existing_keys` for this run. Final merge on success stays (idempotent skips).

## Tests (no Trame, no Docker)

- `opt_out_path(resume=False, …)` under `runs/cockpit_opt_`
- `opt_out_path(resume=True, run_dir=Path("runs/x"))` == `runs/x`
- `merge_opt_designs` offsets trial; second call with same key returns []
- `optimization_argv(..., study_name="fansim")` includes `--study-name fansim`
- `app.py` contains `Continue the opened run` and `merge_opt_designs`

## Non-goals

- Live CFD residual / OpenFOAM log plots
- Changing Optuna sampler mid-run
- Resume into an arbitrary folder picker (opened `--run` only)
- Auto-rebuild catalog.db
