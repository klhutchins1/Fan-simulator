# r26 follow-up pre-registration: QA-68 re-check (grok)

**Written:** 2026-11-08 MST, before any code diff, test or probe output of this follow-up.
**Code under test:** fresh clone `/workspace/fansim/repo-r26-qa68` of `handoff_in/master_419df2e.bundle`
(sha256 24bcef9c…2e25c, verified) at master 419df2e. QA-68 fix d08e48c, merged d365bea.
**Seen before writing:** commit subjects bd6abdd..419df2e; the bundle hash; the brief file list.
**Scope:** QA-68 only. Not round 27. R1.10 G2, R3.1, R3.3 and everything else: not re-tested.
**Rules:** no Docker/CFD/OpenFOAM/Assess/Sweep/Optimize compute; Docker presence and CFD verify are mocked
(verify closure raises if called). No commits or edits in the snapshot. Our r26-A patch is not re-applied
(`git apply --check` / `--reverse --check` only, as static evidence).

## Evidence classes
- **static:** code reading, diffs, `git apply --check`.
- **behavioural:** a test or probe actually executed on 419df2e.
A rule passes as **verified** only with behavioural evidence; static-only = **inspected, not verified**.

## Pass rules (all on 419df2e, `run_optimization.py --surrogate-guided --verify-cfd`, Docker mocked present)
1. No catalog file → `main()` returns 2, prints the "needs a catalog with ≥ 8 CFD rows" message, no traceback/uncaught exception.
2. Catalog with 7 free-air rows → same as 1.
3. Docker mocked absent → returns 2 with the Docker message, no traceback (regression of the earlier guard).
4. No CFD verify is called in 1–3 (guarded closure never fires); no `surrogate_guided.json` written.
5. Run as a real subprocess (`python scripts/run_optimization.py …` via a sitecustomize mock) for case 1: exit code 2 and stderr has no "Traceback". (+ if the subprocess mock is not feasible cheaply, rule 5 is "not re-tested" and closure rests on 1–4.)
6. Regression: `test_r111_cockpit_surrogate`, `test_surrogate_guided`, `test_optimization_argv` pass, and the QA-68 test exists in the repo and fails when the fix hunk is reverted in a scratch copy (reverted copy only, never the snapshot).
7. Non-RuntimeError failures are not swallowed (static: the except clause catches `RuntimeError` only) — informational.

## Verdict
- **QA-68 verified / closable** if 1–4 and 6 hold behaviourally (5 holds or is not re-tested with reason).
- **partly fixed** if any of 1–4 fails; **still open** if 1 fails.
- Out-dir creation before refusal is noted, not a fail.
