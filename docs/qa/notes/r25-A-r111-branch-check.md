# QA r25 A: UI-31 / R1.11 and QA-62 on the unmerged branch, plus the other UI and bug items

**Tested:** 2026-11-02, MST.

**Prereg:** `prereg/round25` b7e7574e, committed before any data. A copy is in `handoff/2026-11-02_from-qa-25/`.

**Brief:** Cursor's **uncommitted draft** `CLAUDE_TO_QA_r25_DRAFT.md`, copied to the handoff folder for the record. It was not in any commit. Its `fansim.bundle` does not exist; I used `master_9d0118f_plus_r111.bundle`.

**Heads:**
- **Branch:** `r111-hide-surrogate` @237a094. It is 7 commits ahead of the merge-base b0228fe, unmerged, and run in a separate clone `repo-r25-r111`.
- **Master:** 9d0118f. It has no `fansim/`, `scripts/` or `tests/` change since r24's 23831da; 3ec0bb3, 9e36cea and 9d0118f touch docs only.

**Label.** Every branch result below means: **verified on unmerged branch r111-hide-surrogate @237a094, not on master.** Nothing is closed here.

**How it was run:**
- No CFD, Docker, OpenFOAM, Assess, Sweep or Optimize. Only Preview was clicked.
- `run_optimization.py` was read, not executed.
- The cockpit ran headless on :8091 (branch) and :8092 (master), driven by Playwright with system Chrome.
- I used the r24 harnesses (`a_ui`, `a_probe`, `a_tooltips` with a UI-31 render count added, `a_flowcard`, `scan_controls`, `build_inventory`, `range_check`) and the new `a_ui31_cli.py`.

## UI-31 / R1.11

| check (prereg) | branch 237a094 | master 9d0118f |
|---|---|---|
| (a) render: visible "Surrogate-guided" labels, Expert with all panels open | **0**; not in page text | **1** (switch renders) |
| (b) cockpit argv with `opt_surrogate_guided=True` forced | `cockpit_optimization_argv` (`fan_optimize.py:60`, `surrogate_guided=False`) → **no `--surrogate-guided`** | no seam; `fan_optimize.py:141` passes `bool(state.opt_surrogate_guided)` |
| (c) CLI: refuse a stub rank without a gate | `surrogate_guided_cli_error` (`cli_argv.py:199`) is called in `main` before the loop (`run_optimization.py:164-170`, `return 2`). Guard table: only verify=F/stub=F refuses | **no guard**: `--surrogate-guided` alone ranks with `synthetic_label` |
| (d) explicit CLI stub path | **present**: `--stub-labels` (`run_optimization.py:113`); prints "synthetic labels, not CFD" (`:180`) | absent |
| (e) behaviour test | cockpit argv: **present** (`test_r111_cockpit_surrogate.py::test_cockpit_argv_omits_surrogate_guided_even_if_state_on`, a real call, passes). CLI: **guard-function unit test only**; no test drives the parser or `main` | absent |
| tests | `test_r111_cockpit_surrogate.py` 5/5 pass; `test_optimization_argv.py` passes | file absent |

**Status:**
- UI-31: **fixed on branch (pending merge)**, since (a), (b) and (c) hold. Master: **still open**.
- R1.11 closing items from 9e36cea, on the branch:

| closing item | status |
|---|---|
| cockpit behaviour test | done |
| CLI refusal unless `--verify-cfd` or `--stub-labels` | done |
| "synthetic labels, not CFD" stamp | **stdout only**: `surrogate_guided.json` notes say `verify=stub`, not "synthetic labels" |
| dead `opt_surrogate_guided` tooltip | done; `fan_copy.py` has no entry |
| GP-boost tooltip mention | nothing to do: the tooltip never named Surrogate-guided on either head; UI-34 is the enabled-but-inert issue, see below |

- **Not yet closable**, because of the CLI behaviour test and QA-66 below.
- Proposed CLI behaviour test: `docs/qa/patches/r25-A-r111-cli-behaviour-test.patch`. It applies to 237a094 (`git apply --check` OK), and with it the file passes 7/7 in a scratch copy. It:
  - drives the real `build_parser()` with `--surrogate-guided` alone, with `--stub-labels`, and with `--verify-cfd`, through the guard;
  - pins that `main` calls the guard before `run_surrogate_guided`.

**Leftover (cosmetic, no ID):** `fan_core.py:124` still sets the now-unused `state.opt_surrogate_guided = False`.

**Merge note:** `git merge-tree` of master and 237a094 gives a **conflict in `docs/release/RELEASE_PLAN.md`** only, because the branch carries its own copies of the r24 queue and results commits (9e721d0, 25d88dc). Code merges cleanly.

