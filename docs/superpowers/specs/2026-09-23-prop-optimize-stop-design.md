# Prop Optimize stop

**Date:** 2026-09-23  
**Status:** approved (2026-09-23)  
**Approach:** A `threading.Event` plus Optuna `Study.stop()` after the current trial  
**Parent:** roadmap §14.8 item 1. Items 2–4 stay open.

## Plain language

Prop Optimize runs until every trial finishes. The only way out today is to close the terminal. This slice adds a Stop button that ends the study after the trial already running and keeps the Pareto rows written so far.

## Goal

1. `run_prop_study` accepts `stop_event: threading.Event | None = None`. When the event is set, a callback calls `study.stop()` after the current trial. The function still returns `(study, pareto)` and, when `out_dir` is set, still calls `save_prop_pareto`.
2. The prop Optimize card has a Stop button beside Optimize. It is enabled only while that study is running. The click sets the event. It does not kill the process.
3. After a stop, `prop_msg` names the trial count and the run directory. `prop_busy` clears. The figure reloads from the saved front the same way a finished study does.
4. A test sets the event before `run_prop_study(..., n_trials=20)` and asserts the study completed fewer than 20 trials. No Trame process.

## Non-goals

- Moving `study.db` or changing how often SQLite commits (that is §14.8 item 2)
- Randomize buttons (§14.8 item 3)
- The wiring audit (§14.8 item 4)
- Stopping CFD refine, Analyze, or Export
- Checking the §14.8 checkbox
