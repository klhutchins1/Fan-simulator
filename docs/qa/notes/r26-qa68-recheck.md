# r26 follow-up (grok, 2026-11-08): QA-68 re-check on master 419df2e

## Setup

- **Code under test:** `/workspace/fansim/repo-r26-qa68`, a fresh clone of `handoff_in/master_419df2e.bundle`.
  - Bundle sha256 is `24bcef9c588d65a4d04e6041f74902568f892ebbd88d033b0245fa731da2e25c` (matches).
  - HEAD is `419df2ec0c17c028063bc3afe5a40642e75c0125`.
  - There were no edits or commits; `git status` is empty afterwards.
- **Prereg:** branch `prereg/round26-qa68-recheck`, commit 491f0d2 (`qa_r26/PREREG_R26_QA68.md`). It was committed 2026-11-08 13:30 MST, before any diff, test or probe output.
- **What did not run:** no Docker, CFD, OpenFOAM, Assess, Sweep or Optimize compute. The box has no `docker` binary.
  - `image_available` is monkeypatched.
  - The CFD verify closure is replaced by one that aborts if called.
- **Scope:** QA-68 only. This is not round 27. R1.10 G2, R3.1, R3.3 and the rest were not re-tested.
- **Data:** `handoff/2026-11-08_from-qa-26-qa68/`.

## Static evidence (inspected, not by itself verification)

- **What d08e48c changes:** it touches `scripts/run_optimization.py` and `tests/test_r111_cockpit_surrogate.py`. It is merged by d365bea, and d365bea..419df2e does not touch those files, `fansim/optimize/` or `tests/test_surrogate_guided.py`.
- **The fix:**
  - `run_surrogate_guided(...)` is wrapped in `try … except RuntimeError as exc: print(exc); return 2` (`run_optimization.py:183-206`).
  - The earlier Docker guard (`:173-175`, return 2) is unchanged.
- **Our r26-A patch** (not re-applied):
  - The script hunk is present exactly: it reverse-applies cleanly with `--include='scripts/*'`.
  - The test hunk reverse-fails, because the landed test differs slightly (27 lines vs 28). The test `test_cli_verify_cfd_without_catalog_exits_2_not_traceback` is at `tests/test_r111_cockpit_surrogate.py:108`.
- **Informational (no new ID):** the `except` covers the whole surrogate run, not only the up-front refusals.
  - A `RuntimeError` raised later, for example from a real CFD verify, would also become a one-line message and exit 2, with no traceback.
  - This is acceptable for a CLI, but it hides the stack trace when debugging.
  - This is static only and was not exercised.
  - If wanted, the fix would be to move the catalog check into a `check_*` helper called before the run, or to re-raise unless the message starts with "ERROR: --verify-cfd". No patch is proposed.

## Behavioural evidence on 419df2e (`qa68_probe.json`)

All cases run `run_optimization.main()` with `--surrogate-guided --verify-cfd`:

| case | Docker (CLI / library) | catalog | result |
|---|---|---|---|
| c1 | present / present | none | **returns 2**, prints "needs a catalog with ≥ 8 CFD rows", no exception, no JSON |
| c2 | present / present | 7 rows | **returns 2**, same message, no JSON |
| c3 | absent (CLI guard) | none | **returns 2**, Docker message, no JSON, no out dir |
| c3b | present / absent (library refusal → caught) | none | **returns 2**, Docker message, no JSON |
| control | present / present | 8 rows | gets past the refusal and hits the guarded CFD verify (aborted). This proves the mock is live |
| c5, real subprocess (`python scripts/run_optimization.py`, sitecustomize mock) | present / present | none | **exit 2**, empty stderr (no "Traceback"), catalog message on stdout |

- CFD verify was called 1 time in total, and that was the control; c1–c5 called it 0 times.
- c5 printing the catalog message rather than the Docker message shows the mock worked, since this box has no Docker.
- Noted, not a fail: c1, c2 and c3b create the out dir before refusing.

## Regression tests

- **The targeted files pass, 36 of 36** (3.0 s):

  | file | tests |
  |---|---|
  | `test_r111_cockpit_surrogate` (includes the QA-68 test) | 9 |
  | `test_surrogate_guided` | 11 |
  | `test_optimization_argv` | 16 |

- **Red check:** in a scratch clone I restored `scripts/run_optimization.py` to `d08e48c^`. That gives 1 failed (`test_cli_verify_cfd_without_catalog_exits_2_not_traceback`) and 8 passed in `test_r111_cockpit_surrogate`. The landed test does detect the bug.

## Verdict against the prereg

- Rules 1, 2, 3, 4 and 6: **verified, behavioural**.
- Rule 5 (subprocess): **verified, behavioural**.
- Rule 7: informational, static only.
- **QA-68: verified, closable.**

## Remaining blockers (not tested here; status as the brief reports it)

- R1.10 G2: tests are queued, the runtime is unknown, and it is not merged.
- R3.1: not landed (the export leak check is still waiting).
- The R3.5b merge gate is queued.
- R3.3 is reported done; not re-tested.
- Items carried from r26 (UI-26 etc.) are unchanged and were not re-tested.