### New: QA-66 (MED). The R1.11 CLI gate still lets synthetic labels through

Found on the branch by code reading; nothing was run.

1. **`--verify-cfd` still trains on synthetic labels.** `run_surrogate_guided` uses `label = label_fn or synthetic_label` (`surrogate_search.py:458`). The CLI never passes `label_fn`, so the 24 default DoE points are labelled by `synthetic_label` (`:484`); only the top-k verify is CFD. No "synthetic" notice is printed, because `:179` prints only when `--stub-labels` is on without `--verify-cfd`.
2. **The documented wrapper opts in silently.** `scripts/run_surrogate_search.py:26-27` adds `--stub-labels` whenever `--verify-cfd` is missing, so the explicit opt-in the review asked for is bypassed on that entry point.
3. **The stub output on disk is not stamped "synthetic labels, not CFD".** Only stdout says it; `surrogate_guided.json` notes say `verify=stub` and `DoE n=24`.

**Fix direction (not a patch):**
- Pass a CFD (or catalog-only) `label_fn` when `--verify-cfd` is set, or refuse DoE>0 without `--stub-labels`.
- Have the wrapper refuse rather than add `--stub-labels`.
- Write `"labels": "synthetic, not CFD"` into `surrogate_guided.json`.

Cockpit users are not exposed on the branch, because the switch is hidden.

## QA-62

| | branch 237a094 | master 9d0118f |
|---|---|---|
| `validate_lt120.py` listed | in **`AXIAL_SCRIPTS`** (`tests/test_axial_scripts_oriented.py:14`) | not listed |
| `test_axial_scripts_oriented` | **passes** | **fails** (`test_no_unlisted_script_calls_build_case`) |

QA-62: **fixed on branch (pending merge)**. Master: **still open**.

## Other items

All are run on both heads. The harness output is identical to r24 except where noted.

| item | branch 237a094 | master 9d0118f |
|---|---|---|
| UI-26 jargon | still open on branch. The jargon renders in 3/4 viewports this run; 1366×768 Simple did not show "Gold = parametric Stock" on **either** head this time (r24: 4/4). No cockpit code changed, so this is treated as render timing, not a fix | still open |
| UI-27 viewer cut off at 1366×768 | still open on branch (viewer bottom 957 px of 768) | still open (957) |
| UI-29 1920 layout / "Start here" | still open on branch (identical probe) | still open |
| UI-32 control images | still open on branch (loader 54 `e_*`, 0 `opt_*`/`assess_*`) | still open (54/0) |
| UI-33 Optimize ignores sliders | still open on branch (no hit words in panel text) | still open |
| UI-34 Boost/NN inert | still open on branch: both enabled with GP skip off; tooltips say "With Catalog GP skip on…". With Surrogate-guided gone, GP skip is now their only gate | still open |
| UI-35 image ranges | still open on branch (range_check 58 rows, byte-identical to r24) | still open (identical) |
| UI-36 missing tooltips | still open on branch (0/8 hovered show one; inventory: only change is the removed Surrogate-guided row, 292 vs 293) | still open (0/8; 293, identical) |
| UI-37 proxy tooltips | still open on branch (inventory unchanged) | still open |
| UI-38 design pick resets settings | still open on branch (captions as r24; reset unchanged) | still open |
| QA-40 noise row in Simple | still open on branch (flowcard identical) | still open |
| QA-42 "11 g" no material | still open on branch (preview text identical) | still open |
| QA-61 "~15–30 min" vs "30–40" | still open on branch: same 8 grep lines. `mixed_tab.py:362` "15–30 min" is also listed; it is Mixed-tab copy | still open (same) |
| QA-63 fuse "remaining" > "whole" | still open on branch (`test_fuse_memory` fails) | still open (fails) |

## Fast suite

Command: `-m "not docker and not slow"`. Both heads ran in parallel from 08:23 MST.

| head | failed | passed | skipped | deselected | xfailed | time | failing tests |
|---|---|---|---|---|---|---|---|
| master 9d0118f | 4 | 1883 | 21 | 23 | 1 | 42 min 48 s | QA-62, QA-63, QA-41 ×2 (same as r24) |
| branch 237a094 | 3 | 1889 | 21 | 23 | 1 | 66 min 18 s | QA-63, QA-41 ×2 |

The branch's 1889 passes are master's 1883, plus QA-62 now passing, plus the 5 R1.11 tests.

The branch run was slow because of `test_fan_tab_setup_smoke.py::test_readonly_handlers_run`:
- it spent about 25 min in an OCC loft on unseeded random geometry, then passed;
- this is filed as **QA-67 (LOW)**: seed the RNG in the test.
