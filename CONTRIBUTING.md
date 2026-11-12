# Contributing

The working rules are in [AGENTS.md](AGENTS.md). Read that before you change anything. The task board is [docs/release/RELEASE_PLAN.md](docs/release/RELEASE_PLAN.md). This page is the short version, not a copy of `AGENTS.md`.

## Pre-register before a run judges a result

If a run sets a threshold, accepts a model, or decides whether a fix worked, write the pass/fail rule first and commit it. Put the file in `docs/validation/audits/`, named with the date and the topic, ending in `-prereg.md`. Run the check only after that file is in the repository. If the result fails, record the failure. Do not change the rule so the same run passes. An inconclusive result is not a pass.

## Tests first

For a behaviour change, write the test that should fail, run it, and see it fail before you change the code.

## No heavy CPU from 4 PM to 9 PM

Do not run heavy CPU from 4 PM to 9 PM local time, any day. That includes CFD, optimizer runs, the full test suite, and big builds. One heavy run can set the power bill's peak charge for the whole month. Run that work overnight or in the early morning.

## One branch per task

Use one branch per task. Do not force-push `master`.
