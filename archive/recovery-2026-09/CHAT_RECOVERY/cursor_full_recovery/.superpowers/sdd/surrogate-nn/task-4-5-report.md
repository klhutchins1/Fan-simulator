## Task 4–5 Report (surrogate-nn + docs)

### Status
- **Task 4**: Implemented `--surrogate-nn` end-to-end (CLI, study wiring, cockpit argv gating, tests).
- **Task 5**: Documentation + spec status updated (roadmap, bibliography, spec status, surrogate package docstring).

### Code changes
- **`scripts/run_optimization.py`**
  - Added `--surrogate-nn` flag and passed through to `run_study(..., surrogate_nn=...)`.
- **`fansim/optimize/study.py`**
  - Added `surrogate_nn: bool` flag.
  - Passed `nn=...` into `prescreen_fit(...)`.
  - If both boost and nn are enabled: **nn wins** and prints **one** log line (`surrogate-prescreen: nn enabled; boost ignored`).
- **`fansim/optimize/cli_argv.py`**
  - Added `gp_nn` and gated `--surrogate-nn` exactly like `--surrogate-boost`: only emitted when `gp_floor > 0`.
- **`fansim/cockpit/app.py`** (optional UI)
  - Added `opt_gp_nn` state, a VSwitch, and passed `gp_nn=...` into `optimization_argv(...)`.
- **Tests**
  - `tests/test_optimization_argv.py`: added `test_gp_nn_only_with_gp_floor`.

### Docs
- **`docs/roadmap.md` §7.4**
  - Marked NN+GP stage 1 done; noted FNO stub; clarified real CNN/FNO still remaining (needs field snapshots).
- **`docs/bibliography.md` §6**
  - Added NN+GP ensemble entry; updated FNO entry to reflect stub shipped (real training still future).
- **`docs/superpowers/specs/2026-09-08-surrogate-nn-fno-stub-design.md`**
  - Status updated to **implemented**.
- **`fansim/surrogate/__init__.py`**
  - Docstring now references `--surrogate-nn` explicitly.

### Tests run
- `uv run pytest tests/test_optimization_argv.py tests/test_boost_ensemble.py tests/test_surrogate_nn.py -q`
  - **23 passed, 3 skipped**.

### Notes / concerns
- A full `uv run pytest` run was started but appeared to stall (no new progress output for an extended period) and was terminated; the targeted suite covering Task 4–5 changes is green.
